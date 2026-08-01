from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import init_db
from .engine.carddata import load_cards
from .routers.cards import router as cards_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_cards()
    await init_db()
    yield


app = FastAPI(title="Deepcards", lifespan=lifespan)
app.include_router(cards_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
