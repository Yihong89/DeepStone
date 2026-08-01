from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Deepcards", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}
