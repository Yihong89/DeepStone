from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

from .config import settings
from .db import SessionLocal, init_db
from .engine.carddata import load_cards
from .models import User
from .routers.auth import hash_password, router as auth_router
from .routers.cards import router as cards_router


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
    await init_db()
    await _bootstrap_admin()
    yield


app = FastAPI(title="Deepcards", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(cards_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
