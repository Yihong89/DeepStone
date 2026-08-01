# Deepcards

A self-hosted, web-based Hearthstone-style card game. Players register, build decks from the full card library, challenge each other or play against a simple AI, all inside the browser.

- **Engine:** [Fireplace](https://github.com/jleclanche/fireplace) — a pure-Python Hearthstone rules re-implementation (~2,500 collectible cards through the Scholomance Academy expansion).
- **Backend:** FastAPI + uvicorn + SQLite, JWT auth, WebSocket game sessions (`backend/`).
- **Frontend:** React + Vite + TypeScript (`frontend/`).
- **Deployment:** Docker Compose (`deploy/`) — intended for an Apple Silicon Mac Mini.

## Features

- Register / log in (JWT), admin user management.
- Full card gallery + deck builder with server-side deck validation (30 cards, class-legal, copy limits).
- Play vs AI or challenge another player via a shareable code/link.
- Real-time game board over WebSocket: mulligan, play cards, attack, hero powers, Discover choices.

## Running locally

Backend (port 8000):

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/ensure_fireplace_data.py   # fetch real CardDefs.xml (git-LFS)
.venv/bin/python scripts/build_cards.py             # generate cards.json
.venv/bin/uvicorn app.main:app --port 8000
```

Frontend (port 5173, proxies to :8000):

```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173.

## Docker

```bash
cd deploy
docker compose up -d --build
# site on http://<host>:8080
```

## Roadmap

- Smarter AI + difficulty levels.
- Newer card sets + rules-engine updates.
- Matchmaking queue.
- Real card-art generation + upload UX.
- Replays / spectate / match logs in admin.
- Mac Mini deployment (Docker Desktop install + compose).

## Notes

- Card images are Blizzard's **copyrighted art**, used here **privately** only. They live in `backend/images/` (gitignored via `**/images/`) and are **never committed**. Re-download with `python scripts/download_card_images.py`.
- A **pre-commit guard** (`.githooks/pre-commit`) refuses any commit that would add a file under an `images/` directory. Enable it in any clone with: `git config core.hooksPath .githooks`.
- Fireplace's bundled `CardDefs.xml` is stored in git-LFS; `pip install` leaves a stub. `scripts/ensure_fireplace_data.py` downloads the real file (SHA-256 verified).
