# Deepcards — Design Document

**Date:** 2026-08-01
**Status:** Approved (design phase)

A self-hosted, web-based Hearthstone-style card game. Registered users own the full card library, build any legal deck, and play head-to-head (challenge via code/link) or against a simple AI bot. An admin panel manages accounts.

---

## 1. Goals & non-goals

### Goals (v1)
- Users register, log in, and manage their profile.
- Every user has **all cards** from the start — no collecting/booster economy.
- **Deck builder**: build any legal deck (30 cards, class-legal, ≤2 non-legendary / ≤1 legendary).
- **PvP**: challenge another registered user via a short code or link, then play a full game in the browser.
- **PvE**: play against a minimal functional AI bot.
- **Admin**: list users, enable/disable accounts, reset passwords.
- Card visuals are **placeholders** now, swappable for real images later without code changes.
- Self-hosted on the user's Apple Silicon Mac Mini via Docker Compose.

### Non-goals (v1) / Roadmap
- Sophisticated AI and difficulty levels.
- Newer card sets (post-Ashes of Outlands) and rules-engine updates.
- Matchmaking queue.
- In-app card-art generation/upload UX (admin file-drop is fine).
- Replays, spectating, chat.
- Mobile-native polish.

---

## 2. Architecture

```
Browser (React SPA)
   │  REST: auth, decks, cards, admin, matches
   │  WebSocket: /ws/game/{id}  — state snapshots + choices (send), actions (receive)
   ▼
Backend: FastAPI + uvicorn
   ├─ REST layer (routers: auth, decks, cards, games, admin)
   ├─ Auth: JWT (access token), bcrypt password hashing, role field (user/admin)
   ├─ GameManager (asyncio)
   │    └─ GameSession per match:
   │         • Fireplace Game running in a worker thread
   │         • NetworkController per player — bridges engine choices ↔ WebSockets via queues
   │         • State serializer → JSON snapshots broadcast after each action
   ├─ SQLite — users, decks, matches (game state is in-memory only)
   └─ Static: /images/cards/{card_id}.png (placeholder; later real art)
```

Key decision: **Fireplace solves the rules engine** (~3,000 cards, tested upstream). All project code sits around it: networking bridge, serialization, API, frontend.

---

## 3. Components in detail

### 3.1 Fireplace engine (dependency)
- Pure-Python Hearthstone re-implementation, AGPLv3, no Blizzard assets.
- Covers Basic/Classic/Hall of Fame plus expansions Naxxramas → Ashes of Outlands (~3,000+ cards).
- Bundled with card data via `python-hearthstone` (CardDefs.xml).
- Used as-is; no upstream code changes in v1 (fork pin if we later need engine fixes).

### 3.2 Game networking bridge (core new code)
Fireplace is synchronous and blocking: a `Controller` decides each action. We wrap each human in a `NetworkController`:

1. Game runs in a **worker thread** (dedicated per session) so it never blocks the asyncio loop.
2. When the engine needs a decision (mulligan, play card, attack, target, Discover choice…), the controller:
   - serializes the choice/options → sends over that player's WebSocket → **blocks** on an event/queue.
3. The client's action reply is mapped to a Fireplace call; the engine advances.
4. A fresh **state snapshot** is serialized and broadcast to both players.

**Hidden-information handling** in the serializer: opponent hand shown only as a count; opponent secrets masked; deck shown as count; only revealed/randomly-drawn cards visible to the owning player.

**Action protocol (client→server):** `MULLIGAN`, `PLAY_CARD`, `ATTACK`, `HERO_POWER`, `USE_WEAPON`, `END_TURN`, `CHOICE`.

### 3.3 Data model (SQLite)
- `users`: id, username (unique), email (unique), password_hash, role (`user`|`admin`), is_active, created_at.
- `decks`: id, user_id, name, hero_class, card_ids (JSON array of Fireplace card IDs), created_at, updated_at.
- `matches`: id, game_id, player1_id, player2_id (nullable → AI), winner_id (nullable → draw), hero_classes, deck1_ids, deck2_ids, started_at, ended_at, status.

Game *state* is in-memory per session; only match outcomes/history are persisted.

### 3.4 Card data pipeline + placeholders
- One-time generation script produces a static `cards.json` from Fireplace's card universe (via `python-hearthstone`), filtered to collectible cards — the deck builder and the game read the **same** card set.
- Images: each card maps to `/images/cards/{card_id}.png`. v1 serves generated placeholders; later AI-generated art is dropped into that folder (per-card file scheme ⇒ no code changes). `images/cards/` is gitignored.

### 3.5 REST API
- `POST /auth/register`, `POST /auth/login` → JWT; `GET /auth/me`.
- `GET /cards` — search/filter for the gallery + deck builder (name, class, cost, set, keyword).
- `POST/GET /decks`, `GET/PUT/DELETE /decks/{id}` — server-side validation: exactly 30 cards, class-legal, ≤2 copies of non-legendary, ≤1 legendary.
- `POST /games` → creates a challenge, returns a short code; `GET /games/join/{code}` → resolves to a game room.
- `GET /matches` — the user's match history.
- Admin: `GET /admin/users`, `PATCH /admin/users/{id}` (enable/disable), `POST /admin/users/{id}/reset-password`.
- Static: `/images/cards/{card_id}.png`.

### 3.6 WebSocket
- `GET /ws/game/{game_id}?token=<jwt>`.
- Server→client: game-state snapshots and choice prompts.
- Client→server: actions listed in §3.2.
- Disconnect handling: grace period; opponent notified; match can be resigned/forfeited.

### 3.7 Frontend (React + Vite + TypeScript)
Pages:
- **Login / Register**
- **Lobby** (home)
- **Card Gallery** (browse/search all cards)
- **Decks** (list) + **Deck Builder** (`/decks/:id`) — drag/filter UI with live legal-deck validation
- **Play** — create a challenge (shows code/link) or join by code
- **Game Board** (`/game/:id`) — the real-time match UI
- **Profile**
- **Admin** — user management

**Game Board** requirements: opponent + player rows (hands, board, hero + hero power + weapon), mana crystals, end-turn button, targeting arrows for attacks/effects, choice dialogs (Discover etc.), card hover tooltips, placeholder card art.

State: server snapshots applied through a client-side reducer (Zustand). Styling: Tailwind CSS.

### 3.8 PvE bot (minimal)
- v1 ships one simple heuristic `Controller`: play highest-cost playable card, attack/trade sensibly, use hero power when idle. Enough for a functional PvE mode. Reuses the same NetworkController bridge shape (bot supplies choices directly in-thread).

### 3.9 Admin
- List users, toggle `is_active`, reset password. (Later: match logs, card-art upload.)

---

## 4. Deployment (Mac Mini, Apple M4 / 16 GB)

**Docker Compose**, one `docker compose up -d`:
- `backend`: uvicorn serving FastAPI (binds WebSocket + REST).
- `frontend`: nginx serving the built React SPA (static), proxying `/api` + `/ws` to backend.
- SQLite data volume (no separate DB container in v1).
- Card data (`cards.json`) baked into the backend image at build time.

Dev workflow: run backend + frontend locally on the development Mac first; deploy to the Mini when green. Docker Desktop to be installed on the Mini.

---

## 5. Testing

- **Unit:** auth, deck validation, serializer (incl. hidden-info rules), REST endpoints.
- **Integration:** scripted two-bot games driven through a full `GameSession` + WebSocket path — proves the loop end-to-end before any human plays.
- **Manual:** one human-vs-bot and one human-vs-human game on the deployed stack.

---

## 6. Tech stack summary

| Layer | Choice |
|---|---|
| Rules engine | Fireplace (Python, AGPLv3) + python-hearthstone data |
| Backend | FastAPI, uvicorn, SQLAlchemy, aiosqlite, PyJWT, passlib/bcrypt |
| Frontend | React 18, Vite, TypeScript, React Router, Zustand, Tailwind |
| Game transport | WebSocket (FastAPI native) + threading bridge |
| Storage | SQLite (v1) |
| Deploy | Docker Compose on Apple Silicon Mac Mini |

---

## 7. Roadmap (deferred)
1. Smarter AI + difficulty levels.
2. Newer card sets + rules-engine updates.
3. Matchmaking queue.
4. Real card-art generation + upload UX.
5. Replays / spectate / match logs in admin.
6. Mobile polish.
