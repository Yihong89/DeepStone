import os

os.environ.setdefault("CARDS_JSON_PATH", "tests/fixtures/cards_fixture.json")
os.environ.setdefault("DEEPCHARD_DB_URL", "sqlite+aiosqlite:///./test_deepcards.db")

import pytest
from fastapi.testclient import TestClient

from app.engine.carddata import load_cards
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def load_cards_fixture():
    load_cards()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
