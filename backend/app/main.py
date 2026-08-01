import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
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

# Serve private card art and audio (gitignored — never committed).
_images_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images")
os.makedirs(_images_dir, exist_ok=True)
app.mount("/images", StaticFiles(directory=_images_dir), name="images")

_audio_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "audio")
os.makedirs(_audio_dir, exist_ok=True)
app.mount("/audio", StaticFiles(directory=_audio_dir), name="audio")


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve the built React SPA so the whole app runs on a single port — no nginx.
# Dist is at <repo>/frontend/dist by default; override for the Docker mount.
_dist_dir = os.environ.get(
    "FRONTEND_DIST_DIR",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "frontend",
        "dist",
    ),
)


@app.get("/{full_path:path}", include_in_schema=False)
async def spa(full_path: str):
    # Never shadow the API/media mounts (they're registered before this route).
    if full_path.startswith(("api/", "images/", "audio/")):
        raise HTTPException(status_code=404)
    candidate = os.path.normpath(os.path.join(_dist_dir, full_path))
    if full_path and candidate.startswith(_dist_dir) and os.path.isfile(candidate):
        return FileResponse(candidate)
    index = os.path.join(_dist_dir, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    raise HTTPException(status_code=404)
