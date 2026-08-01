# Deepcards Roadmap

Current status: **v1 shipped** — register/login, full card gallery, deck builder with
validation, play vs AI and challenge-based PvP, real-time board with battle log,
card art + audio (private), admin panel. See `README.md` for how to run it.

Items are roughly ordered by priority/impact. Checkboxes reflect progress.

## Gameplay & AI
- [ ] **Smarter AI + difficulty levels** (Easy / Medium / Hard) — the current bot is a simple heuristic (play on curve, trade sensibly).
- [ ] **Matchmaking queue** — a "find game" button that pairs you with a random online opponent (currently PvP is via shareable challenge codes).
- [ ] **Ranked ladder / MMR** — persistent rating and seasons.
- [ ] **Replays & spectate** — record match events, replay them, let others watch live.
- [ ] **More board polish** — floating damage numbers, card-play animations, board glow effects.
- [ ] **More keywords & mechanics** — expand the hover keyword reference as new cards are added.

## Content
- [ ] **Newer card sets + rules-engine updates** — Fireplace currently implements cards through the Scholomance Academy expansion (~2020). Adding newer sets means hand-writing card logic in the engine.
- [ ] **Card balance & curated pools** — opt-in format/ban-list presets.
- [ ] **Tavern Brawl–style modes** — rotate custom rulesets.

## UI / UX
- [ ] **Real card-art generation + upload UX** — currently images are placeholders/private local files; add an admin flow to upload art per card.
- [ ] **Mobile polish** — responsive board layout, touch targeting.
- [ ] **Accessibility** — keyboard navigation, screen-reader-friendly board, colorblind-safe indicators.
- [ ] **Localization** — the card data supports multiple locales; wire up language switching.

## Administration & Community
- [ ] **Match logs in the admin panel** — inspect any match's event history.
- [ ] **User management extras** — ban/unban with reasons, role tiers, audit log.
- [ ] **Leaderboards & match stats** — per-class win rates, deck performance.

## Infrastructure
- [ ] **Mac Mini deployment** — install Docker Desktop, `docker compose up`, serve on the LAN/domain.
- [ ] **HTTPS + custom domain** — reverse proxy (Caddy/nginx) with TLS.
- [ ] **CI / CD** — automated backend tests + frontend build on push, auto-deploy.
- [ ] **Backups** — scheduled SQLite snapshot + media backup.

---

### Contributing ideas
This is a self-hosted hobby project. Features are driven by what's fun to play and
build. If you'd like something on this list moved up, just say so.
