# Deepcards

A self-hosted, web-based Hearthstone-style card game. Players register, build decks from the full card library, challenge each other or play against a simple AI, all inside the browser.

- **Engine:** [Fireplace](https://github.com/jleclanche/fireplace) — a pure-Python Hearthstone rules re-implementation (~3,000 cards through the Ashes of Outlands expansion).
- **Backend:** FastAPI + uvicorn + SQLite, JWT auth, WebSocket game sessions.
- **Frontend:** React + Vite + TypeScript.
- **Deployment:** Docker Compose on an Apple Silicon Mac Mini.

## Status

Design phase. See `docs/superpowers/specs/` for the design document.
