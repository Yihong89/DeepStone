# 3D Battlefield (three.js + R3F) with TripoSR Assets — Design

Date: 2026-08-01
Status: Approved (pending spec review)

## Context & Goals

DeepStone's battlefield is currently a 2D DOM board (`GameBoard.tsx`, React + Tailwind). The
roadmap calls for a **3D battlefield rebuild** as the flagship feature: heroes and minions as 3D
models standing on a board plane, 3D animations, camera/scene polish. This spec designs the
migration to a **three.js (via React Three Fiber) board** with 3D models generated from card art
by **TripoSR**.

The game state layer is already ideal for this: the frontend is a thin "dumb view" over full JSON
snapshots pushed over WebSocket; all game rules live in the Python backend. Migrating the *board
rendering* therefore touches **no backend and no game logic** — the 3D board is a new renderer for
the same `GameState` and the same intent actions.

### Success criteria (v1)

A full game — vs AI and in PvP — plays correctly in 3D: unit placement, targeting, hero power,
mulligan, death, end turn — with the core animation set, at a playable framerate, with a working
2D⇄3D toggle. All existing features (hand, battle log, deck builder, gallery, auth) keep working.

## Decisions (recorded)

| Topic | Decision |
|---|---|
| Scope | **Board-only 3D** — the battlefield (minions, heroes, weapons) is 3D; hand, mana, buttons, log, mulligan/choice/end overlays stay React 2D. |
| Rendering lib | **React Three Fiber** (`@react-three/fiber` + `@react-three/drei` over `three`). |
| 3D assets | **TripoSR** generates GLBs for the ~11 heroes + the meta minion pool (~200–400, from `recommended_decks.json`); any unit without a GLB renders as a **card-plane stand** with its board art textured on. |
| Animations (v1) | **Core set**: attack lunge, card-play scale-in, death fade-out, hero-power glow, subtle camera nudge. No particle systems. |
| 2D ⇄ 3D | **User-facing toggle** (status bar button, persisted in `localStorage`), default **3D**; auto-fallback to 2D on WebGL init failure. The 2D board stays as a maintained alternate view. |
| Trajectory | **Feature branch + dev flag, then one flip commit** that ships both renderers with 3D default. |
| Backend | No changes to game logic, WS protocol, auth, or data model. Only an additive static mount for GLBs. |

## Architecture

`GameBoard.tsx` remains the HUD shell. The board zones — opponent field + hero/weapon row
(`GameBoard.tsx` ≈ lines 260–289) and player field + hero/weapon row (≈ lines 308–332) — are
extracted into a reusable **`Board2D`** component (identical rendering to today). `GameBoard` then
renders either `Board2D` or the new **`Battlefield3D`** based on the view mode:

```
<GameBoard>                              // HUD shell: hand, mana, status bar, log, overlays
  <ViewMode === "2d" ? <Board2D /> : <Battlefield3D />
  ...shared HUD sections...
```

Both board components are pure functions of the existing Zustand store (`store/game.ts`), which
already holds the full `GameState` snapshot from the WebSocket. Neither talks to the network; both
call the same `send({ type: "action", action })` for user intents.

### Proposed new/changed files

- `frontend/src/components/Board2D.tsx` — extracted current board zones (opponent + player field/hero).
- `frontend/src/components/Battlefield3D.tsx` — R3F `<Canvas>` + scene composition.
- `frontend/src/three/` — scene internals:
  - `Board.tsx` — table plane, camera, lights, slot layout.
  - `Unit3D.tsx` — one entity's mesh (GLB or card-plane), stats label, selection effects.
  - `models.ts` — GLB loader/cache, card-plane geometry, unit normalization (up-axis/scale/center).
  - `animations.ts` — core animation triggers (attack lunge, play, death, hero-power, camera nudge).
  - `pick.ts` — raycast hit → `entity_id` → selection handlers.
- `frontend/src/GameBoard.tsx` — view-mode selector + toggle button + `localStorage`.
- `backend/scripts/3d/generate_models.py` — TripoSR batch pipeline (manifest → GLBs → normalize).
- `backend/3dmodels/` — generated GLBs (**gitignored**, derived from private art).
- Serving: `backend/app/main.py` (`/models` mount), `frontend/vite.config.*` (`/models` proxy),
  `deploy/nginx.conf` (`/models/` location), `deploy/docker-compose.yml` (volume bind).

## The 3D Scene

- **Camera**: fixed perspective, Hearthstone-style — angled down at the board center; opponent's
  hero + minions at the far edge, player's at the near edge. No free orbit in v1; subtle
  programmatic nudges on big actions.
- **Board**: a dark table plane sized for 2×7 slots + hero positions; ambient + directional light.
- **Units** (`Unit3D`): each entity resolves to one of:
  - **GLB model** if `3dmodels/{id}.glb` exists — drei `useGLTF`, normalized to a uniform base scale
    (hero ≈ 1.6, minion ≈ 1.2), centered on its slot.
  - **Card-plane stand** otherwise — a rounded-rect plane textured with the square board art
    (`/images/cards_board/{id}.png`), tilted back on a small base. Guarantees no empty slots.
- **Live stats** (atk/HP/armor) render as crisp DOM labels via drei `<Html>`/Billboard above each
  unit — sharp text without WebGL font machinery.
- **Weapons** become small 3D card-planes beside each hero. **Secrets** remain DOM overlay chips
  (HUD-ish) above the opponent hero.
- **Selection/state cues**: selected / attackable / taunt → emissive pulse + a ring mesh under the
  unit, mirroring today's amber ring and purple taunt aura.
- **Art fallback chain**: GLB → card-plane with `cards_board` art → framed `cards` art → placeholder
  material. GLB load failure degrades to card-plane, never a crash.

## Interaction & Data Flow

- **Reconciliation**: each snapshot maps to `<Unit3D key={entity_id} …/>` per zone. R3F + React
  reconcile adds/removes/moves units automatically — the same model as the 2D board.
- **Picking**: raycast on click → `userData.entity_id` → the same selection/targeting handlers
  (`onMyMinion` / `onOppCharacter` / `onMyHand`), which call `send({ type: "action", action })`.
  Server-computed `targets` / `attack_targets` remain the source of legal targets.
- **Targeting overlay** ("Choose a target…") stays a DOM element over the canvas; legal targets glow.
- **Turn, hero power, mulligan, end turn**: unchanged HUD flow; the scene reflects the snapshot.

## Animations (v1 core set)

Triggered by the existing WS `event` messages (`store.game.lastEvent`) plus snapshot diffs:

| Trigger | Animation |
|---|---|
| `event.kind === "attack"` | Attacker lunges along the vector to the target; impact flash on the target. |
| New entity in snapshot | Scale-in + rise from the hand side (card played). |
| Removed entity | Fade + scale-out (death). |
| `event.kind === "hero_power"` | Glow pulse on the hero. |
| Turn change / big action | Subtle camera nudge. |

Slot movement lerps over ~200 ms via `useFrame` interpolation — no tween library. No particle
systems, projectiles, or dynamic lighting in v1 (roadmap follow-ups).

## TripoSR Asset Pipeline

- **Manifest**: card ids to model — the ~11 hero card ids + the unique minion ids referenced by
  `frontend/src/data/recommended_decks.json` (~200–400 total).
- **Script** (`backend/scripts/3d/generate_models.py`): for each manifest id, if
  `backend/3dmodels/{id}.glb` is missing and board art exists, run TripoSR (`run.py`), then
  **normalize** the output (up-axis, recenter, uniform scale) and save the GLB. Skips failures
  per-card (those units render as card-planes).
- **Gitignored**: `**/3dmodels/` — GLBs are derived from Blizzard's private art and must never be
  committed (same rule as `**/images/`).
- **Runtime**: TripoSR is CUDA/PyTorch. Generation is a **one-time offline batch** — run on this
  M4 Mac (MPS/CPU, slower) or hosted (Hugging Face Space / Tripo API). Never in CI.

## Serving GLBs (dev + prod)

Mirror the existing `/images` pattern end-to-end:

1. `backend/app/main.py`: `app.mount("/models", StaticFiles(directory=backend/3dmodels), ...)`.
2. `frontend/vite.config.*`: proxy `/models` → `http://localhost:8000` (like `/images`).
3. `deploy/nginx.conf`: add a `/models/` location proxying to `backend:8000/models/` (like `/images/`).
4. `deploy/docker-compose.yml`: bind-mount `../backend/3dmodels` into the backend container
   (like the existing `../backend/images` mount).

## Performance & Error Handling

- WebGL init failure → **auto-fallback to the 2D board** (the toggle remains available).
- GLB load failure / missing art → card-plane → placeholder. No hard failures.
- Cap `devicePixelRatio` at 2; dispose GLTF geometries on unmount; the scene renders at most ~14
  minions + 2 heroes, so the draw load is small.

## 2D ⇄ 3D Toggle

- Button in the status/action bar (next to the existing mute button): **2D | 3D**.
- Persisted in `localStorage` (`deepstone_view_mode`); default **3D**.
- On WebGL init failure, force 2D (and notify via the button state).
- `Board2D` remains a **maintained** view: regressions there still matter because it's user-reachable.

## Testing & Rollout

Milestones on branch `feat/3d-battlefield` (main stays green; Mini trail keeps working):

1. **Scaffold** — add `three` + `@react-three/fiber` + `@react-three/drei`; `Battlefield3D` renders
   a static board + heroes; view toggle swaps board zones (persisted `localStorage` view mode;
   `?view=` URL param as a dev convenience while building).
2. **Units + interaction** — card-plane minions, stat badges, raycast targeting, play / attack /
   hero-power end-to-end vs AI.
3. **Animations** — core set wired to `event`s + snapshot diffs.
4. **Assets** — TripoSR script + run heroes/meta pool; GLB loading + normalization + fallback.
5. **Flip** — tune camera/lighting/layout; ship both renderers, 3D default, toggle visible; PR to
   `main` → trail updates the Mini.

**Definition of done (v1)**: a full game vs AI and in PvP plays correctly in 3D with core
animations at playable framerate, and the 2D board remains reachable via the toggle.

**Verification**: backend tests untouched (no backend logic changes); frontend `tsc -b && vite build`
must pass; manual playtest on both the 3D and 2D paths; then the trail (commit → push → Mini pull)
is the deploy check.

## Non-Goals (v1)

- Particle systems / spell projectiles / dynamic lighting (roadmap follow-ups).
- Free-orbit camera, full-3D HUD (hand, buttons, overlays in the scene).
- Modeling all ~3,875 cards (meta pool only; card-plane fallback for the rest).
- Unity, mobile touch, text-to-3D, and localization.
