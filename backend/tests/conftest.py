import os

os.environ.setdefault("CARDS_JSON_PATH", "tests/fixtures/cards_fixture.json")
os.environ.setdefault("DEEPCHARD_DB_URL", "sqlite+aiosqlite:///./test_deepcards.db")

import pytest
from fastapi.testclient import TestClient

from app.engine.carddata import load_cards
from app.main import app
from app.models import User
from app.routers.auth import hash_password
from app.db import SessionLocal


@pytest.fixture(scope="session", autouse=True)
def load_cards_fixture():
    load_cards()
    yield


@pytest.fixture(scope="session", autouse=True)
def clean_test_db():
    # Ensure each pytest session starts with a fresh database.
    if os.path.exists("test_deepcards.db"):
        os.remove("test_deepcards.db")
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_token(client):
    import asyncio
    from sqlalchemy import select

    async def _ensure():
        async with SessionLocal() as db:
            existing = (
                await db.execute(select(User).where(User.username == "root"))
            ).scalars().first()
            if existing is None:
                db.add(User(username="root", email="root@example.com",
                            hashed_password=hash_password("rootpw1234"), role="admin"))
                await db.commit()

    asyncio.run(_ensure())
    resp = client.post("/api/auth/login", json={"username": "root", "password": "rootpw1234"})
    return resp.json()["access_token"]
