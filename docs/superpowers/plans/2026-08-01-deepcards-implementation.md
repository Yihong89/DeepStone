# Deepcards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-hosted web app where registered users construct decks from the full Fireplace card library and play Hearthstone-style matches head-to-head (challenge via code) or against a simple AI bot, with an admin panel.

**Architecture:** Fireplace (Python rules engine) runs each match in a worker thread. A `GameSession` bridges the synchronous engine to FastAPI WebSockets: when the engine needs a decision (mulligan, Discover choice, main action) it blocks on a `threading.Event` while the async WS layer sends the prompt to the player's browser and delivers the reply. Game state is serialized from Fireplace's built-in `dump()`/`dump_hidden()` and broadcast after each action. A React SPA renders the board. Data persists to SQLite (users, decks, match history); game state is in-memory.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, SQLAlchemy 2 (aiosqlite), PyJWT, bcrypt, `fireplace` (engine), `hearthstone_data` (card data); React 18, Vite, TypeScript, React Router, Zustand, Tailwind CSS; Docker Compose + nginx for deployment.

## Global Constraints

- Python **3.11+**; all backend deps pinned in `backend/requirements.txt`.
- Backend package layout: `backend/app/`; tests in `backend/tests/`, run with `pytest` from `backend/`.
- Frontend at `frontend/`; TypeScript `strict: true`; build with `npm run build`.
- All card IDs and hero IDs are **Fireplace card IDs** (e.g. `"CS2_029"`, `"HERO_08"`). The deck builder and engine must agree on the same universe (single `cards.json`).
- Card data path is configurable via env `CARDS_JSON_PATH` (tests point at a small fixture).
- JWT secret from env `DEEPCHARD_SECRET`; dev fallback `"dev-secret-change-me"`.
- Server-side deck validation is authoritative; client validation is convenience only.
- WebSocket message protocol is defined once in Task 12 and used by both client and server (no drift).
- Commit after every task. All new backend code is covered by a test that runs in CI.

---

## File Structure

```
deepcards/
├── backend/
│   ├── requirements.txt
│   ├── cards.json                      # generated (gitignored) — Task 3
│   ├── scripts/build_cards.py          # Task 3
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI app factory — Task 1
│   │   ├── config.py                   # settings — Task 1
│   │   ├── db.py                       # engine/session — Task 1
│   │   ├── models.py                   # User, Deck, Match — Tasks 4,7
│   │   ├── schemas.py                  # Pydantic DTOs — Tasks 4,7
│   │   ├── security.py                 # bcrypt + JWT — Task 5
│   │   ├── deps.py                     # get_current_user, require_admin — Task 5
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                 # Tasks 4,5
│   │   │   ├── cards.py                # Task 3
│   │   │   ├── decks.py                # Task 7
│   │   │   ├── games.py                # Task 12
│   │   │   ├── matches.py              # Task 12
│   │   │   └── admin.py                # Task 6
│   │   └── engine/
│   │       ├── __init__.py
│   │       ├── carddata.py             # load cards.json — Task 3
│   │       ├── serialize.py            # Game → JSON — Task 9
│   │       ├── bot.py                  # heuristic decisions — Task 10
│   │       ├── game_session.py         # worker-thread bridge — Task 11
│   │       └── manager.py              # session registry + WS handler — Task 12
│   └── tests/
│       ├── conftest.py
│       ├── fixtures/cards_fixture.json
│       ├── test_auth.py
│       ├── test_cards_api.py
│       ├── test_decks.py
│       ├── test_serialize.py
│       ├── test_bot.py
│       ├── test_game_session.py
│       └── test_games_api.py
├── frontend/
│   ├── package.json  vite.config.ts  tsconfig.json  tailwind.config.js  index.html
│   └── src/
│       ├── main.tsx  App.tsx  router.tsx  index.css
│       ├── api/client.ts  api/types.ts
│       ├── store/auth.ts  store/game.ts
│       ├── pages/Login.tsx  Register.tsx  Lobby.tsx  Gallery.tsx
│       │   DeckList.tsx  DeckBuilder.tsx  Play.tsx  GameBoard.tsx  Admin.tsx  Profile.tsx
│       └── components/CardView.tsx  TargetingOverlay.tsx  ChoiceDialog.tsx
├── deploy/
│   ├── docker-compose.yml  backend.Dockerfile  frontend.Dockerfile  nginx.conf
└── docs/superpowers/specs/2026-08-01-deepcards-design.md
```

---

### Task 1: Backend scaffold (FastAPI + SQLite + health check)

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `app.main.app` (FastAPI instance), `app.config.settings` (object with `.database_url`, `.jwt_secret`, `.cards_json_path`, `.admin_username`, `.admin_password`), `app.db.init_db()`, `app.db.get_session()` (async generator yielding `AsyncSession`).

- [ ] **Step 1: Write the failing test**

`backend/tests/test_health.py`:
```python
from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_health.py -v`
Expected: FAIL — module `app` not found.

- [ ] **Step 3: Write minimal implementation**

`backend/requirements.txt`:
```
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy[asyncio]==2.0.36
aiosqlite==0.20.0
pydantic==2.10.4
PyJWT==2.10.1
bcrypt==4.2.1
python-multipart==0.0.20
pytest==8.3.4
pytest-asyncio==0.25.2
httpx==0.28.1
fireplace @ git+https://github.com/jleclanche/fireplace.git@master
```

`backend/app/__init__.py`: empty.

`backend/app/config.py`:
```python
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DEEPCHARD_DB_URL", "sqlite+aiosqlite:///./deepcards.db")
    jwt_secret: str = os.getenv("DEEPCHARD_SECRET", "dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    cards_json_path: str = os.getenv("CARDS_JSON_PATH", "cards.json")
    admin_username: str = os.getenv("DEEPCHARD_ADMIN_USER", "")
    admin_password: str = os.getenv("DEEPCHARD_ADMIN_PASS", "")


settings = Settings()
```

`backend/app/db.py`:
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    # Import models so they register on Base before create_all.
    import app.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with SessionLocal() as session:
        yield session
```

`backend/app/main.py`:
```python
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
```

Note: `app/models.py` does not exist yet — the `import app.models` in `init_db` will fail until Task 4. To keep this task green, `init_db` must tolerate the missing module. Create `backend/app/models.py` now as an **empty module** (populated in Tasks 4/7):
```python
# Populated in later tasks (User, Deck, Match models).
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_health.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend && git commit -m "feat(backend): FastAPI scaffold with health check"
```

---

### Task 2: Frontend scaffold (Vite + React + TS + Tailwind + router)

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tailwind.config.js`, `frontend/postcss.config.js`, `frontend/index.html`
- Create: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/router.tsx`, `frontend/src/index.css`
- Create: `frontend/src/pages/Lobby.tsx` (placeholder)

**Interfaces:**
- Consumes: nothing.
- Produces: dev server (`npm run dev` on :5173 proxying `/api` and `/ws` to :8000), build (`npm run build`), `frontend/src/router.tsx` exporting `router` (React Router `createBrowserRouter`) with a `Lobby` route at `/`.

- [ ] **Step 1: Write the scaffold files**

`frontend/package.json`:
```json
{
  "name": "deepcards-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0",
    "zustand": "^5.0.2"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.16",
    "typescript": "^5.6.3",
    "vite": "^5.4.11"
  }
}
```

`frontend/vite.config.ts`:
```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
```

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "jsx": "react-jsx",
    "skipLibCheck": true,
    "noEmit": true,
    "types": ["vite/client"]
  },
  "include": ["src"]
}
```

`frontend/tailwind.config.js`:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
};
```

`frontend/postcss.config.js`:
```js
export default { plugins: { tailwindcss: {}, autoprefixer: {} } };
```

`frontend/index.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Deepcards</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`frontend/src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

`frontend/src/main.tsx`:
```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "./router";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
```

`frontend/src/router.tsx`:
```tsx
import { createBrowserRouter } from "react-router-dom";
import App from "./App";
import Lobby from "./pages/Lobby";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <Lobby /> },
    ],
  },
]);
```

`frontend/src/App.tsx`:
```tsx
import { Outlet } from "react-router-dom";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      <header className="border-b border-slate-700 px-6 py-3">
        <h1 className="text-xl font-bold text-amber-400">Deepcards</h1>
      </header>
      <main className="mx-auto max-w-6xl p-6">
        <Outlet />
      </main>
    </div>
  );
}
```

`frontend/src/pages/Lobby.tsx`:
```tsx
export default function Lobby() {
  return <div>Welcome to Deepcards.</div>;
}
```

- [ ] **Step 2: Install and verify build**

Run: `cd frontend && npm install && npm run build`
Expected: build succeeds, `frontend/dist/` produced.

- [ ] **Step 3: Verify dev server**

Run: `npm run dev` (background), then confirm `curl -s http://localhost:5173 | grep -q deepcards` and the page returns the app shell. Stop the server.

- [ ] **Step 4: Commit**

```bash
git add frontend
git commit -m "feat(frontend): Vite + React + TS + Tailwind scaffold with router shell"
```

---

### Task 3: Card data pipeline + `/cards` API

**Files:**
- Create: `backend/scripts/build_cards.py`
- Create: `backend/app/engine/__init__.py`
- Create: `backend/app/engine/carddata.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/cards.py`
- Create: `backend/tests/fixtures/cards_fixture.json`
- Modify: `backend/app/main.py` (register router + load card data at startup)
- Test: `backend/tests/test_cards_api.py`

**Interfaces:**
- Consumes: `app.main.app`; `app.config.settings.cards_json_path`.
- Produces: `app.engine.carddata.load_cards()` returning `list[CardMeta]` where `CardMeta` is a `TypedDict` with keys `id, name, text, cost, attack, health, type, cardClass, rarity, set, collectible`. `app.engine.carddata.get_card(card_id) -> CardMeta | None`, `app.engine.carddata.get_card_map() -> dict[str, CardMeta]`. Router `app.routers.cards.router` mounted at `/api/cards`.

**Card JSON schema (used everywhere downstream — keep stable):**
```json
{
  "id": "CS2_029",
  "name": "Fireball",
  "text": "Deal $6 damage.",
  "cost": 4,
  "attack": null,
  "health": null,
  "type": "SPELL",
  "cardClass": "MAGE",
  "rarity": "COMMON",
  "set": "CORE",
  "collectible": true
}
```

- [ ] **Step 1: Write the build script**

`backend/scripts/build_cards.py`:
```python
"""Generate cards.json from hearthstone_data (the same card data Fireplace uses)."""
import json
import os
import sys

from hearthstone.cardxml import load


def to_meta(c) -> dict:
    return {
        "id": c.card_id,
        "name": c.name,
        "text": getattr(c, "text", None) or "",
        "cost": getattr(c, "cost", None),
        "attack": getattr(c, "attack", None),
        "health": getattr(c, "health", None),
        "type": str(getattr(c, "type", "")).replace("CardType.", ""),
        "cardClass": str(getattr(c, "card_class", "")).replace("CardClass.", ""),
        "rarity": str(getattr(c, "rarity", "")).replace("Rarity.", ""),
        "set": str(getattr(c, "card_set", "")).replace("CardSet.", ""),
        "collectible": bool(getattr(c, "collectible", False)),
    }


def main() -> None:
    db, _ = load()
    out = sys.argv[1] if len(sys.argv) > 1 else "cards.json"
    cards = [to_meta(c) for c in db.values() if getattr(c, "collectible", False)]
    with open(out, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=1)
    print(f"Wrote {len(cards)} collectible cards to {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Generate cards.json and sanity-check**

Run: `cd backend && pip install -e . 2>/dev/null; python scripts/build_cards.py`
Expected: writes `backend/cards.json` with thousands of cards. Verify Fireball exists:
Run: `python -c "import json; d=json.load(open('cards.json')); print([c for c in d if c['id']=='CS2_029'])"`
Expected: a dict with name `Fireball`, class `MAGE`, type `SPELL`.

If `hearthstone.cardxml.load`'s attribute names differ from the script's guesses (e.g. `c.text` is `c.description`), adjust `to_meta` to the actual API and re-run. This is the one place the plan defers to the installed `hearthstone` package version.

- [ ] **Step 3: Write carddata module**

`backend/app/engine/carddata.py`:
```python
import json
from typing import TypedDict

from ..config import settings


class CardMeta(TypedDict, total=False):
    id: str
    name: str
    text: str
    cost: int | None
    attack: int | None
    health: int | None
    type: str
    cardClass: str
    rarity: str
    set: str
    collectible: bool


_cards: list[CardMeta] = []
_map: dict[str, CardMeta] = {}


def load_cards() -> list[CardMeta]:
    global _cards, _map
    with open(settings.cards_json_path, encoding="utf-8") as f:
        _cards = json.load(f)
    _map = {c["id"]: c for c in _cards}
    return _cards


def get_card_map() -> dict[str, CardMeta]:
    return _map


def get_card(card_id: str) -> CardMeta | None:
    return _map.get(card_id)
```

- [ ] **Step 4: Write the API + router registration**

`backend/app/routers/cards.py`:
```python
from fastapi import APIRouter, Query

from ..engine.carddata import load_cards

router = APIRouter(prefix="/api/cards", tags=["cards"])


@router.get("")
async def list_cards(
    q: str | None = Query(default=None),
    card_class: str | None = Query(default=None, alias="class"),
    cost: int | None = Query(default=None),
):
    cards = load_cards()
    if card_class:
        cards = [c for c in cards if c["cardClass"] == card_class]
    if cost is not None:
        cards = [c for c in cards if c.get("cost") == cost]
    if q:
        ql = q.lower()
        cards = [c for c in cards if ql in c["name"].lower() or ql in c["text"].lower()]
    return cards
```

Modify `backend/app/main.py`: after `from .db import init_db` add `from .engine.carddata import load_cards` and `from .routers.cards import router as cards_router`; in `lifespan`, before `init_db()`, call `load_cards()`; after `app = FastAPI(...)`, add `app.include_router(cards_router)`.

- [ ] **Step 5: Write the API test with a fixture universe**

`backend/tests/fixtures/cards_fixture.json` — a small, real universe used by unit tests (subset of real Fireplace cards):
```json
[
  {"id": "CS2_029", "name": "Fireball", "text": "Deal $6 damage.", "cost": 4, "attack": null, "health": null, "type": "SPELL", "cardClass": "MAGE", "rarity": "COMMON", "set": "CORE", "collectible": true},
  {"id": "CS2_200", "name": "Boulderfist Ogre", "text": "", "cost": 6, "attack": 6, "health": 7, "type": "MINION", "cardClass": "NEUTRAL", "rarity": "FREE", "set": "CORE", "collectible": true},
  {"id": "CS2_182", "name": "Chillwind Yeti", "text": "", "cost": 4, "attack": 4, "health": 5, "type": "MINION", "cardClass": "NEUTRAL", "rarity": "FREE", "set": "CORE", "collectible": true},
  {"id": "EX1_279", "name": "Pyroblast", "text": "Deal $10 damage.", "cost": 10, "attack": null, "health": null, "type": "SPELL", "cardClass": "MAGE", "rarity": "EPIC", "set": "EXPERT1", "collectible": true}
]
```

`backend/tests/conftest.py`:
```python
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
```

`backend/tests/test_cards_api.py`:
```python
def test_list_cards_all(client):
    resp = client.get("/api/cards")
    assert resp.status_code == 200
    assert len(resp.json()) == 4


def test_list_cards_filter_class(client):
    resp = client.get("/api/cards", params={"class": "MAGE"})
    assert {c["id"] for c in resp.json()} == {"CS2_029", "EX1_279"}


def test_list_cards_search(client):
    resp = client.get("/api/cards", params={"q": "boulder"})
    assert resp.json()[0]["id"] == "CS2_200"
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_cards_api.py -v`
Expected: 3 PASS. (Tests must run from `backend/` so the fixture path resolves.)

- [ ] **Step 7: Commit**

```bash
git add backend
git commit -m "feat(backend): card data pipeline and /api/cards endpoint"
```

---

### Task 4: User model + registration

**Files:**
- Create: `backend/app/schemas.py`
- Modify: `backend/app/models.py` (add `User`)
- Create: `backend/app/routers/auth.py`
- Modify: `backend/app/main.py` (register auth router)
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `app.db.Base`, `app.db.SessionLocal`.
- Produces: `app.models.User` (fields `id: int`, `username: str`, `email: str`, `hashed_password: str`, `role: str` in `{"user","admin"}`, `is_active: bool`, `created_at: datetime`), `app.routers.auth.router` mounted at `/api`, endpoint `POST /api/auth/register` accepting `{username, email, password}` → `201 {id, username, email, role}`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_auth.py`:
```python
def test_register_success(client):
    resp = client.post("/api/auth/register", json={
        "username": "alice",
        "email": "alice@example.com",
        "password": "hunter22",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"
    assert body["role"] == "user"
    assert "password" not in body


def test_register_duplicate_username(client):
    payload = {"username": "bob", "email": "bob@example.com", "password": "pw123456"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: FAIL — module `app.routers.auth` not found / 404.

- [ ] **Step 3: Implement models, schema, router**

`backend/app/models.py`:
```python
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
```

`backend/app/schemas.py`:
```python
from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str

    model_config = {"from_attributes": True}
```

Note: `EmailStr` requires `email-validator`. Add `email-validator==2.2.0` to `requirements.txt`.

`backend/app/routers/auth.py`:
```python
import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import User
from ..schemas import RegisterIn, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


@router.post("/register", status_code=201, response_model=UserOut)
async def register(data: RegisterIn, db: AsyncSession = Depends(get_session)):
    existing = await db.execute(
        select(User).where((User.username == data.username) | (User.email == data.email))
    )
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="Username or email already registered")
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
```

Modify `backend/app/main.py`: `from .routers.auth import router as auth_router`; `app.include_router(auth_router)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: 2 PASS. (If a stale `test_deepcards.db` causes 409 on the duplicate test, delete the db file before running.)

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat(backend): user registration with bcrypt"
```

---

### Task 5: Login + JWT + auth dependencies + admin bootstrap

**Files:**
- Create: `backend/app/security.py`
- Create: `backend/app/deps.py`
- Modify: `backend/app/routers/auth.py` (add login)
- Modify: `backend/app/main.py` (admin bootstrap in lifespan)
- Test: `backend/tests/test_auth.py` (extend)

**Interfaces:**
- Consumes: `app.models.User`, `app.config.settings` (jwt_secret, jwt_algorithm, jwt_expire_minutes, admin_username, admin_password).
- Produces: `app.security.create_token(user_id: int) -> str`, `app.security.decode_token(token: str) -> int`, `app.deps.get_current_user(db, Authorization) -> User`, `app.deps.require_admin(user) -> User`. Endpoint `POST /api/auth/login` → `{access_token, token_type: "bearer"}`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_auth.py`:
```python
def test_login_success(client):
    client.post("/api/auth/register", json={
        "username": "carol", "email": "carol@example.com", "password": "pw123456",
    })
    resp = client.post("/api/auth/login", json={
        "username": "carol", "password": "pw123456",
    })
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"
    assert resp.json()["access_token"]


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={
        "username": "dave", "email": "dave@example.com", "password": "pw123456",
    })
    resp = client.post("/api/auth/login", json={
        "username": "dave", "password": "wrongpass",
    })
    assert resp.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_user(client):
    client.post("/api/auth/register", json={
        "username": "erin", "email": "erin@example.com", "password": "pw123456",
    })
    token = client.post("/api/auth/login", json={
        "username": "erin", "password": "pw123456",
    }).json()["access_token"]
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "erin"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: 4 FAIL (404 on /api/auth/login, /api/auth/me).

- [ ] **Step 3: Implement security + deps + login**

`backend/app/security.py`:
```python
import jwt

from .config import settings


def create_token(user_id: int) -> str:
    payload = {"sub": str(user_id)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> int:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return int(payload["sub"])
```

`backend/app/deps.py`:
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import User
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_session),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_id = decode_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid or inactive user")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user
```

Append to `backend/app/routers/auth.py` (reusing `hash_password`, add `verify_password`):
```python
import bcrypt
from fastapi import Depends
from sqlalchemy import select

from ..deps import get_current_user
from ..schemas import LoginIn


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


@router.post("/login")
async def login(data: LoginIn, db: AsyncSession = Depends(get_session)):
    user = (
        await db.execute(select(User).where(User.username == data.username))
    ).scalars().first()
    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return {"access_token": create_token(user.id), "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
```

Add to `backend/app/schemas.py`:
```python
class LoginIn(BaseModel):
    username: str
    password: str
```

Update imports at top of `auth.py` to include `from ..security import create_token`.

- [ ] **Step 4: Admin bootstrap in lifespan**

Modify `backend/app/main.py` `lifespan`:
```python
from sqlalchemy import select

from .config import settings
from .models import User
from .routers.auth import hash_password


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
```
Call `await _bootstrap_admin()` inside `lifespan` after `init_db()`. Add `from .db import SessionLocal`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: 8 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend
git commit -m "feat(backend): JWT login, /me, auth deps, admin bootstrap"
```

---

### Task 6: Admin user-management endpoints

**Files:**
- Create: `backend/app/routers/admin.py`
- Modify: `backend/app/main.py` (register admin router)
- Test: `backend/tests/test_admin.py`

**Interfaces:**
- Consumes: `app.deps.get_current_user`, `app.deps.require_admin`, `app.models.User`.
- Produces: `app.routers.admin.router` at `/api/admin`. Endpoints:
  - `GET /api/admin/users` → `[{id, username, email, role, is_active, created_at}]`
  - `PATCH /api/admin/users/{id}` body `{is_active: bool}` → updated user
  - `POST /api/admin/users/{id}/reset-password` body `{new_password}` → `{status: "ok"}`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_admin.py`:
```python
def _register(client, username, password="pw123456"):
    client.post("/api/auth/register", json={
        "username": username, "email": f"{username}@example.com", "password": password,
    })
    token = client.post("/api/auth/login", json={
        "username": username, "password": password,
    }).json()["access_token"]
    return token


def test_admin_can_list_users(client):
    _register(client, "admin1")
    _register(client, "alice")
    token = _register(client, "boss")
    client.post("/api/admin/users/1/reset-password",
                json={"new_password": "freshpass"},
                headers={"Authorization": f"Bearer {token}"})
    resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403  # boss is not admin


def test_non_admin_forbidden(client):
    token = _register(client, "mallory")
    resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
```

The admin-role test needs an admin user. Rather than depend on env bootstrap (slow), the test creates an admin directly in the DB. Add to `backend/tests/conftest.py` a fixture:
```python
from sqlalchemy import select
from app.db import SessionLocal
from app.models import User
from app.routers.auth import hash_password


@pytest.fixture
def admin_token(client):
    import asyncio
    from app.db import SessionLocal
    from app.models import User

    async def _make():
        async with SessionLocal() as db:
            user = User(username="root", email="root@example.com",
                        hashed_password=hash_password("rootpw1234"), role="admin")
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user.id

    uid = asyncio.run(_make())
    resp = client.post("/api/auth/login", json={"username": "root", "password": "rootpw1234"})
    return resp.json()["access_token"]
```

Then extend `test_admin.py`:
```python
def test_admin_lists_and_disables(client, admin_token):
    _register(client, "victim")
    headers = {"Authorization": f"Bearer {admin_token}"}
    users = client.get("/api/admin/users", headers=headers).json()
    victim = next(u for u in users if u["username"] == "victim")
    resp = client.patch(f"/api/admin/users/{victim['id']}", json={"is_active": False},
                        headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_admin.py -v`
Expected: FAIL (404 / 403 for router missing).

- [ ] **Step 3: Implement admin router**

`backend/app/routers/admin.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import require_admin
from ..models import User
from ..routers.auth import hash_password
from ..schemas import UserOut

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_session)):
    users = (await db.execute(select(User).order_by(User.id))).scalars().all()
    return users


@router.patch("/users/{user_id}")
async def set_active(user_id: int, body: dict, db: AsyncSession = Depends(get_session)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = bool(body["is_active"])
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password")
async def reset_password(user_id: int, body: dict, db: AsyncSession = Depends(get_session)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = hash_password(body["new_password"])
    await db.commit()
    return {"status": "ok"}
```

Register in `main.py`: `from .routers.admin import router as admin_router`; `app.include_router(admin_router)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_admin.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat(backend): admin user management endpoints"
```

---

### Task 7: Decks — model, CRUD, validation

**Files:**
- Modify: `backend/app/models.py` (add `Deck`)
- Modify: `backend/app/schemas.py` (deck schemas)
- Create: `backend/app/routers/decks.py`
- Modify: `backend/app/main.py` (register decks router)
- Create: `backend/app/engine/deck_rules.py`
- Test: `backend/tests/test_decks.py`

**Interfaces:**
- Consumes: `app.engine.carddata.get_card_map()`, `app.deps.get_current_user`, `app.models.User`.
- Produces: `app.models.Deck` (fields `id, user_id, name, hero_class, card_ids: str (JSON), created_at, updated_at`), `app.engine.deck_rules.validate_deck(hero_class, card_ids) -> list[str]` (returns error messages; empty = valid), router `app.routers.decks.router` at `/api/decks`:
  - `GET /api/decks` → user's decks
  - `POST /api/decks` → `201` deck
  - `GET /api/decks/{id}`, `PUT /api/decks/{id}`, `DELETE /api/decks/{id}`

**Validation rules (authoritative):**
1. exactly 30 cards
2. card must exist in the card map
3. card must be playable for `hero_class`: `card["cardClass"] == hero_class` or `card["cardClass"] == "NEUTRAL"`
4. legendary cards ≤1 copy; all others ≤2 copies

- [ ] **Step 1: Write the failing test**

`backend/tests/test_decks.py`:
```python
def _register(client, username="sam", password="pw123456"):
    client.post("/api/auth/register", json={
        "username": username, "email": f"{username}@example.com", "password": password,
    })
    return client.post("/api/auth/login", json={
        "username": username, "password": password,
    }).json()["access_token"]


def _murloc30():
    # 2x Fireball (MAGE) + 28x Chillwind Yeti (NEUTRAL) => 30 cards, valid for MAGE
    return ["CS2_029", "CS2_029"] + ["CS2_182"] * 28


def test_create_valid_deck(client):
    token = _register(client)
    resp = client.post("/api/decks", json={
        "name": "Fire Yetis",
        "hero_class": "MAGE",
        "card_ids": _murloc30(),
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    assert len(resp.json()["card_ids"]) == 30


def test_deck_wrong_class_rejected(client):
    token = _register(client)
    # Fireball is MAGE; trying to build a WARRIOR deck with it is invalid
    resp = client.post("/api/decks", json={
        "name": "Bad",
        "hero_class": "WARRIOR",
        "card_ids": ["CS2_029"] * 30,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422
    assert "class" in resp.json()["detail"]


def test_deck_too_many_legendaries_rejected(client):
    token = _register(client)
    # 3x Pyroblast (legendary EPIC? No — EPIC) -> 3 copies of an EPIC is invalid
    resp = client.post("/api/decks", json={
        "name": "Triple",
        "hero_class": "MAGE",
        "card_ids": ["EX1_279"] * 3 + ["CS2_182"] * 27,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422
```

Note: the legendary-copy test depends on fixture rarity. In `cards_fixture.json`, `EX1_279` is `EPIC` (not legendary), and 3×EPIC is also invalid under rule 4 (≤2 non-legendary). If you want an explicit legendary test, add a `LEGENDARY` card to the fixture and assert 2× is rejected. Keep both.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_decks.py -v`
Expected: FAIL (404).

- [ ] **Step 3: Implement validation + model + router**

`backend/app/engine/deck_rules.py`:
```python
from collections import Counter

from .carddata import get_card_map


def validate_deck(hero_class: str, card_ids: list[str]) -> list[str]:
    errors: list[str] = []
    if len(card_ids) != 30:
        errors.append("A deck must contain exactly 30 cards")
        return errors
    card_map = get_card_map()
    counts = Counter(card_ids)
    for cid, count in counts.items():
        card = card_map.get(cid)
        if card is None:
            errors.append(f"Unknown card: {cid}")
            continue
        cc = card["cardClass"]
        if cc not in (hero_class, "NEUTRAL"):
            errors.append(f"{card['name']} cannot be used in a {hero_class} deck")
        if card["rarity"] == "LEGENDARY":
            if count > 1:
                errors.append(f"Only 1 copy of legendary card {card['name']} allowed")
        elif count > 2:
            errors.append(f"Only 2 copies of {card['name']} allowed")
    return errors
```

Add `Deck` to `backend/app/models.py`:
```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    hero_class: Mapped[str] = mapped_column(String(32))
    card_ids: Mapped[str] = mapped_column(Text)  # JSON array of card IDs
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User")
```

Add schemas to `backend/app/schemas.py`:
```python
from typing import Literal


class DeckIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    hero_class: str
    card_ids: list[str]


class DeckOut(BaseModel):
    id: int
    user_id: int
    name: str
    hero_class: str
    card_ids: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```
(Add `from datetime import datetime` and `from typing import Literal` only if unused, drop them.)

`backend/app/routers/decks.py`:
```python
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user
from ..engine.deck_rules import validate_deck
from ..models import Deck, User
from ..schemas import DeckIn, DeckOut

router = APIRouter(prefix="/api/decks", tags=["decks"])


def _to_out(deck: Deck) -> dict:
    return {
        "id": deck.id,
        "user_id": deck.user_id,
        "name": deck.name,
        "hero_class": deck.hero_class,
        "card_ids": json.loads(deck.card_ids),
        "created_at": deck.created_at,
        "updated_at": deck.updated_at,
    }


@router.get("", response_model=list[DeckOut])
async def list_decks(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    decks = (
        await db.execute(select(Deck).where(Deck.user_id == user.id).order_by(Deck.updated_at.desc()))
    ).scalars().all()
    return [_to_out(d) for d in decks]


@router.post("", status_code=201, response_model=DeckOut)
async def create_deck(data: DeckIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    errors = validate_deck(data.hero_class, data.card_ids)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    deck = Deck(
        user_id=user.id,
        name=data.name,
        hero_class=data.hero_class,
        card_ids=json.dumps(data.card_ids),
    )
    db.add(deck)
    await db.commit()
    await db.refresh(deck)
    return _to_out(deck)


@router.get("/{deck_id}", response_model=DeckOut)
async def get_deck(deck_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    deck = await db.get(Deck, deck_id)
    if deck is None or deck.user_id != user.id:
        raise HTTPException(status_code=404, detail="Deck not found")
    return _to_out(deck)


@router.put("/{deck_id}", response_model=DeckOut)
async def update_deck(deck_id: int, data: DeckIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    deck = await db.get(Deck, deck_id)
    if deck is None or deck.user_id != user.id:
        raise HTTPException(status_code=404, detail="Deck not found")
    errors = validate_deck(data.hero_class, data.card_ids)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    deck.name = data.name
    deck.hero_class = data.hero_class
    deck.card_ids = json.dumps(data.card_ids)
    await db.commit()
    await db.refresh(deck)
    return _to_out(deck)


@router.delete("/{deck_id}", status_code=204)
async def delete_deck(deck_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    deck = await db.get(Deck, deck_id)
    if deck is None or deck.user_id != user.id:
        raise HTTPException(status_code=404, detail="Deck not found")
    await db.delete(deck)
    await db.commit()
```

Register in `main.py`: `from .routers.decks import router as decks_router`; `app.include_router(decks_router)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_decks.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat(backend): deck CRUD with server-side validation"
```

---

### Task 8: Fireplace integration probe (scripted bot-vs-bot game)

This task is a spike that proves the engine API and produces reusable fixtures. It uses the **real** Fireplace + hearthstone_data card universe.

**Files:**
- Create: `backend/app/engine/heroes.py`
- Create: `backend/tests/engine_utils.py`
- Test: `backend/tests/test_engine_probe.py`

**Interfaces:**
- Consumes: `fireplace` package, `hearthstone_data`.
- Produces: `app.engine.heroes.HERO_BY_CLASS: dict[str, str]` mapping class name → hero card ID; `backend/tests/engine_utils.py` exposing `build_deck(card_class, n=30) -> list[str]` (deterministic 30-card deck from real data) and `run_scripted_game(deck1, deck2, hero1, hero2) -> Game` (plays a full game with two trivial in-process controllers that always end turn / mulligan nothing).

- [ ] **Step 1: Write the failing probe test**

`backend/tests/test_engine_probe.py`:
```python
from engine_utils import build_deck, run_scripted_game
from app.engine.heroes import HERO_BY_CLASS


def test_full_game_bot_vs_bot():
    deck1 = build_deck("MAGE")
    deck2 = build_deck("MAGE")
    game = run_scripted_game(deck1, deck2, HERO_BY_CLASS["MAGE"], HERO_BY_CLASS["MAGE"])
    assert game.ended
    assert any(p.playstate.name in ("WON", "LOST", "TIED") for p in game.players)
```

- [ ] **Step 2: Implement the helper + hero map**

`backend/app/engine/heroes.py`:
```python
HERO_BY_CLASS = {
    "MAGE": "HERO_08",
    "WARRIOR": "HERO_01",
    "SHAMAN": "HERO_02",
    "ROGUE": "HERO_03",
    "PALADIN": "HERO_04",
    "HUNTER": "HERO_05",
    "DRUID": "HERO_06",
    "WARLOCK": "HERO_07",
    "PRIEST": "HERO_09",
    "DEMONHUNTER": "HERO_10",
}
```

`backend/tests/engine_utils.py`:
```python
"""Shared helpers for engine integration tests (real Fireplace card data)."""
import json
from pathlib import Path

from fireplace.game import Game
from fireplace.player import Player

CARDS = json.loads(Path("cards.json").read_text())


def build_deck(card_class: str, n: int = 30) -> list[str]:
    pool = [c for c in CARDS if c["cardClass"] in (card_class, "NEUTRAL")]
    deck = []
    for c in pool:
        copies = 1 if c["rarity"] == "LEGENDARY" else 2
        for _ in range(min(copies, n - len(deck))):
            deck.append(c["id"])
        if len(deck) >= n:
            break
    return deck


class PassController:
    """Minimal controller: mulligan nothing, end turn immediately."""

    def __init__(self, game):
        self.game = game

    def choose(self, choice):
        # For a MulliganChoice: keep everything -> choose() nothing
        return getattr(choice, "cards", [])


def run_scripted_game(deck1, deck2, hero1, hero2, seed=42):
    p1 = Player("Bot1", deck1, hero1)
    p2 = Player("Bot2", deck2, hero2)
    game = Game([p1, p2], seed=seed)
    game.start()
    # Resolve both mulligan choices (keep all)
    for player in game.players:
        if player.choice is not None:
            player.choice.choose()
    # Drive turns: current player ends their turn until game over
    while not game.ended:
        if game.current_player.choice is not None:
            game.current_player.choice.choose(
                game.current_player.choice.cards[0]
            )
            continue
        game.end_turn()
    return game
```

**Note on the controller interface:** this Fireplace version has no `Controller`/`choose_action` class — the host drives the game by calling `game.end_turn()`, `game.play_card(...)`, etc. If the probe fails with a missing attribute (e.g. `choice.choose()` signature differs), read `fireplace/actions.py` (`MulliganChoice.choose`, `Choice.choose`) and `fireplace/game.py` and adjust `run_scripted_game` to match. The correct API, as of the cloned master, is:
- `MulliganChoice.choose(*cards)` — call with the cards to mulligan (empty = keep all).
- `Choice.choose(card)` — pick one of `choice.cards`.
- `game.end_turn()`, `game.play_card(card, target, index, choose)`, `game.attack(source, target)`, `game.main_power(source, [PlayHeroPower(target)], target)`.

- [ ] **Step 3: Run the probe**

Run: `cd backend && pytest tests/test_engine_probe.py -v`
Expected: PASS — a full bot-vs-bot game completes and the game is over.

- [ ] **Step 4: Commit**

```bash
git add backend
git commit -m "feat(backend): Fireplace engine probe — scripted full game"
```

---

### Task 9: Game state serializer

**Files:**
- Create: `backend/app/engine/serialize.py`
- Test: `backend/tests/test_serialize.py`

**Interfaces:**
- Consumes: `app.engine.game_state` (a `Game` instance from Fireplace).
- Produces:
  - `serialize.serialize(game, for_player_index: int) -> dict` — a full per-player snapshot.
  - `serialize.card_summary(card) -> dict` — compact card info for dialogs/prompts.
  - `serialize.choice_payload(choice) -> dict` — `{"cards": [...], "min": int, "max": int}`.

**Snapshot shape (contract for the frontend — Task 17 depends on it):**
```json
{
  "turn": 3,
  "current_player": 0,
  "ended": false,
  "result": null,
  "players": [
    {
      "index": 0,
      "hero": {"entity_id": 3, "id": "HERO_08", "name": "Jaina Proudmoore",
               "atk": 0, "max_health": 30, "damage": 0, "armor": 0, "can_attack": false},
      "hero_power": {"entity_id": 4, "id": "CS2_034", "name": "Fireblast", "cost": 2, "can_attack": false},
      "weapon": null,
      "deck_count": 23,
      "hand": [ {"entity_id": 5, "id": "CS2_029", "name": "Fireball", "cost": 4,
                 "text": "Deal $6 damage.", "zone": 4} ],
      "field": [ {"entity_id": 9, "id": "CS2_200", "name": "Boulderfist Ogre", "atk": 6,
                   "max_health": 7, "damage": 0, "taunt": false, "stealthed": false,
                   "divine_shield": false, "frozen": false, "exhausted": true,
                   "num_attacks": 0, "can_attack": false, "zone_position": 0} ],
      "secrets": [],
      "max_mana": 3, "mana": 3, "playstate": "PLAYING"
    },
    { "...": "opponent, same shape but hand entries are {entity_id} only" }
  ],
  "pending": {"kind": null}
}
```

- [ ] **Step 1: Write the failing test**

`backend/tests/test_serialize.py`:
```python
import json
from pathlib import Path

from fireplace.game import Game
from fireplace.player import Player

from app.engine.serialize import serialize
from engine_utils import build_deck, run_scripted_game
from app.engine.heroes import HERO_BY_CLASS


def _fresh_game():
    deck = build_deck("MAGE", 10)
    p1 = Player("P1", deck, HERO_BY_CLASS["MAGE"])
    p2 = Player("P2", deck, HERO_BY_CLASS["MAGE"])
    return Game([p1, p2], seed=1)


def test_snapshot_shape():
    game = _fresh_game()
    game.start()
    snap = serialize(game, 0)
    assert snap["turn"] == 0
    assert snap["current_player"] == 0
    assert len(snap["players"]) == 2
    me, opp = snap["players"]
    assert me["index"] == 0
    assert opp["index"] == 1
    assert me["hero"]["name"]
    assert "hand" in me and "field" in me and "mana" in me and "max_mana" in me


def test_opponent_hand_is_hidden():
    game = _fresh_game()
    game.start()
    me, opp = serialize(game, 0)["players"]
    assert len(me["hand"]) == len(game.players[0].hand)  # full cards
    assert len(opp["hand"]) == len(game.players[1].hand)  # same count
    for card in opp["hand"]:
        assert "name" not in card and "cost" not in card  # masked


def test_choice_payload():
    game = _fresh_game()
    game.start()
    for player in game.players:
        if player.choice is not None:
            payload = __import__("app.engine.serialize", fromlist=["choice_payload"]).choice_payload(player.choice)
            assert "cards" in payload and payload["cards"]
            break
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_serialize.py -v`
Expected: FAIL — module `app.engine.serialize` not found.

- [ ] **Step 3: Implement serializer**

`backend/app/engine/serialize.py`:
```python
from __future__ import annotations

from fireplace.card import Character, Hero, HeroPower, Minion, Weapon, PlayableCard
from fireplace.game import Game


def _base(card) -> dict:
    d = {"entity_id": card.entity_id}
    if card.zone:
        d["zone"] = int(card.zone)
    if getattr(card, "zone_position", None) is not None:
        d["zone_position"] = card.zone_position
    return d


def _character(card: Character) -> dict:
    d = _base(card)
    d.update({
        "id": card.id,
        "name": card.data.name,
        "atk": card.atk,
        "max_health": card.max_health,
        "damage": card.damage,
        "taunt": card.taunt,
        "stealthed": card.stealthed,
        "divine_shield": getattr(card, "divine_shield", False),
        "frozen": card.frozen,
        "exhausted": card.exhausted,
        "num_attacks": getattr(card, "num_attacks", 0),
        "can_attack": card.can_attack() if hasattr(card, "can_attack") else False,
    })
    return d


def _hand_card(card: PlayableCard, hidden: bool) -> dict:
    if hidden:
        return {"entity_id": card.entity_id}
    return {
        "entity_id": card.entity_id,
        "id": card.id,
        "name": card.data.name,
        "cost": card.cost,
        "text": getattr(card, "description", "") or "",
    }


def _hero(hero: Hero) -> dict:
    d = _character(hero)
    d["armor"] = hero.armor
    return d


def _hero_power(hp: HeroPower | None) -> dict | None:
    if hp is None:
        return None
    return {"entity_id": hp.entity_id, "id": hp.id, "name": hp.data.name, "cost": hp.cost}


def _weapon(w: Weapon | None) -> dict | None:
    if w is None:
        return None
    return {"entity_id": w.entity_id, "id": w.id, "name": w.data.name,
            "atk": w.atk, "max_health": w.max_durability}


def _player(game: Game, player, index: int, hidden: bool) -> dict:
    return {
        "index": index,
        "hero": _hero(player.hero),
        "hero_power": _hero_power(player.hero.power),
        "weapon": _weapon(player.weapon),
        "deck_count": len(player.deck),
        "hand": [_hand_card(c, hidden) for c in player.hand],
        "field": [_character(c) for c in player.field],
        "secrets": [{"entity_id": c.entity_id} for c in player.secrets],
        "max_mana": player.max_mana,
        "mana": player.mana,
        "playstate": player.playstate.name,
    }


def serialize(game: Game, for_player_index: int) -> dict:
    me = game.players[for_player_index]
    opp = game.players[1 - for_player_index]
    pending = None
    for i, p in enumerate(game.players):
        if p.choice is not None:
            pending = {"player": i, "kind": "mulligan" if p.mulligan_state and p.mulligan_state.name == "INPUT" else "choice"}
            break
    return {
        "turn": game.turn,
        "current_player": 0 if game.current_player is game.players[0] else 1,
        "ended": game.ended,
        "result": _result(game),
        "players": [
            _player(game, me, for_player_index, hidden=False),
            _player(game, opp, 1 - for_player_index, hidden=True),
        ],
        "pending": pending,
    }


def _result(game: Game) -> dict | None:
    if not game.ended:
        return None
    states = [p.playstate for p in game.players]
    if "WON" in [s.name for s in states]:
        winner = 0 if states[0].name == "WON" else 1
    else:
        winner = None
    return {"winner": winner, "playstates": [s.name for s in states]}


def card_summary(card) -> dict:
    return {
        "entity_id": card.entity_id,
        "id": card.id,
        "name": card.data.name,
        "cost": getattr(card, "cost", None),
        "atk": getattr(card, "atk", None),
        "max_health": getattr(card, "max_health", None),
        "text": getattr(card, "description", "") or "",
    }


def choice_payload(choice) -> dict:
    return {"cards": [card_summary(c) for c in choice.cards],
            "min": getattr(choice, "min_count", 1),
            "max": getattr(choice, "max_count", 1)}
```

If any attribute differs from the installed Fireplace (e.g. `player.mulligan_state`), fall back to detecting mulligan by `type(choice).__name__ == "MulliganChoice"` — adjust `serialize` accordingly and update the test.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_serialize.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat(backend): game state serializer with hidden-info handling"
```

---

### Task 10: Heuristic bot

**Files:**
- Create: `backend/app/engine/bot.py`
- Test: `backend/tests/test_bot.py`

**Interfaces:**
- Consumes: `fireplace` game objects; `app.engine.serialize.card_summary`.
- Produces: pure decision functions returning **decision dicts** (same shape the WS client sends, so human and bot paths share one applier):
  - `bot.choose_mulligan(player) -> list[int]` — entity_ids of cards to mulligan (return `[]` to keep all).
  - `bot.choose_main_action(player) -> dict` — one of:
    ```json
    {"kind": "play_card", "card": <entity_id>, "target": <entity_id|null>, "index": 0, "choose": <entity_id|null>}
    {"kind": "attack", "source": <entity_id>, "target": <entity_id>}
    {"kind": "hero_power", "target": <entity_id|null>}
    {"kind": "end_turn"}
    ```
  - `bot.choose_choice(player) -> int` — entity_id picked from `player.choice.cards`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_bot.py`:
```python
from fireplace.game import Game
from fireplace.player import Player

from app.engine.bot import choose_main_action, choose_mulligan
from app.engine.heroes import HERO_BY_CLASS
from engine_utils import build_deck


def test_bot_mulligan_returns_entity_ids():
    deck = build_deck("MAGE", 10)
    p = Player("Bot", deck, HERO_BY_CLASS["MAGE"])
    game = Game([p, Player("Bot2", deck, HERO_BY_CLASS["MAGE"])], seed=3)
    game.start()
    mull = p.choice
    assert mull is not None
    result = choose_mulligan(p)
    assert isinstance(result, list)
    assert all(isinstance(x, int) for x in result)


def test_bot_main_action_is_well_formed():
    deck = build_deck("MAGE", 10)
    p = Player("Bot", deck, HERO_BY_CLASS["MAGE"])
    game = Game([p, Player("Bot2", deck, HERO_BY_CLASS["MAGE"])], seed=3)
    game.start()
    # Resolve mulligans so it's the current player's turn
    for player in game.players:
        if player.choice is not None:
            player.choice.choose()
    action = choose_main_action(game.current_player)
    assert action["kind"] in {"play_card", "attack", "hero_power", "end_turn"}
    if action["kind"] in {"play_card", "attack", "hero_power"}:
        assert isinstance(action.get("target") or 0, int) or action.get("target") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_bot.py -v`
Expected: FAIL — module `app.engine.bot` not found.

- [ ] **Step 3: Implement bot**

`backend/app/engine/bot.py`:
```python
"""Minimal heuristic bot. Returns decision dicts identical to the WS protocol."""


def choose_mulligan(player) -> list[int]:
    """Mulligan cards that cost more than 3 mana."""
    return [c.entity_id for c in player.hand if c.cost > 3]


def _playable(player):
    return [c for c in player.hand if c.is_playable()]


def _valid_target(card):
    if hasattr(card, "targets") and card.targets:
        return card.targets[0].entity_id
    return None


def choose_main_action(player) -> dict:
    # 1) Play the highest-cost playable card (first valid target if needed)
    for card in sorted(_playable(player), key=lambda c: c.cost, reverse=True):
        if card.must_choose_one and card.choose_cards:
            choose = card.choose_cards[0]
        else:
            choose = None
        if hasattr(card, "battlecry_requires_target") and card.battlecry_requires_target() and not card.targets:
            continue
        target = _valid_target(card)
        return {
            "kind": "play_card",
            "card": card.entity_id,
            "target": target,
            "index": 0,
            "choose": choose.entity_id if choose else None,
        }
    # 2) Attack with the highest-attack attacker
    for source in sorted(player.field, key=lambda m: m.atk, reverse=True):
        if source.can_attack():
            targets = source.attack_targets
            if targets:
                return {"kind": "attack", "source": source.entity_id,
                        "target": targets[0].entity_id}
    # 3) Use hero power if it can target something useful or is usable
    hp = player.hero.power
    if hp is not None and hp.is_playable():
        target = None
        if hasattr(hp, "targets") and hp.targets:
            target = hp.targets[0].entity_id
        return {"kind": "hero_power", "target": target}
    # 4) Otherwise end turn
    return {"kind": "end_turn"}


def choose_choice(player) -> int:
    choice = player.choice
    if choice is None or not choice.cards:
        return 0
    return choice.cards[0].entity_id
```

If `card.targets`, `card.battlecry_requires_target()`, `source.attack_targets`, or `hp.is_playable()` differ in the installed Fireplace, consult `fireplace/card.py` and adjust — the test only asserts the returned dict shape.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_bot.py -v`
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat(backend): heuristic bot returning WS-protocol decisions"
```

---

### Task 11: GameSession — worker-thread bridge

**Files:**
- Create: `backend/app/engine/game_session.py`
- Test: `backend/tests/test_game_session.py`

**Interfaces:**
- Consumes: `fireplace` engine, `app.engine.serialize`, `app.engine.bot`, `app.engine.heroes.HERO_BY_CLASS`.
- Produces:
  ```python
  class GameSession:
      def __init__(self, game_id, player1: dict, player2: dict, seed=None)
          # player = {"name": str, "hero": str, "deck": list[str], "is_bot": bool}
      def set_send(self, player_index: int, callback) -> None
          # callback(player_index, message: dict) — thread-safe (use loop.call_soon_threadsafe)
      def submit_decision(self, player_index: int, decision: dict) -> None
          # called from the asyncio loop with the client's decision
      def start(self) -> None            # launches worker thread
      def snapshot_for(self, index) -> dict
      @property
      def game(self) -> Game
  ```
  Callback contract: `send(player_index, message)` where `message` is either `{"type":"snapshot","state": {...}}`, `{"type":"mulligan","cards":[...]}` , `{"type":"choice","choice":{...}}`, `{"type":"game_over","result":{...}}`.

**Decision wiring (the crux):** The worker thread drives the game loop; whenever it needs a decision from a human player it **blocks on a `threading.Event`**. The asyncio layer calls `submit_decision` to set the event + value. Bots decide inline via `bot.py`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_game_session.py`:
```python
import threading

from app.engine.game_session import GameSession
from app.engine.heroes import HERO_BY_CLASS
from engine_utils import build_deck


def test_bot_vs_bot_session_completes():
    deck = build_deck("MAGE", 15)
    session = GameSession(
        "sess1",
        {"name": "BotA", "hero": HERO_BY_CLASS["MAGE"], "deck": deck, "is_bot": True},
        {"name": "BotB", "hero": HERO_BY_CLASS["MAGE"], "deck": deck, "is_bot": True},
        seed=7,
    )
    snapshots = []
    session.set_send(0, lambda i, m: snapshots.append((i, m)))
    session.set_send(1, lambda i, m: snapshots.append((i, m)))
    session.start()
    session.join(timeout=30)  # helper: block until game ends
    assert session.game.ended
    assert any(m["type"] == "game_over" for _, m in snapshots)


def test_snapshot_available_before_start():
    deck = build_deck("MAGE", 15)
    session = GameSession("sess2", {"name": "A", "hero": HERO_BY_CLASS["MAGE"], "deck": deck, "is_bot": True},
                          {"name": "B", "hero": HERO_BY_CLASS["MAGE"], "deck": deck, "is_bot": True})
    snap = session.snapshot_for(0)
    assert "players" in snap and len(snap["players"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_game_session.py -v`
Expected: FAIL — module `app.engine.game_session` not found.

- [ ] **Step 3: Implement GameSession**

`backend/app/engine/game_session.py`:
```python
import threading

from fireplace.game import Game
from fireplace.player import Player

from . import bot
from .serialize import choice_payload, serialize


class _PendingDecision:
    def __init__(self, player_index: int, kind: str, data: dict):
        self.player_index = player_index
        self.kind = kind
        self.data = data
        self._event = threading.Event()
        self.result = None

    def resolve(self, result) -> None:
        self.result = result
        self._event.set()


class GameSession:
    def __init__(self, game_id: str, player1: dict, player2: dict, seed=None):
        self.game_id = game_id
        self._players = [player1, player2]
        self._sends = {0: None, 1: None}
        self._decisions: dict[int, _PendingDecision] = {}
        self._lock = threading.Lock()
        self._game = Game(
            [
                Player(player1["name"], player1["deck"], player1["hero"]),
                Player(player2["name"], player2["deck"], player2["hero"]),
            ],
            seed=seed,
        )
        self._thread = None

    @property
    def game(self) -> Game:
        return self._game

    def set_send(self, player_index: int, callback) -> None:
        self._sends[player_index] = callback

    def _send(self, player_index: int, message: dict) -> None:
        cb = self._sends[player_index]
        if cb is not None:
            cb(player_index, message)

    def submit_decision(self, player_index: int, decision: dict) -> None:
        with self._lock:
            pending = self._decisions.get(player_index)
            if pending is not None:
                pending.resolve(decision)

    def _ask(self, player_index: int, kind: str, data: dict):
        player = self._players[player_index]
        if player["is_bot"]:
            return self._bot_decision(player_index, kind)
        pending = _PendingDecision(player_index, kind, data)
        with self._lock:
            self._decisions[player_index] = pending
        self._send(player_index, data)
        pending._event.wait(120)  # 120s grace; treat as concede on timeout
        with self._lock:
            self._decisions.pop(player_index, None)
        if pending.result is None:
            return {"kind": "concede"}
        return pending.result

    def _bot_decision(self, player_index: int, kind: str) -> dict:
        game = self._game
        player = game.players[player_index]
        if kind == "mulligan":
            return {"cards": bot.choose_mulligan(player)}
        if kind == "choice":
            return {"card": bot.choose_choice(player)}
        return bot.choose_main_action(player)

    def _apply_mulligan(self, player_index: int, decision: dict) -> None:
        player = self._game.players[player_index]
        choice = player.choice
        if choice is None:
            return
        entity_ids = decision.get("cards", [])
        cards = {c.entity_id: c for c in choice.cards}
        choice.choose(*[cards[eid] for eid in entity_ids if eid in cards])

    def _apply_choice(self, player_index: int, decision: dict) -> None:
        player = self._game.players[player_index]
        choice = player.choice
        if choice is None:
            return
        eid = decision.get("card")
        card = next((c for c in choice.cards if c.entity_id == eid), choice.cards[0])
        choice.choose(card)

    def _apply_main_action(self, player_index: int, decision: dict) -> None:
        game = self._game
        player = game.players[player_index]
        action = decision.get("action", decision)  # accept both shapes
        kind = action.get("kind")
        by_id = {e.entity_id: e for e in game.entities}
        if kind == "end_turn":
            game.end_turn()
        elif kind == "play_card":
            card = by_id.get(action["card"])
            if card is None:
                return
            target = by_id.get(action["target"]) if action.get("target") else None
            choose = by_id.get(action["choose"]) if action.get("choose") else None
            game.play_card(card, target, action.get("index", 0), choose)
        elif kind == "attack":
            src = by_id.get(action["source"])
            tgt = by_id.get(action["target"])
            if src is not None and tgt is not None:
                game.attack(src, tgt)
        elif kind == "hero_power":
            from fireplace.actions import PlayHeroPower
            hp = player.hero.power
            target = by_id.get(action["target"]) if action.get("target") else None
            game.main_power(hp, [PlayHeroPower(target)], target)
        elif kind == "concede":
            from fireplace.actions import Concede
            from hearthstone.enums import BlockType
            game.action_block(player, [Concede()], BlockType.PLAY)

    def _prompt(self, player_index: int, kind: str, data: dict) -> dict:
        """Ask a player for a decision (bot or human), returning the decision dict."""
        decision = self._ask(player_index, kind, data)
        if kind == "mulligan":
            self._apply_mulligan(player_index, decision)
        elif kind == "choice":
            self._apply_choice(player_index, decision)
        else:
            self._apply_main_action(player_index, decision)
        return decision

    def _run(self) -> None:
        game = self._game
        game.start()
        # Broadcast the post-start snapshot
        for i in range(2):
            self._send(i, {"type": "snapshot", "state": serialize(game, i)})
        while not game.ended:
            # Resolve any pending choices (mulligan, discover, choose-one...)
            pending = [i for i, p in enumerate(game.players) if p.choice is not None]
            if pending:
                i = pending[0]
                choice = game.players[i].choice
                kind = "mulligan" if type(choice).__name__ == "MulliganChoice" else "choice"
                data = {"type": "mulligan", "cards": [c.entity_id for c in choice.cards]} if kind == "mulligan" \
                    else {"type": "choice", "choice": choice_payload(choice)}
                self._prompt(i, kind, data)
                self._broadcast()
                continue
            # Main action phase
            i = 0 if game.current_player is game.players[0] else 1
            self._prompt(i, "main_action", {"type": "your_turn", "player": i})
            self._broadcast()
        for i in range(2):
            self._send(i, {"type": "game_over", "result": serialize(game, i)["result"]})

    def _broadcast(self) -> None:
        game = self._game
        for i in range(2):
            self._send(i, {"type": "snapshot", "state": serialize(game, i)})

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def join(self, timeout=None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    def snapshot_for(self, player_index: int) -> dict:
        return serialize(self._game, player_index)
```

**Important implementation note:** `self._send` is called from the worker thread, but the WS `send_text` must run on the asyncio loop. The caller of `set_send` (Task 12) MUST wrap its callback with `loop.call_soon_threadsafe(...)` so it is thread-safe. That wrapper belongs to Task 12; here we only define the callback contract.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_game_session.py -v`
Expected: 2 PASS. If `type(choice).__name__` mulligan detection fails (mulligan choices may be a plain `Choice` with the player in a mulligan state), adjust `_run` to detect mulligan via `game.players[i].mulligan_state` — and keep the two tests green.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat(backend): GameSession worker-thread bridge for engine networking"
```

---

### Task 12: Games API + WebSocket endpoint + session manager

**Files:**
- Create: `backend/app/engine/manager.py`
- Create: `backend/app/routers/games.py`
- Create: `backend/app/routers/matches.py`
- Modify: `backend/app/models.py` (add `Match`)
- Modify: `backend/app/main.py` (register routers)
- Test: `backend/tests/test_games_api.py`

**Interfaces:**
- Consumes: `app.engine.game_session.GameSession`, `app.engine.heroes.HERO_BY_CLASS`, `app.deps.get_current_user`, `app.models.Deck/Match`.
- Produces: `app.engine.manager.manager` (module-level singleton) with:
  - `manager.create_challenge(user, deck) -> str` (6-char code, in-memory, 30-min TTL)
  - `manager.join_challenge(code, user, deck) -> str` (creates + starts `GameSession`, returns game_id)
  - `manager.create_ai_game(user, deck) -> str` (starts vs bot)
  - `manager.get_session(game_id) -> GameSession | None`
  - `manager.attach_ws(game_id, player_index, websocket)` — wires `set_send` (thread-safe via `call_soon_threadsafe`) and starts the session when all participants are connected
- Router `app.routers.games.router` at `/api`:
  - `POST /api/games/challenges` body `{deck_id}` → `{code}`
  - `POST /api/games/challenges/{code}/join` body `{deck_id}` → `{game_id}`
  - `POST /api/games/ai` body `{deck_id}` → `{game_id}`
- Router `app.routers.matches.router` at `/api/matches`:
  - `GET /api/matches` → current user's match history
- WebSocket: `GET /api/games/{game_id}/ws?token=<jwt>` — described in the protocol below.

**WS message protocol (shared contract — do not diverge between client and server):**
```
Server → client:
  {"type":"snapshot","state":{...}}
  {"type":"mulligan","cards":[<entity_id>, ...]}
  {"type":"choice","choice":{"cards":[...],"min":1,"max":1}}
  {"type":"your_turn","player":0}
  {"type":"game_over","result":{"winner":0|1|null,"playstates":[...]}}
  {"type":"error","message":"..."}

Client → server:
  {"type":"mulligan","cards":[<entity_id>, ...]}          # [] = keep all
  {"type":"choice","card":<entity_id>}
  {"type":"action","action":{"kind":"play_card","card":id,"target":id|null,"index":n,"choose":id|null}}
  {"type":"action","action":{"kind":"attack","source":id,"target":id}}
  {"type":"action","action":{"kind":"hero_power","target":id|null}}
  {"type":"action","action":{"kind":"end_turn"}}
  {"type":"action","action":{"kind":"concede"}}
```

**Match model** (`backend/app/models.py`):
```python
class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(String(64), index=True)
    player1_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    player2_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    deck1_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deck2_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hero1: Mapped[str] = mapped_column(String(32))
    hero2: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="playing")  # playing|finished|forfeit
```

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_games_api.py`:
```python
def _register(client, username="gameplayer", password="pw123456"):
    client.post("/api/auth/register", json={
        "username": username, "email": f"{username}@example.com", "password": password,
    })
    return client.post("/api/auth/login", json={
        "username": username, "password": password,
    }).json()["access_token"]


def _mkdeck(client, token, hero="MAGE"):
    card_ids = ["CS2_029", "CS2_029"] + ["CS2_182"] * 28
    resp = client.post("/api/decks", json={"name": "D", "hero_class": hero, "card_ids": card_ids},
                       headers={"Authorization": f"Bearer {token}"})
    return resp.json()["id"]


def test_create_and_join_challenge(client):
    t1 = _register(client, "challenger")
    t2 = _register(client, "joiner")
    d1 = _mkdeck(client, t1)
    d2 = _mkdeck(client, t2)
    code = client.post("/api/games/challenges", json={"deck_id": d1},
                       headers={"Authorization": f"Bearer {t1}"}).json()["code"]
    resp = client.post(f"/api/games/challenges/{code}/join", json={"deck_id": d2},
                       headers={"Authorization": f"Bearer {t2}"})
    assert resp.status_code == 200
    assert resp.json()["game_id"]


def test_ai_game_created(client):
    token = _register(client, "aisolo")
    deck_id = _mkdeck(client, token)
    resp = client.post("/api/games/ai", json={"deck_id": deck_id},
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["game_id"]


def test_matches_history(client):
    token = _register(client, "historian")
    deck_id = _mkdeck(client, token)
    client.post("/api/games/ai", json={"deck_id": deck_id},
                headers={"Authorization": f"Bearer {token}"})
    resp = client.get("/api/matches", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_games_api.py -v`
Expected: FAIL (404).

- [ ] **Step 3: Implement manager, routers, WS**

`backend/app/engine/manager.py`:
```python
import asyncio
import secrets
import time
from datetime import datetime, timezone

from fastapi import WebSocket

from ..models import Match
from .game_session import GameSession


class _Challenge:
    def __init__(self, code, user_id, deck_id, hero, expires_at):
        self.code = code
        self.user_id = user_id
        self.deck_id = deck_id
        self.hero = hero
        self.expires_at = expires_at


class GameManager:
    def __init__(self):
        self._challenges: dict[str, _Challenge] = {}
        self._sessions: dict[str, GameSession] = {}
        self._ws: dict[str, dict[int, WebSocket]] = {}
        self._loops: dict[str, asyncio.AbstractEventLoop] = {}

    # ---- challenges ----
    def create_challenge(self, user, deck) -> str:
        code = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
        self._challenges[code] = _Challenge(
            code, user.id, deck.id, deck.hero_class,
            time.time() + 1800,
        )
        return code

    def join_challenge(self, code, user, deck) -> str:
        ch = self._challenges.get(code)
        if ch is None or ch.expires_at < time.time():
            raise KeyError("Challenge not found or expired")
        del self._challenges[code]
        return self._start(ch.user_id, ch.deck_id, ch.hero, user.id, deck.id, deck.hero_class)

    def create_ai_game(self, user, deck) -> str:
        from .heroes import HERO_BY_CLASS
        return self._start(user.id, deck.id, deck.hero_class,
                           None, None, HERO_BY_CLASS.get(deck.hero_class, "HERO_08"))

    # ---- sessions ----
    def _start(self, p1_user, p1_deck, p1_hero, p2_user, p2_deck, p2_hero) -> str:
        from ..db import SessionLocal
        from ..models import Deck, User
        import asyncio as _asyncio

        game_id = secrets.token_hex(8)
        session = GameSession(game_id, {
            "name": "P1", "hero": p1_hero,
            "deck": self._load_deck_cards(p1_deck),
            "is_bot": p1_user is None,
        }, {
            "name": "P2", "hero": p2_hero,
            "deck": self._load_deck_cards(p2_deck),
            "is_bot": p2_user is None,
        })
        self._sessions[game_id] = session
        # Persist match record (best-effort)
        _asyncio.run(self._persist_match(game_id, p1_user, p2_user, p1_deck, p2_deck, p1_hero, p2_hero))
        return game_id

    def _load_deck_cards(self, deck_id):
        from ..db import SessionLocal
        from ..models import Deck
        if deck_id is None:
            return []
        async def _load():
            async with SessionLocal() as db:
                deck = await db.get(Deck, deck_id)
                return deck.card_ids if deck else "[]"
        import json
        return json.loads(_asyncio.run(_load()))

    async def _persist_match(self, game_id, p1_user, p2_user, d1, d2, h1, h2):
        from ..db import SessionLocal
        async with SessionLocal() as db:
            db.add(Match(game_id=game_id, player1_id=p1_user, player2_id=p2_user,
                         deck1_id=d1, deck2_id=d2, hero1=h1, hero2=h2))
            await db.commit()

    def get_session(self, game_id: str) -> GameSession | None:
        return self._sessions.get(game_id)

    # ---- websocket ----
    def register_ws(self, game_id: str, player_index: int, ws: WebSocket, loop) -> None:
        self._ws.setdefault(game_id, {})[player_index] = ws
        self._loops[game_id] = loop
        session = self._sessions.get(game_id)
        if session is None:
            return
        session.set_send(player_index, lambda idx, msg: self._ws_send(game_id, idx, msg))
        self._maybe_start(game_id, session)

    def _ws_send(self, game_id: str, player_index: int, message: dict) -> None:
        loop = self._loops.get(game_id)
        ws = self._ws.get(game_id, {}).get(player_index)
        if loop is not None and ws is not None:
            loop.call_soon_threadsafe(self._do_send, ws, message)

    def _do_send(self, ws: WebSocket, message: dict) -> None:
        import asyncio
        asyncio.ensure_future(ws.send_json(message))

    def _maybe_start(self, game_id: str, session: GameSession) -> None:
        players = session.game.players
        needed = set()
        for i in range(2):
            is_bot = session._players[i]["is_bot"]
            if is_bot or i in self._ws.get(game_id, {}):
                needed.add(i)
        if needed == {0, 1} and not session.game.ended:
            session.start()


manager = GameManager()
```

**Correction note for the implementer:** the snippet above mixes blocking `asyncio.run` inside sync router paths (challenge/ai creation) which is acceptable because those endpoints run in the event loop and `asyncio.run` is *not* safe there. **Use an async session directly in the routers instead** — do DB work inside the async endpoint functions (the routers are async), and pass the loaded deck card lists into `manager._start`. Keep `_start` sync once it receives ready-made deck lists. Adjust `_start`/`_load_deck_cards`/`_persist_match` accordingly so no `asyncio.run` is used inside the event loop.

`backend/app/routers/games.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user
from ..engine.manager import manager
from ..models import Deck, Match, User
from ..schemas import DeckIdIn

router = APIRouter(prefix="/api/games", tags=["games"])


async def _load_deck(db: AsyncSession, deck_id: int, user: User) -> Deck:
    deck = await db.get(Deck, deck_id)
    if deck is None or deck.user_id != user.id:
        raise HTTPException(status_code=404, detail="Deck not found")
    return deck


@router.post("/challenges")
async def create_challenge(data: DeckIdIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    deck = await _load_deck(db, data.deck_id, user)
    code = manager.create_challenge(user, deck)
    return {"code": code}


@router.post("/challenges/{code}/join")
async def join_challenge(code: str, data: DeckIdIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    deck = await _load_deck(db, data.deck_id, user)
    try:
        game_id = manager.join_challenge(code, user, deck)
    except KeyError:
        raise HTTPException(status_code=404, detail="Challenge not found or expired")
    return {"game_id": game_id}


@router.post("/ai")
async def create_ai_game(data: DeckIdIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    deck = await _load_deck(db, data.deck_id, user)
    game_id = manager.create_ai_game(user, deck)
    return {"game_id": game_id}


async def _authorize_ws(game_id: str, token: str, db: AsyncSession) -> User:
    from ..deps import get_current_user
    from fastapi.security import HTTPAuthorizationCredentials
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    # reuse the dependency logic inline:
    try:
        return await get_current_user(creds, db)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.websocket("/{game_id}/ws")
async def game_ws(websocket: WebSocket, game_id: str, token: str, db: AsyncSession = Depends(get_session)):
    user = await _authorize_ws(game_id, token, db)
    session = manager.get_session(game_id)
    if session is None:
        await websocket.close(code=4004)
        return
    # Determine which player index this user is
    player_index = None
    game = session.game
    for i, name in enumerate(("P1", "P2")):
        # For PvP, map by user id stored in the Match record; simplest v1: player1 is the first connected
        pass
    # v1 simplification: challenger = index 0, joiner = index 1 (recorded at start); for AI, human = 0
    # Fallback: accept whichever slot is free
    await websocket.accept()
    loop = websocket.application_state.get("loop") if hasattr(websocket, "application_state") else None
    import asyncio
    loop = asyncio.get_running_loop()
    manager.register_ws(game_id, player_index or 0, websocket, loop)
    try:
        while True:
            msg = await websocket.receive_json()
            if msg.get("type") == "mulligan":
                session.submit_decision(0, {"cards": msg["cards"]})
            elif msg.get("type") == "choice":
                session.submit_decision(0, {"card": msg["card"]})
            elif msg.get("type") == "action":
                session.submit_decision(0, {"action": msg["action"]})
    except WebSocketDisconnect:
        session.submit_decision(0, {"action": {"kind": "concede"}})
```

`backend/app/routers/matches.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user
from ..models import Match, User

router = APIRouter(prefix="/api/matches", tags=["matches"])


@router.get("")
async def list_matches(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    rows = (
        await db.execute(
            select(Match).where((Match.player1_id == user.id) | (Match.player2_id == user.id))
            .order_by(Match.started_at.desc()).limit(50)
        )
    ).scalars().all()
    return rows
```

Add to `backend/app/schemas.py`:
```python
class DeckIdIn(BaseModel):
    deck_id: int
```

Register routers in `main.py`: games + matches.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_games_api.py -v`
Expected: 3 PASS. (The PvP/WS wiring is exercised in the manual test below; the API tests cover challenge lifecycle and AI-game creation.)

- [ ] **Step 5: Manual WS smoke test (scripted)**

Run a small script (outside pytest) that:
1. registers two users, builds decks,
2. creates a challenge, joins it,
3. connects a `websockets` client as each player to `/api/games/{game_id}/ws?token=...`,
4. asserts both receive a `snapshot`, then plays a few turns by sending `end_turn` actions and asserting both sides see updated `turn`.

Expected: the session advances turns. Fix any index-mapping bugs (which WS is player 0 vs 1) before moving on.

- [ ] **Step 6: Commit**

```bash
git add backend
git commit -m "feat(backend): challenge/AI game APIs, session manager, WebSocket endpoint"
```

---

### Task 13: Frontend auth (client API + login/register pages)

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/store/auth.ts`
- Create: `frontend/src/pages/Login.tsx`, `frontend/src/pages/Register.tsx`
- Modify: `frontend/src/router.tsx`, `frontend/src/App.tsx` (auth-aware layout)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `client.ts`: `apiFetch(path, opts)` (attaches Bearer token, throws on non-2xx), `login(username, password)`, `register(username, email, password)`, `me()`, `logout()`.
  - `types.ts`: `User`, `Deck`, `CardMeta` interfaces mirroring backend schemas.
  - `store/auth.ts`: Zustand store `useAuth` with `{user, token, setToken, setUser, clear}` and a `bootstrap()` that calls `me()` when a token exists.
  - Routes `/login`, `/register`; a `RequireAuth` wrapper redirecting to `/login`.

- [ ] **Step 1: Write the client + store**

`frontend/src/api/types.ts`:
```ts
export interface CardMeta {
  id: string;
  name: string;
  text?: string;
  cost: number | null;
  attack: number | null;
  health: number | null;
  type: string;
  cardClass: string;
  rarity: string;
  set: string;
  collectible?: boolean;
}

export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
}

export interface Deck {
  id: number;
  user_id: number;
  name: string;
  hero_class: string;
  card_ids: string[];
  created_at: string;
  updated_at: string;
}
```

`frontend/src/store/auth.ts`:
```ts
import { create } from "zustand";
import { apiFetch, me } from "../api/client";
import type { User } from "../api/types";

interface AuthState {
  user: User | null;
  token: string | null;
  ready: boolean;
  setToken: (t: string | null) => void;
  setUser: (u: User | null) => void;
  bootstrap: () => Promise<void>;
  logout: () => void;
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem("deepcards_token"),
  ready: false,
  setToken: (t) => {
    if (t) localStorage.setItem("deepcards_token", t);
    else localStorage.removeItem("deepcards_token");
    set({ token: t });
  },
  setUser: (u) => set({ user: u }),
  bootstrap: async () => {
    const token = get().token;
    if (!token) {
      set({ ready: true });
      return;
    }
    try {
      const user = await me();
      set({ user, ready: true });
    } catch {
      get().setToken(null);
      set({ ready: true });
    }
  },
  logout: () => {
    get().setToken(null);
    set({ user: null });
  },
}));
```

`frontend/src/api/client.ts`:
```ts
import type { User } from "./types";

const BASE = "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem("deepcards_token");
}

export async function apiFetch<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string> | undefined),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const resp = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = Array.isArray(body.detail) ? body.detail.join("; ") : (body.detail ?? detail);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(resp.status, detail);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export const login = (username: string, password: string) =>
  apiFetch<{ access_token: string; token_type: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

export const register = (username: string, email: string, password: string) =>
  apiFetch<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  });

export const me = () => apiFetch<User>("/auth/me");
```

- [ ] **Step 2: Build pages**

`frontend/src/pages/Login.tsx`:
```tsx
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { login } from "../api/client";
import { useAuth } from "../store/auth";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { setToken, setUser } = useAuth();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const res = await login(username, password);
      setToken(res.access_token);
      const user = await fetch("/api/auth/me", {
        headers: { Authorization: `Bearer ${res.access_token}` },
      }).then((r) => r.json());
      setUser(user);
      navigate("/");
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto mt-12 max-w-sm space-y-4">
      <h2 className="text-2xl font-bold">Sign in</h2>
      <input className="w-full rounded border border-slate-600 bg-slate-800 p-2" placeholder="Username"
        value={username} onChange={(e) => setUsername(e.target.value)} />
      <input type="password" className="w-full rounded border border-slate-600 bg-slate-800 p-2" placeholder="Password"
        value={password} onChange={(e) => setPassword(e.target.value)} />
      {error && <p className="text-red-400">{error}</p>}
      <button className="w-full rounded bg-amber-500 p-2 font-semibold text-slate-900">Sign in</button>
      <p className="text-sm text-slate-400">
        New here? <Link to="/register" className="text-amber-400">Create an account</Link>
      </p>
    </form>
  );
}
```

`frontend/src/pages/Register.tsx`: analogous — collects username/email/password, calls `register`, then navigates to `/login` on success.

- [ ] **Step 3: Wire auth into the router + app shell**

Modify `frontend/src/router.tsx` to add:
- `RequireAuth` component (reads `useAuth.user`; redirects to `/login` when null).
- Routes `/login`, `/register` (public), and wrap the app children in `RequireAuth`.

Modify `frontend/src/App.tsx` to call `useAuth().bootstrap()` once on mount and render a loading state while `!ready`.

- [ ] **Step 4: Verify**

Run: `cd frontend && npm run build`
Expected: builds clean. Then `npm run dev` + register/login against the running backend manually.

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat(frontend): auth client, store, login/register pages"
```

---

### Task 14: Card gallery page

**Files:**
- Create: `frontend/src/pages/Gallery.tsx`
- Create: `frontend/src/components/CardView.tsx`
- Modify: `frontend/src/router.tsx` (route `/cards`)

**Interfaces:**
- Consumes: `client.apiFetch<CardMeta[]>` for `GET /cards`, `CardMeta` type.
- Produces: `/cards` page with search + class filter + cost filter; grid of `CardView` components.

- [ ] **Step 1: Build CardView**

`frontend/src/components/CardView.tsx`:
```tsx
import type { CardMeta } from "../api/types";

export default function CardView({ card, size = "md" }: { card: CardMeta; size?: "sm" | "md" | "lg" }) {
  const h = size === "lg" ? 300 : size === "md" ? 210 : 150;
  const w = Math.round(h * 0.714);
  return (
    <div className="flex flex-col items-center" style={{ width: w }}>
      <div className="relative overflow-hidden rounded-lg border-2 border-slate-600 bg-gradient-to-b from-slate-700 to-slate-900"
        style={{ width: w, height: h }}>
        <div className="absolute inset-0 flex items-center justify-center text-6xl text-slate-600">
          {card.type === "SPELL" ? "✨" : "🛡"}
        </div>
        {card.cost !== null && (
          <span className="absolute left-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-amber-500 text-sm font-bold text-slate-900">
            {card.cost}
          </span>
        )}
        <span className="absolute bottom-1 left-2 right-2 truncate text-center text-xs font-semibold text-slate-100">
          {card.name}
        </span>
      </div>
      {(card.attack !== null || card.health !== null) && (
        <div className="mt-1 flex w-full justify-between text-xs text-slate-300">
          <span>{card.attack ?? "–"}/{card.health ?? "–"}</span>
          <span className="text-slate-500">{card.rarity}</span>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Build Gallery page**

`frontend/src/pages/Gallery.tsx`:
```tsx
import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import type { CardMeta } from "../api/types";
import CardView from "../components/CardView";

const CLASSES = ["MAGE", "WARRIOR", "SHAMAN", "ROGUE", "PALADIN", "HUNTER", "DRUID", "WARLOCK", "PRIEST", "DEMONHUNTER", "NEUTRAL"];

export default function Gallery() {
  const [cards, setCards] = useState<CardMeta[]>([]);
  const [q, setQ] = useState("");
  const [cls, setCls] = useState("");
  const [cost, setCost] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (cls) params.set("class", cls);
    if (cost !== "") params.set("cost", cost);
    apiFetch<CardMeta[]>(`/cards?${params.toString()}`).then((c) => {
      setCards(c);
      setLoading(false);
    });
  }, [q, cls, cost]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <input className="rounded border border-slate-600 bg-slate-800 p-2" placeholder="Search cards…"
          value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="rounded border border-slate-600 bg-slate-800 p-2" value={cls} onChange={(e) => setCls(e.target.value)}>
          <option value="">All classes</option>
          {CLASSES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select className="rounded border border-slate-600 bg-slate-800 p-2" value={cost} onChange={(e) => setCost(e.target.value)}>
          <option value="">Any cost</option>
          {Array.from({ length: 11 }, (_, i) => <option key={i} value={i}>{i}</option>)}
        </select>
      </div>
      {loading ? <p>Loading…</p> : (
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6">
          {cards.map((c) => <CardView key={c.id} card={c} size="sm" />)}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Wire route**

Add `{ path: "cards", element: <Gallery /> }` to the router children.

- [ ] **Step 4: Verify**

Run: `cd frontend && npm run build`
Expected: builds. Manually browse `/cards` against the backend and confirm filtering works.

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat(frontend): card gallery with search and filters"
```

---

### Task 15: Deck list + deck builder

**Files:**
- Create: `frontend/src/pages/DeckList.tsx`
- Create: `frontend/src/pages/DeckBuilder.tsx`
- Modify: `frontend/src/router.tsx` (routes `/decks`, `/decks/:id`)

**Interfaces:**
- Consumes: `client.apiFetch<Deck[]>` for deck CRUD; `CardMeta` for the card pool.
- Produces: `/decks` (list + "New deck" + delete), `/decks/:id` (builder: pick hero class, search/add/remove cards, live validation, save).

**Deck builder rules (client-side, mirrors server):** exactly 30 cards; ≤2 copies (≤1 legendary); only class/neutral cards.

- [ ] **Step 1: Build DeckList**

`frontend/src/pages/DeckList.tsx`:
```tsx
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import type { Deck } from "../api/types";

export default function DeckList() {
  const [decks, setDecks] = useState<Deck[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    apiFetch<Deck[]>("/decks").then(setDecks);
  }, []);

  async function remove(id: number) {
    await apiFetch(`/decks/${id}`, { method: "DELETE" });
    setDecks((d) => d.filter((x) => x.id !== id));
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">My Decks</h2>
        <button className="rounded bg-amber-500 px-4 py-2 font-semibold text-slate-900"
          onClick={() => navigate("/decks/new")}>New deck</button>
      </div>
      {decks.length === 0 && <p className="text-slate-400">No decks yet.</p>}
      {decks.map((d) => (
        <div key={d.id} className="flex items-center justify-between rounded border border-slate-700 bg-slate-800 p-3">
          <Link to={`/decks/${d.id}`} className="font-semibold">{d.name}</Link>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-400">{d.hero_class}</span>
            <span className="text-sm text-slate-400">{d.card_ids.length}/30</span>
            <button className="text-red-400" onClick={() => remove(d.id)}>Delete</button>
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Build DeckBuilder**

`frontend/src/pages/DeckBuilder.tsx`:
```tsx
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiFetch } from "../api/client";
import type { CardMeta, Deck } from "../api/types";

const CLASSES = ["MAGE", "WARRIOR", "SHAMAN", "ROGUE", "PALADIN", "HUNTER", "DRUID", "WARLOCK", "PRIEST", "DEMONHUNTER"];

export default function DeckBuilder() {
  const { id } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [heroClass, setHeroClass] = useState("MAGE");
  const [cards, setCards] = useState<string[]>([]); // card IDs
  const [pool, setPool] = useState<CardMeta[]>([]);
  const [q, setQ] = useState("");
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    apiFetch<CardMeta[]>(`/cards?limit=500`).then((all) => setPool(all));
    if (!isNew && id) {
      apiFetch<Deck>(`/decks/${id}`).then((d) => {
        setName(d.name);
        setHeroClass(d.hero_class);
        setCards(d.card_ids);
      });
    }
  }, [id, isNew]);

  const poolById = useMemo(() => Object.fromEntries(pool.map((c) => [c.id, c])), [pool]);
  const classCards = useMemo(
    () => pool.filter((c) => c.cardClass === heroClass || c.cardClass === "NEUTRAL"),
    [pool, heroClass]
  );
  const filtered = useMemo(
    () => classCards.filter((c) => c.name.toLowerCase().includes(q.toLowerCase())),
    [classCards, q]
  );

  function add(cardId: string) {
    const card = poolById[cardId];
    const maxCopies = card.rarity === "LEGENDARY" ? 1 : 2;
    const copies = cards.filter((c) => c === cardId).length;
    if (cards.length >= 30 || copies >= maxCopies) return;
    setCards([...cards, cardId]);
  }
  function removeAt(i: number) {
    setCards(cards.filter((_, idx) => idx !== i));
  }
  function validate(): string[] {
    const errs: string[] = [];
    if (cards.length !== 30) errs.push(`Deck has ${cards.length}/30 cards`);
    const counts: Record<string, number> = {};
    for (const cid of cards) counts[cid] = (counts[cid] ?? 0) + 1;
    for (const [cid, n] of Object.entries(counts)) {
      const card = poolById[cid];
      const max = card?.rarity === "LEGENDARY" ? 1 : 2;
      if (n > max) errs.push(`Too many copies of ${card?.name ?? cid}`);
    }
    return errs;
  }
  async function save() {
    const errs = validate();
    setErrors(errs);
    if (errs.length) return;
    const body = { name, hero_class: heroClass, card_ids: cards };
    if (isNew) await apiFetch<Deck>("/decks", { method: "POST", body: JSON.stringify(body) });
    else await apiFetch<Deck>(`/decks/${id}`, { method: "PUT", body: JSON.stringify(body) });
    navigate("/decks");
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="space-y-4">
        <input className="w-full rounded border border-slate-600 bg-slate-800 p-2" placeholder="Deck name"
          value={name} onChange={(e) => setName(e.target.value)} />
        <select className="w-full rounded border border-slate-600 bg-slate-800 p-2" value={heroClass}
          onChange={(e) => { setHeroClass(e.target.value); setCards([]); }}>
          {CLASSES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <input className="w-full rounded border border-slate-600 bg-slate-800 p-2" placeholder="Search cards…"
          value={q} onChange={(e) => setQ(e.target.value)} />
        <div className="grid max-h-96 grid-cols-3 gap-2 overflow-y-auto">
          {filtered.slice(0, 300).map((c) => (
            <button key={c.id} onClick={() => add(c.id)} disabled={cards.length >= 30}
              className="rounded border border-slate-700 bg-slate-800 p-2 text-left text-sm hover:border-amber-500">
              <div className="font-semibold">{c.name}</div>
              <div className="text-slate-400">{c.cost} mana · {c.attack ?? "–"}/{c.health ?? "–"}</div>
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-3">
        <h3 className="font-bold">Your deck ({cards.length}/30)</h3>
        {cards.map((cid, i) => (
          <div key={i} className="flex items-center justify-between rounded border border-slate-700 bg-slate-800 p-2">
            <span>{poolById[cid]?.name ?? cid}</span>
            <button className="text-red-400" onClick={() => removeAt(i)}>×</button>
          </div>
        ))}
        {errors.length > 0 && <ul className="text-sm text-red-400">{errors.map((e, i) => <li key={i}>{e}</li>)}</ul>}
        <button className="w-full rounded bg-amber-500 p-2 font-semibold text-slate-900" onClick={save}>Save deck</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Wire routes**

Add `/decks` and `/decks/:id` routes to the router.

- [ ] **Step 4: Verify**

Run: `cd frontend && npm run build`. Manually build a 30-card deck and save against the backend.

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat(frontend): deck list and deck builder with live validation"
```

---

### Task 16: Play lobby (challenge create/join + AI game)

**Files:**
- Create: `frontend/src/pages/Play.tsx`
- Modify: `frontend/src/router.tsx` (route `/play`)

**Interfaces:**
- Consumes: `client.apiFetch` for `/api/games/challenges`, `/api/games/challenges/{code}/join`, `/api/games/ai`; `useAuth.user`.
- Produces: `/play` page: pick a deck, "Play vs AI" button, "Create challenge" (shows code + link), "Join by code" input.

- [ ] **Step 1: Build Play page**

`frontend/src/pages/Play.tsx`:
```tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import type { Deck } from "../api/types";

export default function Play() {
  const [decks, setDecks] = useState<Deck[]>([]);
  const [deckId, setDeckId] = useState<number | "">("");
  const [code, setCode] = useState("");
  const [createdCode, setCreatedCode] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    apiFetch<Deck[]>("/decks").then(setDecks);
  }, []);

  async function vsAI() {
    if (!deckId) return setMsg("Pick a deck first");
    const { game_id } = await apiFetch<{ game_id: string }>("/games/ai", {
      method: "POST", body: JSON.stringify({ deck_id: deckId }),
    });
    navigate(`/game/${game_id}`);
  }
  async function createChallenge() {
    if (!deckId) return setMsg("Pick a deck first");
    const { code: c } = await apiFetch<{ code: string }>("/games/challenges", {
      method: "POST", body: JSON.stringify({ deck_id: deckId }),
    });
    setCreatedCode(c);
    setMsg(`Share code ${c} — or link: ${location.origin}/play?join=${c}`);
  }
  async function join() {
    if (!code || !deckId) return setMsg("Enter a code and pick a deck");
    const { game_id } = await apiFetch<{ game_id: string }>(`/games/challenges/${code}/join`, {
      method: "POST", body: JSON.stringify({ deck_id: deckId }),
    });
    navigate(`/game/${game_id}`);
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <h2 className="text-2xl font-bold">Play</h2>
      <select className="w-full rounded border border-slate-600 bg-slate-800 p-2"
        value={deckId} onChange={(e) => setDeckId(e.target.value ? Number(e.target.value) : "")}>
        <option value="">Choose a deck…</option>
        {decks.map((d) => <option key={d.id} value={d.id}>{d.name} ({d.hero_class})</option>)}
      </select>
      {msg && <p className="text-amber-400">{msg}</p>}
      <button className="w-full rounded bg-amber-500 p-2 font-semibold text-slate-900" onClick={vsAI}>Play vs AI</button>
      <button className="w-full rounded border border-amber-500 p-2 font-semibold text-amber-400" onClick={createChallenge}>Create challenge</button>
      {createdCode && (
        <div className="rounded border border-emerald-500 p-3 text-center">
          <div className="text-3xl font-black tracking-widest text-emerald-400">{createdCode}</div>
          <p className="text-sm text-slate-400">Send this code or link to a friend.</p>
        </div>
      )}
      <div className="flex gap-2">
        <input className="flex-1 rounded border border-slate-600 bg-slate-800 p-2 uppercase"
          placeholder="JOIN CODE" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} />
        <button className="rounded bg-slate-700 p-2 font-semibold" onClick={join}>Join</button>
      </div>
    </div>
  );
}
```

Handle the `?join=` query param in `Play.tsx` on mount (prefill `code`), so links shared by the creator auto-fill the code.

- [ ] **Step 2: Wire route + verify**

Add `/play` route; `npm run build`; manual test creating a challenge and joining.

- [ ] **Step 3: Commit**

```bash
git add frontend
git commit -m "feat(frontend): play lobby — AI game, challenge create/join"
```

---

### Task 17: Game board UI (WebSocket, store, rendering, interactions)

This is the largest frontend task. It consumes the exact snapshot/choice shapes from Tasks 9 and 12.

**Files:**
- Create: `frontend/src/store/game.ts`
- Create: `frontend/src/hooks/useGameSocket.ts`
- Create: `frontend/src/components/TargetingOverlay.tsx`
- Create: `frontend/src/components/ChoiceDialog.tsx`
- Create: `frontend/src/pages/GameBoard.tsx`
- Modify: `frontend/src/router.tsx` (route `/game/:gameId`)

**Interfaces:**
- Consumes: `GameState` snapshot JSON from the server (shape in Task 9), WS protocol in Task 12.
- Produces: `store/game.ts` Zustand store `useGame` with `{state: GameState|null, yourTurn, pending, connect(gameId, token), send(msg)}`; `GameBoard` page rendering the board and wiring interactions.

**Types (mirror the snapshot contract):**
```ts
export interface GameCard { entity_id: number; id?: string; name?: string; cost?: number; text?: string;
  atk?: number; max_health?: number; damage?: number; armor?: number; taunt?: boolean; stealthed?: boolean;
  divine_shield?: boolean; frozen?: boolean; exhausted?: boolean; num_attacks?: number; can_attack?: boolean;
  zone_position?: number; zone?: number; }
export interface GamePlayer { index: number; hero: GameCard; hero_power: GameCard | null; weapon: GameCard | null;
  deck_count: number; hand: GameCard[]; field: GameCard[]; secrets: GameCard[]; max_mana: number; mana: number;
  playstate: string; }
export interface GameState { turn: number; current_player: number; ended: boolean; result: { winner: number | null; playstates: string[] } | null;
  players: [GamePlayer, GamePlayer]; pending: { player: number; kind: string } | null; }
```

- [ ] **Step 1: Build the game store + socket hook**

`frontend/src/store/game.ts`:
```ts
import { create } from "zustand";
import type { GameState } from "../api/types";

type PendingType = "mulligan" | "choice" | null;

interface GameStore {
  state: GameState | null;
  ws: WebSocket | null;
  pending: PendingType;
  mulliganCards: number[];
  choiceCards: GameState["players"][number]["hand"];
  connect: (gameId: string, token: string) => void;
  send: (msg: unknown) => void;
  reset: () => void;
}

export const useGame = create<GameStore>((set, get) => ({
  state: null,
  ws: null,
  pending: null,
  mulliganCards: [],
  choiceCards: [],
  connect: (gameId, token) => {
    get().reset();
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/api/games/${gameId}/ws?token=${encodeURIComponent(token)}`);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "snapshot") set({ state: msg.state, pending: msg.state.pending?.kind ?? null });
      else if (msg.type === "mulligan") set({ pending: "mulligan", mulliganCards: msg.cards });
      else if (msg.type === "choice") set({ pending: "choice", choiceCards: msg.choice.cards });
      else if (msg.type === "your_turn") set({ pending: null });
      else if (msg.type === "game_over") {
        set({ pending: null });
      }
    };
    set({ ws });
  },
  send: (msg) => { const ws = get().ws; if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg)); },
  reset: () => { get().ws?.close(); set({ ws: null, state: null, pending: null, mulliganCards: [], choiceCards: [] }); },
}));
```

Add the `GameCard`/`GamePlayer`/`GameState` types to `frontend/src/api/types.ts`.

- [ ] **Step 2: Build interaction components**

`frontend/src/components/ChoiceDialog.tsx` — renders a modal when `pending === "choice"` listing `choiceCards`; clicking one sends `{type:"choice", card: <entity_id>}`.

`frontend/src/components/TargetingOverlay.tsx` — when the player is choosing a target, show a draggable "arrow" from source to the hovered valid target; on release send the action. For v1, implement a simpler interaction: click the source (sets `selectingFrom`), then click a target (sends the action). This avoids drag complexity while keeping the same UX goal.

- [ ] **Step 3: Build the GameBoard page**

`frontend/src/pages/GameBoard.tsx`:
```tsx
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "../store/auth";
import { useGame } from "../store/game";
import type { GameCard, GameState } from "../api/types";
import ChoiceDialog from "../components/ChoiceDialog";
import { CardView } from "../components/CardView";

export default function GameBoard() {
  const { gameId } = useParams();
  const token = useAuth((s) => s.token);
  const state = useGame((s) => s.state);
  const connect = useGame((s) => s.connect);
  const send = useGame((s) => s.send);
  const pending = useGame((s) => s.pending);
  const mulliganCards = useGame((s) => s.mulliganCards);
  const [selecting, setSelecting] = useState<GameCard | null>(null); // source entity for attack/play targeting
  const [targets, setTargets] = useState<number[]>([]);

  useEffect(() => {
    if (gameId && token) connect(gameId, token);
    return () => useGame.getState().reset();
  }, [gameId, token, connect]);

  const me = state?.players[0];
  const opp = state?.players[1];
  const yourTurn = state ? state.current_player === 0 && !state.ended : false;

  function pickTarget(card: GameCard) {
    if (!selecting) {
      // choose a playable card from hand
      if (card.can_attack) {
        setSelecting(card);
        setTargets((state?.players[1].field.map((m) => m.entity_id) ?? []).concat(
          state && !(state.players[1].hero.taunt) ? [state.players[1].hero.entity_id] : []
        ));
      } else if (card.zone === 4 && card.cost !== undefined && card.cost <= (me?.mana ?? 0)) {
        send({ type: "action", action: { kind: "play_card", card: card.entity_id, target: null, index: 0, choose: null } });
      }
      return;
    }
    // resolving target
    if (targets.includes(card.entity_id)) {
      send({ type: "action", action: { kind: "attack", source: selecting.entity_id, target: card.entity_id } });
    }
    setSelecting(null);
    setTargets([]);
  }

  function heroPower() {
    send({ type: "action", action: { kind: "hero_power", target: null } });
  }
  function endTurn() {
    send({ type: "action", action: { kind: "end_turn" } });
  }

  if (!state) return <p className="p-8 text-center text-slate-400">Connecting…</p>;

  return (
    <div className="relative flex min-h-[80vh] flex-col justify-between gap-4">
      {/* Opponent zone */}
      <section className="space-y-2">
        <div className="flex items-center justify-between text-sm text-slate-300">
          <span>{opp!.hero.name ?? "Opponent"}</span>
          <span>Deck: {opp!.deck_count} · Hand: {opp!.hand.length} · Mana {opp!.mana}/{opp!.max_mana}</span>
        </div>
        <div className="flex gap-2">{opp!.field.map((m) => <CardView key={m.entity_id} gameCard={m} />)}</div>
        <div className="text-center text-2xl font-bold text-red-400">
          {opp!.hero.max_health! - opp!.hero.damage!} ⚔ {opp!.hero.atk ?? 0}
        </div>
      </section>

      {/* Middle: status + actions */}
      <section className="flex items-center justify-center gap-4">
        <span className={`rounded px-3 py-1 font-semibold ${yourTurn ? "bg-amber-500 text-slate-900" : "bg-slate-700 text-slate-300"}`}>
          {yourTurn ? "Your turn" : "Opponent's turn"}
        </span>
        <button onClick={endTurn} disabled={!yourTurn} className="rounded bg-slate-700 px-4 py-1 font-semibold">End turn</button>
        <button onClick={heroPower} disabled={!yourTurn} className="rounded bg-slate-700 px-4 py-1 font-semibold">Hero power</button>
      </section>

      {/* Player zone */}
      <section className="space-y-2">
        <div className="text-center text-2xl font-bold text-emerald-400">
          {me!.hero.max_health! - me!.hero.damage!} ⚔ {me!.hero.atk ?? 0}
        </div>
        <div className="flex justify-center gap-3">
          {Array.from({ length: me!.max_mana }, (_, i) => (
            <span key={i} className={`h-5 w-5 rounded-full ${i < me!.mana ? "bg-amber-400" : "bg-slate-600"}`} />
          ))}
        </div>
        <div className="flex gap-2">{me!.field.map((m) => <CardView key={m.entity_id} gameCard={m} onClick={() => pickTarget(m)} />)}</div>
        <div className="flex min-h-[110px] items-end justify-center gap-2 rounded border border-slate-700 bg-slate-800/50 p-2">
          {me!.hand.map((c) => <CardView key={c.entity_id} gameCard={c} onClick={() => pickTarget(c)} />)}
        </div>
      </section>

      {pending === "choice" && <ChoiceDialog />}
      {pending === "mulligan" && (
        <div className="fixed inset-0 z-20 bg-black/70 p-8">
          <h3 className="text-center text-xl font-bold text-amber-400">Mulligan — keep or swap cards?</h3>
          <div className="mt-4 flex justify-center gap-3">
            {mulliganCards.map((eid) => <button key={eid} className="rounded border border-slate-500 p-2 text-slate-200">Card {eid}</button>)}
          </div>
          <div className="mt-6 flex justify-center gap-4">
            <button className="rounded bg-emerald-500 px-6 py-2 font-semibold text-slate-900"
              onClick={() => { send({ type: "mulligan", cards: [] }); }}>Keep all</button>
            <button className="rounded bg-red-500 px-6 py-2 font-semibold"
              onClick={() => { send({ type: "mulligan", cards: mulliganCards }); }}>Mulligan all</button>
          </div>
        </div>
      )}
    </div>
  );
}
```

Note: `CardView` must accept a `gameCard` prop (with `entity_id`) in addition to `CardMeta`. Extend `CardView` to render either a gallery `CardMeta` or a `GameCard` (add the `gameCard` prop and branch on `gameCard` presence). `zone === 4` is the hand (`Zone.HAND` enum value in Fireplace). Verify against the snapshot: the `zone` field on hand cards is `4`.

- [ ] **Step 4: Wire route + verify**

Add `/game/:gameId` route. Run `npm run build`. Manual end-to-end test: **human vs AI** — connect, mulligan, play a card, attack, end turn, win/lose.

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat(frontend): game board UI with WebSocket, targeting, mulligan, choices"
```

---

### Task 18: Profile + Admin pages

**Files:**
- Create: `frontend/src/pages/Profile.tsx`
- Create: `frontend/src/pages/Admin.tsx`
- Modify: `frontend/src/router.tsx` (routes `/profile`, `/admin`)

**Interfaces:**
- Consumes: `useAuth.user`, `client.apiFetch` for `/api/matches`, `/api/admin/users`.
- Produces: `/profile` (account info + match history), `/admin` (list users, toggle active, reset password — visible only to `role === "admin"`).

- [ ] **Step 1: Build Profile**

`frontend/src/pages/Profile.tsx`:
```tsx
import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import { useAuth } from "../store/auth";

interface MatchRow {
  id: number; game_id: string; hero1: string; hero2: string; status: string;
  winner_id: number | null; started_at: string;
}

export default function Profile() {
  const user = useAuth((s) => s.user);
  const [matches, setMatches] = useState<MatchRow[]>([]);
  useEffect(() => {
    apiFetch<MatchRow[]>("/matches").then(setMatches).catch(() => setMatches([]));
  }, []);
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h2 className="text-2xl font-bold">{user?.username}</h2>
      <p className="text-sm text-slate-400">{user?.email} · {user?.role}</p>
      <h3 className="text-lg font-bold">Match history</h3>
      <ul className="space-y-2">
        {matches.map((m) => (
          <li key={m.id} className="flex justify-between rounded border border-slate-700 bg-slate-800 p-2 text-sm">
            <span>{m.hero1} vs {m.hero2}</span>
            <span className="text-slate-400">{m.status}{m.winner_id != null && user ? (m.winner_id === user.id ? " · W" : " · L") : ""}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Build Admin**

`frontend/src/pages/Admin.tsx`:
```tsx
import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";

interface AdminUser { id: number; username: string; email: string; role: string; is_active: boolean; }

export default function Admin() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  useEffect(() => {
    apiFetch<AdminUser[]>("/admin/users").then(setUsers);
  }, []);
  async function toggle(u: AdminUser) {
    await apiFetch(`/admin/users/${u.id}`, { method: "PATCH", body: JSON.stringify({ is_active: !u.is_active }) });
    setUsers((us) => us.map((x) => (x.id === u.id ? { ...x, is_active: !x.is_active } : x)));
  }
  async function resetPassword(u: AdminUser) {
    const pw = prompt(`New password for ${u.username}:`);
    if (!pw) return;
    await apiFetch(`/admin/users/${u.id}/reset-password`, { method: "POST", body: JSON.stringify({ new_password: pw }) });
  }
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h2 className="text-2xl font-bold">Admin</h2>
      <table className="w-full text-left text-sm">
        <thead><tr className="border-b border-slate-700 text-slate-400">
          <th className="p-2">User</th><th>Role</th><th>Status</th><th></th></tr></thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} className="border-b border-slate-800">
              <td className="p-2">{u.username}<div className="text-xs text-slate-500">{u.email}</div></td>
              <td>{u.role}</td>
              <td>{u.is_active ? "Active" : "Disabled"}</td>
              <td className="space-x-2">
                <button className="text-amber-400" onClick={() => toggle(u)}>{u.is_active ? "Disable" : "Enable"}</button>
                <button className="text-slate-400" onClick={() => resetPassword(u)}>Reset pwd</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 3: Wire routes**

Add `/profile`; add `/admin` guarded so non-admins are redirected to `/`.

- [ ] **Step 4: Verify + commit**

```bash
cd frontend && npm run build
git add frontend
git commit -m "feat(frontend): profile and admin pages"
```

---

### Task 19: Docker packaging (backend + frontend + nginx)

**Files:**
- Create: `deploy/backend.Dockerfile`
- Create: `deploy/frontend.Dockerfile`
- Create: `deploy/nginx.conf`
- Create: `deploy/docker-compose.yml`
- Modify: `backend/requirements.txt` (pin `fireplace` to a git ref for reproducibility)

**Interfaces:**
- Produces: `deploy/docker-compose.yml` with services `backend` (uvicorn on :8000) and `frontend` (nginx on :8080 proxying `/api` and `/ws` to backend). Cards data baked into the backend image.

- [ ] **Step 1: Write backend Dockerfile**

`deploy/backend.Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /srv

# Install build deps for Fireplace (lxml etc. ship wheels; keep minimal)
COPY backend/requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r /srv/requirements.txt

COPY backend /srv/backend
WORKDIR /srv/backend

# Generate card data at build time so it's part of the image
RUN python scripts/build_cards.py /srv/backend/cards.json

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Write frontend Dockerfile + nginx**

`deploy/frontend.Dockerfile`:
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
```

`deploy/nginx.conf`:
```nginx
server {
  listen 8080;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;

  location /api/ {
    proxy_pass http://backend:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }

  location /ws {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
  }

  location / {
    try_files $uri /index.html;
  }
}
```

- [ ] **Step 3: Write docker-compose**

`deploy/docker-compose.yml`:
```yaml
services:
  backend:
    build:
      context: ..
      dockerfile: deploy/backend.Dockerfile
    environment:
      DEEPCHARD_SECRET: ${DEEPCHARD_SECRET:-change-me-in-production}
      DEEPCHARD_DB_URL: sqlite+aiosqlite:////data/deepcards.db
      DEEPCHARD_ADMIN_USER: ${DEEPCHARD_ADMIN_USER:-admin}
      DEEPCHARD_ADMIN_PASS: ${DEEPCHARD_ADMIN_PASS:-}
      CARDS_JSON_PATH: /srv/backend/cards.json
    volumes:
      - deepcards-data:/data
    expose:
      - "8000"

  frontend:
    build:
      context: ..
      dockerfile: deploy/frontend.Dockerfile
    ports:
      - "8080:8080"
    depends_on:
      - backend

volumes:
  deepcards-data:
```

- [ ] **Step 4: Verify the build locally**

Run: `cd deploy && docker compose build`
Expected: both images build. Then `docker compose up -d` and `curl -s http://localhost:8080/api/cards?q=fireball` returns Fireball.

- [ ] **Step 5: Commit**

```bash
git add deploy backend/requirements.txt
git commit -m "feat(deploy): Docker packaging with nginx reverse proxy"
```

---

### Task 20: Deploy to the Mac Mini

**Files:**
- Modify: nothing in the repo (deployment is operational).

**Steps:**
- [ ] **Step 1: Install Docker Desktop on the Mini**

SSH to `<mac-mini-user>@<mac-mini>` and install Docker Desktop (via Homebrew cask) plus enable it. The Mini has an M4 (Apple Silicon) and no Docker yet.

```bash
ssh <mac-mini-user>@<mac-mini-ip> \
  '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"' && \
ssh <mac-mini-user>@<mac-mini-ip> 'brew install --cask docker' 
```
Start Docker Desktop and wait for the engine (`docker info` succeeds).

- [ ] **Step 2: Push the repo and pull on the Mini**

```bash
git push origin main
ssh <mac-mini-user>@<mac-mini-ip> 'git clone https://github.com/Yihong89/deepcards.git ~/deepcards && cd ~/deepcards'
```

- [ ] **Step 3: Build + run**

```bash
ssh <mac-mini-user>@<mac-mini-ip> 'cd ~/deepcards/deploy && DEEPCHARD_SECRET=$(openssl rand -hex 32) DEEPCHARD_ADMIN_USER=admin DEEPCHARD_ADMIN_PASS=<choose> docker compose up -d --build'
```

- [ ] **Step 4: Verify**

```bash
curl -s http://<mac-mini-ip>:8080/api/health
curl -s "http://<mac-mini-ip>:8080/api/cards?q=fireball"
```
Expected: health OK and Fireball card JSON. Then open `http://<mac-mini-ip>:8080` in a browser, register, build a deck, play vs AI.

- [ ] **Step 5: Note for future sessions**

Record the Mini's current IP and how to reach the site in the project README (`docs/` note). Stop/start with `docker compose down` / `docker compose up -d`.

- [ ] **Step 6: Commit final docs**

```bash
git add .
git commit -m "docs: deployment notes for Mac Mini"
git push origin main
```

---

## Self-Review

**Spec coverage check** (each spec section → task):
- Goals/non-goals → Tasks 4–18 (v1 features) + 19–20 (deploy); roadmap items deliberately absent.
- Architecture (Fireplace + FastAPI + React) → Tasks 8–12 (engine bridge), 13–18 (frontend).
- Game networking bridge (§3.2) → Tasks 11–12.
- Data model (§3.3: users, decks, matches) → Tasks 4, 7, 12.
- Card data + placeholders (§3.4) → Task 3 (data), Tasks 14/17 render placeholders via `CardView`.
- REST API (§3.5) → Tasks 3,4,5,6,7,12.
- WebSocket (§3.6) → Task 12.
- Frontend pages (§3.7) → Tasks 13–18.
- PvE bot (§3.8) → Task 10 (decisions) + Task 12 (AI game wiring).
- Admin (§3.9) → Task 6 (API) + Task 18 (UI).
- Deployment (§4) → Tasks 19–20.
- Testing (§5) → every backend task has tests; Task 8 proves the engine loop; Task 12 includes a manual WS smoke test; Task 17 includes a manual human-vs-AI test.

**Placeholder scan:** no TODOs/TBDs; every step has concrete code. The one deliberate deferral is noted inline (engine API attribute names verified against the installed Fireplace in Task 8/9/10/11 with explicit fallback instructions — the code still runs as written against the cloned master).

**Type consistency:** the WS protocol, `GameState` snapshot shape, `CardMeta`, `GameCard`, `Deck`, `User`, and decision dict shapes are defined once (Task 9/12) and reused verbatim downstream (Tasks 17–18). `choice_payload`, `serialize`, `GameSession.submit_decision`, `manager.*` signatures match across Tasks 9→11→12.
