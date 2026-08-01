import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .config import settings
from .db import SessionLocal, init_db
from .engine.carddata import load_cards
from .engine.fireplace_setup import init_engine
from .models import User
from .routers.admin import router as admin_router
from .routers.auth import hash_password, router as auth_router
from .routers.cards import router as cards_router
from .routers.decks import router as decks_router
from .routers.games import router as games_router
from .routers.matches import router as matches_router


async def _bootstrap_admin():
    if not (settings.admin_username and settings.admin_password):
        return
    async with SessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.username == settings.admin_username))
        ).scalars().first()
        if user is None:
            db.add(User(
                username=settings.admin_username,
                email=f"{settings.admin_username}@deepcards.local",
                hashed_password=hash_password(settings.admin_password),
                role="admin",
            ))
            await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_cards()
    init_engine()
    await init_db()
    await _bootstrap_admin()
    yield


app = FastAPI(title="Deepcards", lifespan=lifespan)
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(cards_router)
app.include_router(decks_router)
app.include_router(games_router)
app.include_router(matches_router)

# Serve private card art from backend/images/ (gitignored — never committed).
_images_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images")
os.makedirs(_images_dir, exist_ok=True)
app.mount("/images", StaticFiles(directory=_images_dir), name="images")


@app.get("/health")
async def health():
    return {"status": "ok"}
