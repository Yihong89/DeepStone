# 3D Battlefield (three.js + R3F) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 2D battlefield board with a 3D board rendered by React Three Fiber, using TripoSR-generated GLB models for heroes and meta minions, with a user-facing 2D⇄3D toggle that defaults to 3D.

**Architecture:** `GameBoard` stays the HUD shell (hand, status bar, battle log, overlays). The current board zones are extracted into `Board2D`. A new `Battlefield3D` (R3F `<Canvas>`) renders the same Zustand `GameState` snapshot — pure logic modules handle board layout, unit-resolution, snapshot diffing, and model normalization, and are unit-tested. TripoSR GLBs are served from a new `/models` static mount (mirroring `/images`). The view mode is a persisted `localStorage` value with a UI toggle.

**Tech Stack:** React 18.3.1, TypeScript, Vite 5, `three` + `@react-three/fiber@8` + `@react-three/drei@9` (v8 required — React 19 would need R3F v9), Zustand 5, Vitest (new devDependency). Backend: FastAPI + pytest. Asset generation: TripoSR (`VAST-AI-Research/TripoSR`) + `trimesh` for OBJ→GLB.

## Global Constraints

- **R3F must be v8** (`@react-three/fiber@8`) and drei v9 — the app is on React 18.3.1; R3F v9 requires React 19.
- **No backend game-logic changes.** The only backend change is an additive static mount (`/models`) and its docker/nginx wiring.
- **`backend/3dmodels/` is gitignored** — GLBs derive from Blizzard's private art. The pre-commit hook (`core.hooksPath=.githooks`) already refuses `images/` additions; never `git add -f` a 3d model.
- **Existing frontend has no test runner.** Vitest is added for the pure-logic modules only. R3F components are verified by `tsc -b && vite build` + manual playtest (spec's verification section). Do not add jsdom/Playwright unless the task says so.
- **Model normalization happens at load time in the browser** (single owner) — the TripoSR script does NOT normalize geometry.
- Commits must not include files under `backend/images/` or `backend/3dmodels/`.

---

### Task 1: Scaffold — dependencies, vitest, gitignore

**Files:**
- Modify: `frontend/package.json` (deps + test script)
- Create: `frontend/vitest.config.ts`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `npm test` → `vitest run` (passes with no tests via `passWithNoTests`); `.gitignore` blocks `**/3dmodels/`.

- [ ] **Step 1: Install the 3D + test dependencies**

```bash
cd frontend
npm i three @react-three/fiber@8 @react-three/drei@9
npm i -D vitest
```

- [ ] **Step 2: Add the test script to `frontend/package.json`**

In the `"scripts"` block add: `"test": "vitest run"`.

- [ ] **Step 3: Create `frontend/vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
    passWithNoTests: true,
  },
});
```

- [ ] **Step 4: Add `3dmodels` to the repo `.gitignore`**

Append this line to the existing `.gitignore` (under the card-art section):

```
**/3dmodels/
```

- [ ] **Step 5: Verify build still passes and vitest runs**

```bash
cd frontend && npm run build
cd frontend && npx vitest run
```
Expected: build succeeds; vitest reports success with 0 tests.

- [ ] **Step 6: Commit**

```bash
git add .gitignore frontend/package.json frontend/package-lock.json frontend/vitest.config.ts
git commit -m "chore(3d): scaffold three/R3F/drei + vitest; gitignore 3dmodels"
```

---

### Task 2: View-mode module (pure, TDD)

**Files:**
- Create: `frontend/src/three/viewMode.ts`
- Test: `frontend/src/three/viewMode.test.ts`

**Interfaces:**
- Consumes: nothing (a `StorageLike` is injected so tests need no DOM).
- Produces:
  - `type ViewMode = "2d" | "3d"`
  - `const VIEW_MODE_KEY = "deepstone_view_mode"`
  - `interface StorageLike { getItem(key: string): string | null; setItem(key: string, value: string): void }`
  - `getViewMode(storage?: StorageLike): ViewMode` — stored value, default `"3d"`.
  - `setViewMode(mode: ViewMode, storage?: StorageLike): void`
  - `effectiveViewMode(webglOk: boolean, mode: ViewMode): ViewMode` — forces `"2d"` when `!webglOk`.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import {
  getViewMode, setViewMode, effectiveViewMode, VIEW_MODE_KEY, type ViewMode, type StorageLike,
} from "./viewMode";

function fakeStorage(init: Record<string, string> = {}): StorageLike {
  const m = new Map(Object.entries(init));
  return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => { m.set(k, v); } };
}

describe("viewMode", () => {
  it("defaults to 3d when nothing is stored", () => {
    expect(getViewMode(fakeStorage())).toBe("3d");
  });
  it("reads the stored value", () => {
    expect(getViewMode(fakeStorage({ [VIEW_MODE_KEY]: "2d" }))).toBe("2d");
  });
  it("persists via setViewMode", () => {
    const s = fakeStorage();
    setViewMode("2d", s);
    expect(getViewMode(s)).toBe("2d");
  });
  it("treats unknown stored values as 3d", () => {
    expect(getViewMode(fakeStorage({ [VIEW_MODE_KEY]: "banana" }))).toBe("3d");
  });
  it("falls back to 2d when WebGL is unavailable", () => {
    expect(effectiveViewMode(false, "3d")).toBe("2d");
    expect(effectiveViewMode(true, "3d")).toBe("3d");
    expect(effectiveViewMode(false, "2d")).toBe("2d");
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && npx vitest run src/three/viewMode.test.ts`
Expected: FAIL — module `./viewMode` not found.

- [ ] **Step 3: Implement `frontend/src/three/viewMode.ts`**

```ts
export type ViewMode = "2d" | "3d";
export const VIEW_MODE_KEY = "deepstone_view_mode";

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export function getViewMode(storage: StorageLike = localStorage): ViewMode {
  const v = storage.getItem(VIEW_MODE_KEY);
  return v === "2d" || v === "3d" ? v : "3d";
}

export function setViewMode(mode: ViewMode, storage: StorageLike = localStorage): void {
  storage.setItem(VIEW_MODE_KEY, mode);
}

/** The mode actually rendered: falls back to 2d when WebGL is unavailable. */
export function effectiveViewMode(webglOk: boolean, mode: ViewMode): ViewMode {
  return webglOk ? mode : "2d";
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/three/viewMode.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/three/viewMode.ts frontend/src/three/viewMode.test.ts
git commit -m "feat(3d): view-mode module with localStorage persistence and WebGL fallback"
```

---

### Task 3: Extract the 2D board into `Board2D` (no behavior change)

**Files:**
- Create: `frontend/src/components/Board2D.tsx`
- Modify: `frontend/src/pages/GameBoard.tsx`

**Interfaces:**
- Consumes: `HeroView`, `CardView`, `GameCard`, `GamePlayer` (existing components/types).
- Produces:
  - `function Board2D(props: { me: GamePlayer; opp: GamePlayer; yourTurn: boolean; selection: Selection | null; targetIds: Set<number>; onMyMinion(c: GameCard): void; onOppCharacter(c: GameCard): void }): JSX.Element`
  - `function ManaCrystals(props: { available: number; total: number }): JSX.Element` (exported — the 3D board reuses it)

The two board `<section>`s (opponent zone + player zone) move out of `GameBoard.tsx` **verbatim** into `Board2D`, including their `ManaCrystals`, `WeaponView`, and `SecretMarker` usage. `WeaponView` and `SecretMarker` move into `Board2D.tsx` as module-private helpers. `Selection`, `ManaCrystals`, `WeaponView`, `SecretMarker` are no longer declared in `GameBoard.tsx`.

- [ ] **Step 1: Create `frontend/src/components/Board2D.tsx`**

Copy the two board sections (opponent zone ≈ old lines 260–289 and player zone ≈ old lines 308–332) into a new component, keeping the JSX identical. `Selection`, `ManaCrystals`, `WeaponView`, `SecretMarker` live in this file. Full structure:

```tsx
import type { GameCard, GamePlayer } from "../api/types";
import CardView from "./CardView";
import HeroView from "./HeroView";

interface Selection { type: "attack" | "play" | "hero_power"; source: GameCard; }

export function ManaCrystals({ available, total }: { available: number; total: number }) {
  const crystals = Math.max(total, available);
  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-1">
        {Array.from({ length: crystals }, (_, i) => (
          <span key={i} className={`h-4 w-4 rounded-full ${i < available ? "bg-amber-400" : "bg-slate-600"}`} />
        ))}
      </div>
      <span className="text-xs font-semibold text-slate-300">{available}/{total}</span>
    </div>
  );
}

function WeaponView({ weapon }: { weapon: GameCard }) { /* move verbatim from GameBoard */ }
function SecretMarker() { /* move verbatim from GameBoard */ }

interface Board2DProps {
  me: GamePlayer; opp: GamePlayer;
  yourTurn: boolean;
  selection: Selection | null;
  targetIds: Set<number>;
  onMyMinion: (c: GameCard) => void;
  onOppCharacter: (c: GameCard) => void;
}

export default function Board2D({ me, opp, yourTurn, selection, targetIds, onMyMinion, onOppCharacter }: Board2DProps) {
  const hero = me.hero;
  const heroPower = me.hero_power;
  return (
    <>
      {/* Opponent zone — move verbatim, replacing component-local hooks with props */}
      <section className="space-y-2">
        {/* name/deck/hand header, ManaCrystals(opp), field via CardView(onClick=onOppCharacter, selected=targetIds.has),
             HeroView(onClick=onOppCharacter), WeaponView, secrets */}
      </section>
      {/* Player zone — move verbatim, replacing component-local hooks with props */}
      <section className="space-y-2">
        {/* HeroView(onClick=onMyMinion), WeaponView, secrets, ManaCrystals(me), field via CardView(onClick=onMyMinion) */}
      </section>
    </>
  );
}
```

Note: `yourTurn` and `heroPower` are only used by the *status bar* handlers (which stay in `GameBoard`); keep the props that the moved JSX actually uses. The JSX moves unchanged — the prop values come from `GameBoard` via the props.

- [ ] **Step 2: Rewire `GameBoard.tsx`**

Replace the two board `<section>` blocks (opponent zone + player zone) with:

```tsx
<Board2D
  me={me}
  opp={opp}
  yourTurn={yourTurn}
  selection={selection}
  targetIds={targetIds}
  onMyMinion={onMyMinion}
  onOppCharacter={onOppCharacter}
/>
```

Remove the now-unused local declarations (`Selection` interface, `ManaCrystals`, `WeaponView`, `SecretMarker`) and imports; add `import Board2D from "../components/Board2D";`.

- [ ] **Step 3: Verify — type-check + build**

Run: `cd frontend && npm run build`
Expected: PASS (type-check + vite build). The board must still be the 2D board.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Board2D.tsx frontend/src/pages/GameBoard.tsx
git commit -m "refactor(3d): extract 2D board zones into Board2D (no behavior change)"
```

---

### Task 4: Board layout module (pure, TDD)

**Files:**
- Create: `frontend/src/three/layout.ts`
- Test: `frontend/src/three/layout.test.ts`

**Interfaces:**
- Produces:
  - `type Side = "me" | "opp"`
  - `interface SlotPos { x: number; z: number }`
  - `const FIELD_SLOTS = 7`, `const SLOT_SPACING = 1.25`
  - `const ME_FIELD_Z = 1.2`, `const OPP_FIELD_Z = -1.2` (z of each field row)
  - `const HERO_POS: Record<Side, SlotPos>` = `{ me: { x: 0, z: 3.3 }, opp: { x: 0, z: -3.3 } }`
  - `const WEAPON_POS: Record<Side, SlotPos>` = `{ me: { x: 2.2, z: 3.3 }, opp: { x: -2.2, z: -3.3 } }`
  - `slotPosition(side: Side, slot: number): SlotPos` — slot 0..6, left→right from the viewer, me row at `z = ME_FIELD_Z`, opp row at `z = OPP_FIELD_Z`.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { slotPosition, HERO_POS, WEAPON_POS, FIELD_SLOTS, SLOT_SPACING } from "./layout";

describe("layout", () => {
  it("places slot 0 on the far left and slot 6 on the far right", () => {
    const left = slotPosition("me", 0);
    const right = slotPosition("me", FIELD_SLOTS - 1);
    expect(right.x).toBeGreaterThan(left.x);
    expect(left.x).toBeCloseTo(-(FIELD_SLOTS - 1) / 2 * SLOT_SPACING);
  });
  it("mirrors the opponent row to the far side", () => {
    const me = slotPosition("me", 3);
    const opp = slotPosition("opp", 3);
    expect(opp.z).toBeCloseTo(-me.z);
    expect(opp.x).toBeCloseTo(me.x);
  });
  it("heroes sit behind their own field row", () => {
    expect(HERO_POS.me.z).toBeGreaterThan(slotPosition("me", 3).z);
    expect(HERO_POS.opp.z).toBeLessThan(slotPosition("opp", 3).z);
  });
  it("weapon slots sit beside the hero", () => {
    expect(WEAPON_POS.me.x).not.toBe(0);
    expect(WEAPON_POS.me.z).toBeCloseTo(HERO_POS.me.z);
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && npx vitest run src/three/layout.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `frontend/src/three/layout.ts`**

```ts
export type Side = "me" | "opp";
export interface SlotPos { x: number; z: number }

export const FIELD_SLOTS = 7;
export const SLOT_SPACING = 1.25;
export const ME_FIELD_Z = 1.2;
export const OPP_FIELD_Z = -1.2;

export const HERO_POS: Record<Side, SlotPos> = { me: { x: 0, z: 3.3 }, opp: { x: 0, z: -3.3 } };
export const WEAPON_POS: Record<Side, SlotPos> = { me: { x: 2.2, z: 3.3 }, opp: { x: -2.2, z: -3.3 } };

/** slot 0..6, left→right from the viewer's perspective. */
export function slotPosition(side: Side, slot: number): SlotPos {
  const x = (slot - (FIELD_SLOTS - 1) / 2) * SLOT_SPACING;
  const z = side === "me" ? ME_FIELD_Z : OPP_FIELD_Z;
  return { x, z };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/three/layout.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/three/layout.ts frontend/src/three/layout.test.ts
git commit -m "feat(3d): board slot layout module"
```

---

### Task 5: Unit-resolution module (pure, TDD)

**Files:**
- Create: `frontend/src/three/resolveUnit.ts`
- Test: `frontend/src/three/resolveUnit.test.ts`

**Interfaces:**
- Consumes: `GameCard` from `../api/types`.
- Produces:
  - `type UnitVisual = { kind: "glb"; glbUrl: string } | { kind: "cardPlane"; artUrl: string | null } | { kind: "placeholder" }`
  - `isBoardChar(card: GameCard): boolean` — `card.max_health != null` (matches `CardView`).
  - `boardArtUrl(card: GameCard): string | null` — `` `/images/cards_board/${card.id}.png` `` or `null`.
  - `glbUrl(cardId: string): string` — `` `/models/${cardId}.glb` ``
  - `resolveUnit(card: GameCard, availableGlb: ReadonlySet<string>): UnitVisual` — GLB if the id is in the set, else card-plane if art exists, else placeholder.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { resolveUnit, boardArtUrl, isBoardChar, glbUrl } from "./resolveUnit";
import type { GameCard } from "../api/types";

const minion = { entity_id: 1, id: "EX1_001", max_health: 2, atk: 1 } as GameCard;
const hero = { entity_id: 2, id: "HERO_05", max_health: 30, atk: 0 } as GameCard;

describe("resolveUnit", () => {
  it("uses the GLB when the card id is in the available set", () => {
    expect(resolveUnit(minion, new Set(["EX1_001"]))).toEqual({ kind: "glb", glbUrl: "/models/EX1_001.glb" });
  });
  it("falls back to the board-art card plane when no GLB exists", () => {
    expect(resolveUnit(minion, new Set())).toEqual({ kind: "cardPlane", artUrl: "/images/cards_board/EX1_001.png" });
  });
  it("returns placeholder when there is no art and no GLB", () => {
    const noArt = { entity_id: 3, max_health: 1 } as GameCard;
    expect(resolveUnit(noArt, new Set())).toEqual({ kind: "placeholder" });
  });
  it("recognizes heroes and minions as board characters", () => {
    expect(isBoardChar(hero)).toBe(true);
    expect(isBoardChar(minion)).toBe(true);
  });
  it("builds URLs", () => {
    expect(glbUrl("A")).toBe("/models/A.glb");
    expect(boardArtUrl(minion)).toBe("/images/cards_board/EX1_001.png");
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && npx vitest run src/three/resolveUnit.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `frontend/src/three/resolveUnit.ts`**

```ts
import type { GameCard } from "../api/types";

export type UnitVisual =
  | { kind: "glb"; glbUrl: string }
  | { kind: "cardPlane"; artUrl: string | null }
  | { kind: "placeholder" };

/** Board characters (heroes + minions) have a health pool; spells/weapons do not. */
export function isBoardChar(card: GameCard): boolean {
  return card.max_health != null;
}

export function boardArtUrl(card: GameCard): string | null {
  return card.id ? `/images/cards_board/${card.id}.png` : null;
}

export function glbUrl(cardId: string): string {
  return `/models/${cardId}.glb`;
}

export function resolveUnit(card: GameCard, availableGlb: ReadonlySet<string>): UnitVisual {
  if (card.id && availableGlb.has(card.id)) return { kind: "glb", glbUrl: glbUrl(card.id) };
  const art = boardArtUrl(card);
  if (art) return { kind: "cardPlane", artUrl: art };
  return { kind: "placeholder" };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/three/resolveUnit.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/three/resolveUnit.ts frontend/src/three/resolveUnit.test.ts
git commit -m "feat(3d): unit visual resolution (GLB -> card-plane -> placeholder)"
```

---

### Task 6: Snapshot diff → animation directives (pure, TDD)

**Files:**
- Create: `frontend/src/three/animationPlan.ts`
- Test: `frontend/src/three/animationPlan.test.ts`

**Interfaces:**
- Consumes: `GameState`, `GamePlayer`, `GameCard` from `../api/types`; `slotPosition`, `HERO_POS`, `Side` from `./layout`.
- Produces:
  - `type WSEvent = { kind: string; source?: number; target?: number }`
  - `type AnimDirective = { kind: "spawn"; entityId: number; to: SlotPos } | { kind: "death"; entityId: number } | { kind: "move"; entityId: number; to: SlotPos } | { kind: "attack"; source: number; target: number } | { kind: "heroPower"; entityId: number }`
  - `unitPosition(zone: Side, slot: number): SlotPos` — slot `-1` (hero) → `HERO_POS[zone]`; else `slotPosition(zone, slot)`.
  - `diffSnapshots(prev: GameState | null, next: GameState): AnimDirective[]` — spawn/move/death from added/moved/removed board characters.
  - `eventDirectives(ev: WSEvent, state: GameState): AnimDirective[]` — `attack` → attack directive; `hero_power` → heroPower on the current player's hero.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { diffSnapshots, eventDirectives } from "./animationPlan";
import type { GameCard, GamePlayer, GameState } from "../api/types";
import { HERO_POS } from "./layout";

function p(heroId: number, fieldIds: number[]): GamePlayer {
  return {
    index: 0, hero: { entity_id: heroId, max_health: 30 } as GameCard, hero_power: null, weapon: null,
    deck_count: 0, hand: [], field: fieldIds.map((id) => ({ entity_id: id, max_health: 2 }) as GameCard),
    secrets: [], max_mana: 1, mana: 1, playstate: "playing",
  };
}
function state(players: [GamePlayer, GamePlayer], current_player = 0): GameState {
  return { turn: 1, current_player, ended: false, result: null, players, pending: null };
}
const HERO_A = { entity_id: 100, id: "HERO_05", max_health: 30 } as GameCard;

describe("diffSnapshots", () => {
  it("spawns a newly placed minion", () => {
    const prev = state([p(100, []), p(200, [])]);
    const next = state([p(100, [7]), p(200, [])]);
    const dirs = diffSnapshots(prev, next);
    expect(dirs).toContainEqual({ kind: "spawn", entityId: 7, to: { x: -3.75, z: 1.2 } });
  });
  it("emits death for a removed minion", () => {
    const prev = state([p(100, [7]), p(200, [])]);
    const next = state([p(100, []), p(200, [])]);
    expect(diffSnapshots(prev, next)).toContainEqual({ kind: "death", entityId: 7 });
  });
  it("emits move when a minion changes slot", () => {
    const prev = state([p(100, [7]), p(200, [])]);      // entity 7 at slot 0
    const next = state([p(100, [9, 7]), p(200, [])]);   // entity 7 moves to slot 1
    expect(diffSnapshots(prev, next)).toContainEqual({ kind: "move", entityId: 7, to: { x: -2.5, z: 1.2 } });
  });
  it("keeps heroes stable across snapshots", () => {
    const s = state([p(100, []), p(200, [])]);
    expect(diffSnapshots(s, { ...s })).toEqual([]);
  });
});

describe("eventDirectives", () => {
  const gs = state([p(100, []), p(200, [])], 0); // player 0 is "me"
  it("maps attack events to an attack directive", () => {
    expect(eventDirectives({ kind: "attack", source: 7, target: 8 }, gs)).toEqual([{ kind: "attack", source: 7, target: 8 }]);
  });
  it("maps hero_power to a glow on the current player's hero", () => {
    expect(eventDirectives({ kind: "hero_power", target: 8 }, gs)).toEqual([{ kind: "heroPower", entityId: 100 }]);
  });
  it("returns nothing for unrelated events", () => {
    expect(eventDirectives({ kind: "log", source: 1 }, gs)).toEqual([]);
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && npx vitest run src/three/animationPlan.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `frontend/src/three/animationPlan.ts`**

```ts
import type { GameCard, GamePlayer, GameState } from "../api/types";
import { HERO_POS, slotPosition, type Side, type SlotPos } from "./layout";

export type WSEvent = { kind: string; source?: number; target?: number };

export type AnimDirective =
  | { kind: "spawn"; entityId: number; to: SlotPos }
  | { kind: "death"; entityId: number }
  | { kind: "move"; entityId: number; to: SlotPos }
  | { kind: "attack"; source: number; target: number }
  | { kind: "heroPower"; entityId: number };

function isBoardChar(c: GameCard): boolean {
  return c.max_health != null;
}

/** World position for a board character: heroes use HERO_POS, minions use slotPosition. */
export function unitPosition(zone: Side, slot: number): SlotPos {
  return slot === -1 ? HERO_POS[zone] : slotPosition(zone, slot);
}

interface UnitRef { entityId: number; zone: Side; slot: number; card: GameCard; pos: SlotPos; }

function boardUnits(state: GameState): Map<number, UnitRef> {
  const out = new Map<number, UnitRef>();
  const sides: Array<[Side, GamePlayer | undefined]> = [["me", state.players[0]], ["opp", state.players[1]]];
  for (const [zone, p] of sides) {
    if (p?.hero && isBoardChar(p.hero)) {
      out.set(p.hero.entity_id, { entityId: p.hero.entity_id, zone, slot: -1, card: p.hero, pos: HERO_POS[zone] });
    }
    p?.field.forEach((c, slot) => {
      if (isBoardChar(c)) out.set(c.entity_id, { entityId: c.entity_id, zone, slot, card: c, pos: slotPosition(zone, slot) });
    });
  }
  return out;
}

export function diffSnapshots(prev: GameState | null, next: GameState): AnimDirective[] {
  const dirs: AnimDirective[] = [];
  const prevUnits = prev ? boardUnits(prev) : null;
  const nextUnits = boardUnits(next);
  for (const [id, u] of nextUnits) {
    const old = prevUnits?.get(id);
    if (!old) dirs.push({ kind: "spawn", entityId: id, to: u.pos });
    else if (old.pos.x !== u.pos.x || old.pos.z !== u.pos.z) dirs.push({ kind: "move", entityId: id, to: u.pos });
  }
  if (prevUnits) {
    for (const id of prevUnits.keys()) {
      if (!nextUnits.has(id)) dirs.push({ kind: "death", entityId: id });
    }
  }
  return dirs;
}

export function eventDirectives(ev: WSEvent, state: GameState): AnimDirective[] {
  if (ev.kind === "attack" && ev.source != null && ev.target != null) {
    return [{ kind: "attack", source: ev.source, target: ev.target }];
  }
  if (ev.kind === "hero_power") {
    const hero = state.players[state.current_player]?.hero;
    if (hero) return [{ kind: "heroPower", entityId: hero.entity_id }];
  }
  return [];
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/three/animationPlan.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/three/animationPlan.ts frontend/src/three/animationPlan.test.ts
git commit -m "feat(3d): snapshot diff -> animation directives"
```

---

### Task 7: Model normalization (pure, three-based, TDD)

**Files:**
- Create: `frontend/src/three/normalize.ts`
- Test: `frontend/src/three/normalize.test.ts`

**Interfaces:**
- Consumes: `three` (`Box3`, `Vector3`).
- Produces: `normalizeUnit(object: THREE.Object3D, targetHeight: number): void` — scales the object uniformly so its height equals `targetHeight`, centers it on x/z, and puts its base on y=0.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import * as THREE from "three";
import { normalizeUnit } from "./normalize";

describe("normalizeUnit", () => {
  it("scales a mesh to the target height and grounds its base at y=0", () => {
    // A box 1 wide, 2 tall, 1 deep, centered at origin => min.y = -1, height = 2.
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(1, 2, 1));
    const group = new THREE.Group();
    group.add(mesh);
    group.position.set(3, 0, 4); // off-center, like a raw TripoSR model

    normalizeUnit(group, 1.2);

    expect(group.scale.x).toBeCloseTo(0.6);
    const box = new THREE.Box3().setFromObject(group);
    expect(box.getSize(new THREE.Vector3()).y).toBeCloseTo(1.2);
    expect(box.min.y).toBeCloseTo(0);
    // Centered horizontally relative to the group origin (which stays at its own position).
    const center = box.getCenter(new THREE.Vector3());
    expect(center.x).toBeCloseTo(group.position.x);
    expect(center.z).toBeCloseTo(group.position.z);
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && npx vitest run src/three/normalize.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `frontend/src/three/normalize.ts`**

```ts
import * as THREE from "three";

/**
 * Scale `object` uniformly so its height equals `targetHeight`, recenter it on
 * its own x/z, and ground its base on y=0. Mutates `object.scale`/`position`.
 */
export function normalizeUnit(object: THREE.Object3D, targetHeight: number): void {
  const box = new THREE.Box3().setFromObject(object);
  const size = new THREE.Vector3();
  box.getSize(size);
  if (size.y <= 0) return;

  object.scale.setScalar(targetHeight / size.y);

  const scaledBox = new THREE.Box3().setFromObject(object);
  const center = new THREE.Vector3();
  scaledBox.getCenter(center);
  object.position.x -= center.x - object.position.x;
  object.position.z -= center.z - object.position.z;
  object.position.y -= scaledBox.min.y;
}
```

Note: after scaling, `scaledBox.min.y` is in *world* coords; shifting `object.position.y` by `-scaledBox.min.y` puts the base at y=0. The x/z correction re-centers the group's origin over its own x/z.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/three/normalize.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/three/normalize.ts frontend/src/three/normalize.test.ts
git commit -m "feat(3d): GLB normalization (scale to height, center, ground)"
```

---

### Task 8: Static `Battlefield3D` scene (card-plane units)

**Files:**
- Create: `frontend/src/components/Battlefield3D.tsx`
- Create: `frontend/src/three/Unit3D.tsx`
- Create: `frontend/src/three/CardPlane.tsx`
- Create: `frontend/src/three/manifest.ts`
- Modify: `frontend/src/pages/GameBoard.tsx`

**Interfaces:**
- Consumes: `useGame` store (`state`, `myIndex`), `resolveUnit`, `unitPosition`, `HERO_POS`, `WEAPON_POS`, `slotPosition`, `ManaCrystals` (from `Board2D`), `GameCard`/`GamePlayer`.
- Produces:
  - `fetchModelManifest(): Promise<ReadonlySet<string>>` — GET `/models/manifest.json`, cached; empty set on failure.
  - `Battlefield3D` — the `<Canvas>`; no props.
  - `Unit3D({ card, side, slot, visual, onClick, selected, attackable, taunt })` — a group at its slot position.
  - `CardPlane({ artUrl })` — a rounded-rect plane textured with the board art.

This task renders **card-plane units only** (GLBs come in Task 12). The scene must reflect the live snapshot: opponents far, player near, heroes behind each field row, weapon planes beside heroes, stat labels above units, mana overlay.

- [ ] **Step 1: Create `frontend/src/three/manifest.ts`**

```ts
let cached: Promise<ReadonlySet<string>> | null = null;

/** The set of card ids that have a generated GLB (from /models/manifest.json). */
export function fetchModelManifest(): Promise<ReadonlySet<string>> {
  if (!cached) {
    cached = fetch("/models/manifest.json")
      .then((r) => (r.ok ? r.json() as Promise<string[]> : []))
      .then((ids: string[]) => new Set(ids))
      .catch(() => new Set<string>());
  }
  return cached;
}
```

- [ ] **Step 2: Create `frontend/src/three/CardPlane.tsx`**

```tsx
import { useMemo } from "react";
import * as THREE from "three";
import { useTexture } from "@react-three/drei";
import { useLoader } from "@react-three/fiber";
import { TextureLoader } from "three";

interface CardPlaneProps { artUrl: string | null; width?: number; height?: number; }

export function CardPlane({ artUrl, width = 0.9, height = 1.3 }: CardPlaneProps) {
  const tex = artUrl ? useTexture(artUrl) : null;
  const geometry = useMemo(() => new THREE.PlaneGeometry(width, height), [width, height]);
  return (
    <group>
      <mesh geometry={geometry} rotation={[-0.12, 0, 0]}>
        <meshStandardMaterial map={tex ?? undefined} color={tex ? "#fff" : "#334155"} side={THREE.DoubleSide} />
      </mesh>
      {/* thin base */}
      <mesh position={[0, -height / 2 - 0.03, 0]}>
        <cylinderGeometry args={[0.28, 0.32, 0.06, 24]} />
        <meshStandardMaterial color="#1e293b" />
      </mesh>
    </group>
  );
}
```

- [ ] **Step 3: Create `frontend/src/three/Unit3D.tsx`**

```tsx
import { Html } from "@react-three/drei";
import type { GameCard } from "../api/types";
import type { UnitVisual } from "./resolveUnit";
import { CardPlane } from "./CardPlane";
import type { Side } from "./layout";
import { unitPosition } from "./animationPlan";

const HP = (card: GameCard) => Math.max(0, (card.max_health ?? 0) - (card.damage ?? 0));

export interface Unit3DProps {
  card: GameCard;
  side: Side;
  slot: number;               // -1 for heroes
  visual: UnitVisual;
  selected: boolean;
  attackable: boolean;
  taunt: boolean;
  onClick?: () => void;
}

export function Unit3D({ card, side, slot, visual, selected, attackable, taunt, onClick }: Unit3DProps) {
  const pos = unitPosition(side, slot);
  const height = slot === -1 ? 1.6 : 1.2;
  return (
    <group position={[pos.x, 0, pos.z]}>
      {taunt && (
        <mesh position={[0, 0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.55, 0.62, 32]} />
          <meshBasicMaterial color="#a855f7" transparent opacity={0.8} />
        </mesh>
      )}
      {visual.kind === "glb" ? null : <CardPlane artUrl={visual.kind === "cardPlane" ? visual.artUrl : null} />}
      <Html center position={[0, height + 0.15, 0]}>
        <div className="pointer-events-none flex gap-1 text-xs font-black">
          <span className="rounded-full bg-orange-600 px-2 py-0.5 text-white shadow">{card.atk ?? 0}</span>
          <span className={`rounded-full px-2 py-0.5 text-white shadow ${HP(card) < (card.max_health ?? 0) ? "bg-red-600" : "bg-slate-600"}`}>{HP(card)}</span>
        </div>
      </Html>
      {onClick && (
        <mesh
          position={[0, height / 2, 0]}
          onClick={(e) => { e.stopPropagation(); onClick(); }}
          visible={false}
        >
          <boxGeometry args={[1.1, height, 0.4]} />
        </mesh>
      )}
    </group>
  );
}
```

(The `unitPosition(side, slot)` call uses the layout module directly — heroes are `slot === -1`.)

- [ ] **Step 4: Create `frontend/src/components/Battlefield3D.tsx`**

```tsx
import { Suspense, useEffect, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { useGame } from "../store/game";
import { Unit3D } from "../three/Unit3D";
import { CardPlane } from "../three/CardPlane";
import { fetchModelManifest } from "../three/manifest";
import { resolveUnit, isBoardChar } from "../three/resolveUnit";
import { WEAPON_POS } from "../three/layout";
import { ManaCrystals } from "./Board2D";

export default function Battlefield3D() {
  const state = useGame((s) => s.state);
  const [available, setAvailable] = useState<ReadonlySet<string>>(new Set());
  useEffect(() => { fetchModelManifest().then(setAvailable); }, []);

  if (!state) return null;
  const me = state.players[0];
  const opp = state.players[1];
  const boardChars = (p: typeof me, side: "me" | "opp") => [
    ...(isBoardChar(p.hero) ? [{ card: p.hero, slot: -1 }] : []),
    ...p.field.filter(isBoardChar).map((c, i) => ({ card: c, slot: i })),
  ];

  return (
    <div className="relative h-[62vh]">
      <Canvas
        camera={{ position: [0, 6.5, 7.5], fov: 45, up: [0, 1, 0] }}
        gl={{ antialias: true }}
        dpr={[1, 2]}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[4, 8, 4]} intensity={1.1} />
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.06, 0]} receiveShadow>
          <planeGeometry args={[12, 9]} />
          <meshStandardMaterial color="#0f172a" />
        </mesh>
        <Suspense fallback={null}>
          {["me", "opp"].flatMap((side) =>
            boardChars(side === "me" ? me : opp, side as "me" | "opp").map(({ card, slot }) => (
              <Unit3D key={card.entity_id} card={card} side={side as "me" | "opp"} slot={slot}
                visual={resolveUnit(card, available)} selected={false} attackable={false} taunt={card.taunt ?? false} />
            ))
          )}
          {me.weapon?.id && (
            <group position={[WEAPON_POS.me.x, 0, WEAPON_POS.me.z]}>
              <CardPlane artUrl={`/images/cards_board/${me.weapon.id}.png`} width={0.5} height={0.7} />
            </group>
          )}
          {opp.weapon?.id && (
            <group position={[WEAPON_POS.opp.x, 0, WEAPON_POS.opp.z]}>
              <CardPlane artUrl={`/images/cards_board/${opp.weapon.id}.png`} width={0.5} height={0.7} />
            </group>
          )}
        </Suspense>
      </Canvas>
      {/* HUD overlay: mana + turn, on top of the scene */}
      <div className="pointer-events-none absolute inset-x-0 top-2 flex justify-center gap-6">
        <div className="pointer-events-auto"><ManaCrystals available={opp.mana} total={opp.max_mana} /></div>
        <ManaCrystals available={me.mana} total={me.max_mana} />
      </div>
    </div>
  );
}
```


- [ ] **Step 5: Wire the view toggle into `GameBoard.tsx`**

Add a dev-only selector so the 3D board can be previewed while the 2D board stays the default:

```tsx
import Battlefield3D from "../components/Battlefield3D";
import Board2D from "../components/Board2D";
import { getViewMode } from "../three/viewMode";

// Replace the `<Board2D ... />` render with:
const params = new URLSearchParams(location.search);
const dev3d = params.get("view") === "3d" || getViewMode() === "3d";
...
{dev3d ? <Battlefield3D /> : <Board2D ... existing props ... />}
```

- [ ] **Step 6: Verify — build + manual render**

Run: `cd frontend && npm run build` — PASS.
Run the dev server (`npm run dev`), start a game vs AI, open `/?view=3d`: the board shows heroes + minions as card-planes on a dark plane, with stat badges, and mana overlay. `?view=3d` off → unchanged 2D board.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/Battlefield3D.tsx frontend/src/three/Unit3D.tsx frontend/src/three/CardPlane.tsx frontend/src/three/manifest.ts frontend/src/pages/GameBoard.tsx
git commit -m "feat(3d): static R3F battlefield with card-plane units and dev view toggle"
```

---

### Task 9: Interaction — raycast picking + targeting parity

**Files:**
- Create: `frontend/src/three/pick.ts`
- Modify: `frontend/src/components/Battlefield3D.tsx`, `frontend/src/three/Unit3D.tsx`, `frontend/src/pages/GameBoard.tsx`

**Interfaces:**
- Consumes: `Selection` shape from `GameBoard` (`{ type: "attack" | "play" | "hero_power"; source: GameCard }`), `send()` from the store.
- Produces:
  - `entityOfCard(card: GameCard): number` — `card.entity_id` (with a note that heroes use their own entity_id; heroes and minions both carry `entity_id` in the snapshot).
  - `makeSelectionHandlers({ yourTurn, me, heroPower, selection, targets, onMyMinion, onOppCharacter, send })` — returns `onUnitClick(card: GameCard, zone: "me" | "opp")` implementing the 2D board's selection flow in the 3D scene.

- [ ] **Step 1: Create `frontend/src/three/pick.ts`**

The 3D click path must reproduce the current 2D behavior exactly (see `GameBoard.tsx` `onMyMinion` / `onHandCard` / `onOppCharacter` / `useHeroPower`). Because the 3D scene has no DOM `button` affordances, clicking a unit either *starts* a selection (my attackable minion / my playable hero) or *completes* it (clicking a legal target):

```ts
import type { GameCard } from "../api/types";

export type Zone = "me" | "opp";
export interface Selection { type: "attack" | "play" | "hero_power"; source: GameCard; }

export interface PickDeps {
  yourTurn: boolean;
  mana: number;
  selection: Selection | null;
  targetIds: ReadonlySet<number>;
  setSelection: (s: Selection | null) => void;
  send: (msg: unknown) => void;
}

/** A click landed on a board unit (hero or minion). */
export function onUnitClick(deps: PickDeps, card: GameCard, zone: Zone): void {
  const { yourTurn, mana, selection, targetIds, setSelection, send } = deps;
  if (selection) {
    if (targetIds.has(card.entity_id)) {
      if (selection.type === "attack") {
        send({ type: "action", action: { kind: "attack", source: selection.source.entity_id, target: card.entity_id } });
      } else if (selection.type === "play") {
        send({ type: "action", action: { kind: "play_card", card: selection.source.entity_id, target: card.entity_id, index: 0, choose: null } });
      } else {
        send({ type: "action", action: { kind: "hero_power", target: card.entity_id } });
      }
    }
    setSelection(null);
    return;
  }
  if (!yourTurn) return;
  if (zone === "me" && card.can_attack) {
    setSelection({ type: "attack", source: card });
  }
}

/** A hand card is clicked in the HUD while the 3D board is active. */
export function onHandCardClick(deps: PickDeps, card: GameCard): void {
  const { yourTurn, mana, selection, setSelection, send } = deps;
  if (selection) { setSelection(null); return; }
  if (!yourTurn) return;
  if ((card.cost ?? 0) > mana) return;
  if (card.requires_target && (card.targets ?? []).length > 0) {
    setSelection({ type: "play", source: card });
  } else {
    send({ type: "action", action: { kind: "play_card", card: card.entity_id, target: null, index: 0, choose: null } });
  }
}
```

- [ ] **Step 2: Wire picking + targets into `Unit3D` and `Battlefield3D`**

In `Battlefield3D`, thread the selection state (lifted from `GameBoard` into the store or passed as props) to `Unit3D`:
- `Unit3D` gets real `onClick`, `selected` (`targetIds.has(entity_id)` or `selection.source.entity_id === entity_id`), and `attackable` (`yourTurn && card.can_attack`).
- The invisible click-mesh in `Unit3D` uses `onClick` (R3F raycast). Keep `visible={false}` meshes out of the render by `material.transparent`/`depthWrite` — simplest: give the click mesh `visible` but `material={{ visible: false }}`? Use `raycast`-friendly invisible meshes via `mesh.visible = true` + `material.visible = false`, or just make it a flat translucent box. Prefer: `<mesh ... visible={false}>` does NOT raycast. Use a `<Box>` with `material.visible = false`:

```tsx
<mesh position={[0, height / 2, 0]} onClick={(e) => { e.stopPropagation(); onClick(); }}>
  <boxGeometry args={[1.1, height, 0.4]} />
  <meshBasicMaterial visible={false} />
</mesh>
```

- In `Battlefield3D`, render the targeting overlay when a selection is active (reuse the existing `TargetingOverlay` component imported from `../components/TargetingOverlay`), and highlight `targetIds` units.

- [ ] **Step 3: Point the HUD hand clicks at the 3D handlers**

In `GameBoard`, when in 3D mode, the hand `CardView onClick` should call `onHandCardClick` with the same deps; the hero-power button and end-turn button are unchanged. Keep the 2D path unchanged.

- [ ] **Step 4: Verify — build + manual playtest vs AI**

Run: `cd frontend && npm run build` — PASS.
Manual (3D, `/?view=3d`): click an attackable minion → targets glow → click a target → attack resolves; play a targeted spell from hand → pick target on the 3D board; hero power with target works; end turn switches sides.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/three/pick.ts frontend/src/components/Battlefield3D.tsx frontend/src/three/Unit3D.tsx frontend/src/pages/GameBoard.tsx
git commit -m "feat(3d): raycast targeting parity (attack / play / hero power)"
```

---

### Task 10: Core animations

**Files:**
- Create: `frontend/src/three/motion.ts`
- Modify: `frontend/src/three/Unit3D.tsx`, `frontend/src/components/Battlefield3D.tsx`

**Interfaces:**
- Consumes: `AnimDirective`, `diffSnapshots`, `eventDirectives` from `./animationPlan`; the store's `lastEvent`.
- Produces:
  - `useUnitMotion(target: { x: number; z: number })` → `ref` for a `THREE.Group`; lerps toward `target` each frame.
  - `useSpawn()` → returns a ref + a `progress` (0→1) scale-in on mount.
  - `useDeath(onDone: () => void)` → returns a ref; fades/scales the unit out, then calls `onDone`.
  - `useAttackLunge(active, sourceRef, from, to)` — when `active`, displaces `sourceRef` out to 70% toward `to` and back over ~450 ms (mirrors the current 2D animation).
  - `useCameraNudge(active: boolean, scale?: number)` → `{ trigger(): void }` — a short camera offset on the keyframe of a big action.

- [ ] **Step 1: Create `frontend/src/three/motion.ts`**

```ts
import { useEffect, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

export function useUnitMotion(target: { x: number; z: number }) {
  const ref = useRef<THREE.Group>(null);
  useFrame((_, dt) => {
    const g = ref.current;
    if (!g) return;
    const t = 1 - Math.pow(0.0005, dt); // smooth, framerate-independent
    g.position.x += (target.x - g.position.x) * t;
    g.position.z += (target.z - g.position.z) * t;
  });
  return ref;
}

export function useSpawn() {
  const ref = useRef<THREE.Group>(null);
  useFrame((_, dt) => {
    const g = ref.current;
    if (!g) return;
    g.scale.setScalar(Math.min(1, g.scale.x + dt * 3));
  });
  return ref;
}

export function useDeath(onDone: () => void) {
  const ref = useRef<THREE.Group>(null);
  useEffect(() => {
    const g = ref.current;
    if (!g) return;
    const start = performance.now();
    const dur = 300;
    const tick = () => {
      const t = Math.min(1, (performance.now() - start) / dur);
      g.scale.setScalar(Math.max(0.001, 1 - t));
      g.traverse((o) => {
        if ((o as THREE.Mesh).isMesh) {
          const mat = (o as THREE.Mesh).material as THREE.MeshStandardMaterial;
          mat.transparent = true;
          mat.opacity = Math.max(0, 1 - t);
        }
      });
      if (t < 1) requestAnimationFrame(tick);
      else onDone();
    };
    tick();
  }, [onDone]);
  return ref;
}

export function useAttackLunge(active: boolean, sourceRef: THREE.Object3D | null, from: THREE.Vector3, to: THREE.Vector3) {
  const start = useRef(0);
  useFrame(() => {
    if (!active || !sourceRef) return;
    if (start.current === 0) start.current = performance.now();
    const t = (performance.now() - start.current) / 450;
    if (t >= 1) { sourceRef.position.set(from.x, from.y, from.z); start.current = 0; return; }
    const out = Math.min(1, t * 2) * 0.7;
    const back = Math.max(0, (t - 0.5) * 2) * 0.7;
    const amp = out - back;
    sourceRef.position.set(from.x + (to.x - from.x) * amp, from.y, from.z + (to.z - from.z) * amp);
  });
}

export function useCameraNudge(active: boolean, scale = 0.15) {
  const { camera } = useThree();
  const start = useRef(0);
  const base = useRef<{ x: number; y: number; z: number } | null>(null);
  useFrame(() => {
    if (!active) return;
    if (start.current === 0) {
      start.current = performance.now();
      base.current ??= { x: camera.position.x, y: camera.position.y, z: camera.position.z };
    }
    const t = (performance.now() - start.current) / 450;
    if (t >= 1) {
      if (base.current) camera.position.set(base.current.x, base.current.y, base.current.z);
      start.current = 0;
      return;
    }
    const amp = Math.sin(Math.PI * t) * scale;
    camera.position.x = (base.current?.x ?? 0) + amp;
    camera.position.z = (base.current?.z ?? 7.5) - amp * 0.4;
  });
  return { trigger: () => { start.current = 0; } };
}
```

- [ ] **Step 2: Wire animations into `Battlefield3D`**

Track a `prevState` ref; after each render, compute `diffSnapshots(prev, state)` and `eventDirectives(lastEvent, state)` and apply:
- `spawn` → `useSpawn` on the new unit (keyed by entity).
- `death` → `useDeath` (then remove from a local `removed` set that suppresses render until unmount).
- `move` → `useUnitMotion` toward the new slot.
- `attack` → `useAttackLunge` on the source group using the target's current world position.
- `heroPower` → a one-shot emissive flash on the hero mesh.
- big actions / turn change → `useCameraNudge`.

Because units are keyed React components, mount/unmount drive spawn/death; the motion hooks live in `Unit3D` and read their slot + attack state from props derived in `Battlefield3D`.

- [ ] **Step 3: Verify — build + manual playtest vs AI**

Run: `cd frontend && npm run build` — PASS.
Manual (3D): playing a card spawns a unit with a scale-in; attacks lunge toward the target with a flash; deaths fade out; hero power pulses the hero; turn change nudges the camera. No console errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/three/motion.ts frontend/src/three/Unit3D.tsx frontend/src/components/Battlefield3D.tsx
git commit -m "feat(3d): core animations (spawn, move, death, attack lunge, hero power, camera nudge)"
```

---

### Task 11: Serve `/models` (backend + dev + prod)

**Files:**
- Modify: `backend/app/main.py`
- Modify: `frontend/vite.config.ts`
- Modify: `deploy/nginx.conf`
- Modify: `deploy/docker-compose.yml`

**Interfaces:**
- Produces: `GET /models/manifest.json` and `GET /models/{id}.glb` served by the backend in dev and prod (mirrors `/images`).

- [ ] **Step 1: Mount `/models` in `backend/app/main.py`**

After the `/audio` mount (≈ line 65), add:

```python
# Generated 3D models (from private card art — gitignored, never committed).
_models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "3dmodels")
os.makedirs(_models_dir, exist_ok=True)
app.mount("/models", StaticFiles(directory=_models_dir), name="models")
```

- [ ] **Step 2: Proxy `/models` in `frontend/vite.config.ts`**

Add to the `proxy` object (next to `/images`):

```ts
"/models": "http://localhost:8000",
```

- [ ] **Step 3: Add the `/models` location to `deploy/nginx.conf`**

After the `/audio/` block add:

```nginx
  # Generated 3D models (from private art, gitignored).
  location /models/ {
    proxy_pass http://backend:8000/models/;
  }
```

- [ ] **Step 4: Bind-mount `3dmodels` in `deploy/docker-compose.yml`**

Under `volumes` (next to `../backend/images`), add:

```yaml
      - ../backend/3dmodels:/srv/backend/3dmodels
```

- [ ] **Step 5: Verify**

```bash
mkdir -p backend/3dmodels && echo '["HERO_05"]' > backend/3dmodels/manifest.json
cd frontend && npm run dev &
curl -s http://localhost:8000/models/manifest.json   # -> ["HERO_05"]
curl -s http://localhost:5173/models/manifest.json   # vite proxy -> ["HERO_05"]
```
Then remove the scratch manifest (real one is written by Task 13's script):
`rm backend/3dmodels/manifest.json`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py frontend/vite.config.ts deploy/nginx.conf deploy/docker-compose.yml
git commit -m "feat(3d): serve generated GLBs at /models (backend mount + dev proxy + nginx + compose)"
```

---

### Task 12: GLB loading with normalization + fallback

**Files:**
- Modify: `frontend/src/three/models.ts` (new)
- Modify: `frontend/src/three/Unit3D.tsx`, `frontend/src/three/CardPlane.tsx`

**Interfaces:**
- Consumes: `fetchModelManifest`, `normalizeUnit`, `resolveUnit`.
- Produces:
  - `ModelUnit({ glbUrl, height })` — loads the GLB (drei `useGLTF`), applies `normalizeUnit(gltf.scene.clone(), height)`, wrapped in `<Suspense>`.
  - `ModelErrorBoundary` — a small class component that renders the `CardPlane` fallback if GLB loading throws.
- The `visual.kind === "glb"` branch in `Unit3D` now renders `ModelUnit` instead of `null`.

- [ ] **Step 1: Create `frontend/src/three/models.ts`**

```tsx
import { Component, Suspense, type ReactNode } from "react";
import * as THREE from "three";
import { useGLTF } from "@react-three/drei";
import { normalizeUnit } from "./normalize";

export function ModelUnit({ glbUrl, height }: { glbUrl: string; height: number }) {
  const { scene } = useGLTF(glbUrl);
  const clone = scene.clone(true);
  clone.traverse((o) => {
    if (o instanceof THREE.Mesh) {
      o.castShadow = true;
      o.receiveShadow = true;
    }
  });
  normalizeUnit(clone, height);
  return <primitive object={clone} />;
}

export class ModelErrorBoundary extends Component<{ fallback: ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? this.props.fallback : this.props.children; }
}
```

- [ ] **Step 2: Use `ModelUnit` in `Unit3D`**

Replace the `visual.kind === "glb" ? null : ...` line with:

```tsx
{visual.kind === "glb" ? (
  <ModelErrorBoundary fallback={<CardPlane artUrl={null} />}>
    <Suspense fallback={<CardPlane artUrl={null} />}>
      <ModelUnit glbUrl={visual.glbUrl} height={height} />
    </Suspense>
  </ModelErrorBoundary>
) : (
  <CardPlane artUrl={visual.kind === "cardPlane" ? visual.artUrl : null} />
)}
```

- [ ] **Step 3: Verify — build + a sample GLB renders**

Place a real generated GLB at `backend/3dmodels/HERO_05.glb` (use Task 13's script, or download any GLB to test), and a matching manifest. Run `npm run dev`, open `/?view=3d`: the hero renders as a 3D model standing on the board, scaled to 1.6 units and grounded; a minion without a GLB renders as a card-plane. A broken GLB path shows the card-plane fallback with no console error.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/three/models.ts frontend/src/three/Unit3D.tsx
git commit -m "feat(3d): GLB loading with load-time normalization and card-plane fallback"
```

---

### Task 13: TripoSR batch generation script (Python, TDD)

**Files:**
- Create: `backend/scripts/3d/generate_models.py`
- Create: `backend/scripts/3d/heroes.txt` (placeholder with instructions)
- Test: `backend/tests/test_3d_models.py`

**Interfaces:**
- Consumes: `frontend/src/data/recommended_decks.json`, TripoSR repo (`VAST-AI-Research/TripoSR`), `trimesh` (pip).
- Produces:
  - `load_manifest(path: Path) -> list[str]` — read a JSON array of card ids; `[]` if missing.
  - `build_manifest(decks_json: Path, hero_ids: list[str]) -> list[str]` — union of hero ids + all `card_ids` in the decks JSON, sorted.
  - `make_generator(triposr_dir: Path) -> Callable[[str, Path, Path], Path]` — `generate(card_id, art_path, out_dir)` runs TripoSR, finds the produced `.glb`/`.obj`, and writes `out_dir/{card_id}.glb` (OBJ/GLTF converted via `trimesh`).
  - `main(argv) -> int` — CLI: `--manifest`, `--heroes`, `--art-dir`, `--out-dir`, `--triposr-dir`, `--write-manifest`; skips existing outputs; never fails the batch on a single bad card.

- [ ] **Step 1: Add the dev dependency**

```bash
pip install trimesh
```

- [ ] **Step 2: Write the failing tests**

```python
# backend/tests/test_3d_models.py
import json
import sys
from pathlib import Path

# The 3D tooling lives under backend/scripts/3d and is run as a script, so put it
# on sys.path (same convention as the other scripts in that folder).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "3d"))

import generate_models as gm

def test_load_manifest_missing_returns_empty(tmp_path: Path):
    assert gm.load_manifest(tmp_path / "nope.json") == []

def test_load_manifest_roundtrip(tmp_path: Path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(["A", "B"]))
    assert gm.load_manifest(p) == ["A", "B"]

def test_build_manifest_unions_heroes_and_deck_cards(tmp_path: Path):
    decks = tmp_path / "decks.json"
    decks.write_text(json.dumps([
        {"name": "d1", "card_ids": ["A", "B"]},
        {"name": "d2", "card_ids": ["B", "C"]},
    ]))
    assert gm.build_manifest(decks, ["HERO"]) == ["A", "B", "C", "HERO"]

def test_make_generator_converts_obj_to_glb(tmp_path: Path, monkeypatch):
    import subprocess
    def fake_run(cmd, **kw):  # type: ignore[no-untyped-def]
        assert "run.py" in cmd[0]
        out_dir = Path(cmd[cmd.index("--output-dir") + 1])
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "model.obj").write_text("# fake obj\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
    monkeypatch.setattr(subprocess, "run", fake_run)

    art = tmp_path / "art.png"; art.write_text("x")
    out = gm.make_generator(tmp_path / "triposr")("CARD", art, tmp_path / "out")
    assert out.name == "CARD.glb"
    assert out.exists() and out.stat().st_size > 0

def test_generate_skips_existing(tmp_path: Path):
    out_dir = tmp_path / "out"; out_dir.mkdir()
    (out_dir / "KEEP.glb").write_bytes(b"glb")
    art_dir = tmp_path / "art"; art_dir.mkdir()
    (art_dir / "NEW.png").write_bytes(b"png")
    calls: list[str] = []
    def fake_generate(card_id: str, art: Path, out: Path) -> Path:
        calls.append(card_id)
        return out / f"{card_id}.glb"
    log: list[str] = []
    gm.generate_missing(["KEEP", "NEW"], fake_generate, out_dir, art_dir, log)
    assert calls == ["NEW"]
```

Note: the last test uses `generate_missing(ids, generate, out_dir, art_dir, log)` — implement it in Step 3 (the skip + art-missing logic), and have `main` call it.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_3d_models.py -v`
Expected: FAIL — `generate_models` module not importable / functions missing.

- [ ] **Step 4: Implement `backend/scripts/3d/generate_models.py`**

```python
"""Generate 3D models (GLB) from card board-art via TripoSR.

Usage:
    python backend/scripts/3d/generate_models.py --write-manifest --heroes backend/scripts/3d/heroes.txt
    python backend/scripts/3d/generate_models.py --manifest backend/scripts/3d/manifest.json \
        --triposr-dir ~/src/TripoSR --art-dir backend/images/cards_board --out-dir backend/3dmodels

Run TripoSR in a checked-out clone (VAST-AI-Research/TripoSR); generation is a
one-time offline batch — never CI. Outputs are gitignored (private art).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable


def load_manifest(path: Path) -> list[str]:
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [c for c in data if isinstance(c, str) and c]


def build_manifest(decks_json: Path, hero_ids: list[str]) -> list[str]:
    decks = json.loads(decks_json.read_text()) if decks_json.exists() else []
    ids = set(hero_ids)
    for deck in decks:
        for cid in deck.get("card_ids", []):
            ids.add(cid)
    return sorted(ids)


def _to_glb(src: Path, out: Path) -> None:
    import trimesh
    trimesh.load(str(src), force="scene").export(str(out), file_type="glb")


def make_generator(triposr_dir: Path) -> Callable[[str, Path, Path], Path]:
    def generate(card_id: str, art: Path, out_dir: Path) -> Path:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                [sys.executable, "run.py", str(art), "--output-dir", tmp],
                cwd=triposr_dir, check=True, capture_output=True,
            )
            tmp_p = Path(tmp)
            mesh = next(tmp_p.rglob("*.glb"), None) or next(tmp_p.rglob("*.obj"), None)
            if mesh is None:
                raise FileNotFoundError(f"TripoSR produced no mesh for {card_id}")
            out = out_dir / f"{card_id}.glb"
            if mesh.suffix == ".glb":
                out.write_bytes(mesh.read_bytes())
            else:
                _to_glb(mesh, out)
            return out
    return generate


def generate_missing(
    ids: list[str],
    generate: Callable[[str, Path, Path], Path],
    out_dir: Path,
    art_dir: Path,
    log: list[str],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for cid in ids:
        out = out_dir / f"{cid}.glb"
        if out.exists():
            continue
        art = art_dir / f"{cid}.png"
        if not art.exists():
            log.append(f"skip (no art): {cid}")
            continue
        try:
            generate(cid, art, out_dir)
            log.append(f"done: {cid}")
        except Exception as exc:  # noqa: BLE001 — one bad card must not kill the batch
            log.append(f"FAIL {cid}: {exc}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--heroes", type=Path)
    ap.add_argument("--art-dir", type=Path, default=Path("backend/images/cards_board"))
    ap.add_argument("--out-dir", type=Path, default=Path("backend/3dmodels"))
    ap.add_argument("--triposr-dir", type=Path)
    ap.add_argument("--write-manifest", action="store_true",
                    help="build backend/scripts/3d/manifest.json from --heroes + recommended_decks.json and exit")
    args = ap.parse_args(argv)

    if args.write_manifest:
        hero_ids = [ln.strip() for ln in args.heroes.read_text().splitlines() if ln.strip()] if args.heroes else []
        ids = build_manifest(Path("frontend/src/data/recommended_decks.json"), hero_ids)
        out = Path("backend/scripts/3d/manifest.json")
        out.write_text(json.dumps(ids))
        print(f"wrote {out} ({len(ids)} cards)")
        return 0

    if not (args.manifest and args.triposr_dir):
        ap.error("--manifest and --triposr-dir are required unless --write-manifest")
    log: list[str] = []
    generate_missing(load_manifest(args.manifest), make_generator(args.triposr_dir),
                     args.out_dir, args.art_dir, log)
    for line in log:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Also create `backend/scripts/3d/heroes.txt` with a comment header listing one hero card id per line (populate from the app's playable heroes — the `HERO_*` card ids shown in the deck-builder/gallery). No `__init__.py` is needed: the test loads the module via `sys.path`, matching how the other scripts in `backend/scripts/` are run.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_3d_models.py -v`
Expected: PASS.

- [ ] **Step 6: Run the batch (offline, on the dev Mac — may take a while on MPS/CPU)**

```bash
python backend/scripts/3d/generate_models.py --write-manifest --heroes backend/scripts/3d/heroes.txt
python backend/scripts/3d/generate_models.py --manifest backend/scripts/3d/manifest.json --triposr-dir ~/src/TripoSR
```
Expected: `backend/3dmodels/{id}.glb` files for heroes + meta minions; `manifest.json` written; failures logged, batch continues.

- [ ] **Step 7: Commit**

```bash
git add backend/scripts/3d backend/tests/test_3d_models.py
git commit -m "feat(3d): TripoSR batch GLB generation script"
```

---

### Task 14: Toggle button + WebGL auto-fallback + flip to 3D default

**Files:**
- Modify: `frontend/src/pages/GameBoard.tsx`, `frontend/src/components/Battlefield3D.tsx`, `frontend/src/three/viewMode.ts`

**Interfaces:**
- Consumes: `getViewMode`, `setViewMode`, `effectiveViewMode`.
- Produces: a **2D | 3D** button in the status bar; default view 3D; auto-fallback to 2D when WebGL is unavailable. This is the "flip" — from here on the 3D board is the primary view and the 2D board is the toggle target.

- [ ] **Step 1: Add a WebGL probe to `viewMode.ts`**

```ts
/** True if the browser can create a WebGL2 context. Cheap and synchronous. */
export function webglAvailable(): boolean {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
}
```

- [ ] **Step 2: Add the toggle button + default 3D in `GameBoard.tsx`**

```tsx
import Battlefield3D from "../components/Battlefield3D";
import { getViewMode, setViewMode, effectiveViewMode, webglAvailable, type ViewMode } from "../three/viewMode";

// Inside GameBoard:
const [viewMode, setView] = useState<ViewMode>(() => effectiveViewMode(webglAvailable(), getViewMode()));
const show3d = viewMode === "3d";
const toggleView = () => {
  const next: ViewMode = show3d ? "2d" : "3d";
  setViewMode(next);
  setView(effectiveViewMode(webglAvailable(), next));
};
```

In the status/action bar (next to the mute button) add:

```tsx
<button onClick={toggleView} className="rounded bg-slate-700 px-3 py-1 text-sm font-semibold"
  title="Switch between the 3D and 2D board">
  {show3d ? "2D" : "3D"}
</button>
```

Render the board via the toggle (replacing the dev-only `?view=3d` check):

```tsx
{show3d ? <Battlefield3D /> : <Board2D ... existing props ... />}
```

- [ ] **Step 3: Verify — build + manual toggle test**

Run: `cd frontend && npm run build` — PASS.
Manual: fresh browser → default is 3D; toggle to 2D, reload → still 2D (persisted); toggle back to 3D, reload → 3D. Temporarily simulate `webglAvailable() === false` (stub it) → forced 2D. Play a full game vs AI in 3D and one in 2D.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/GameBoard.tsx frontend/src/components/Battlefield3D.tsx frontend/src/three/viewMode.ts
git commit -m "feat(3d): 2D/3D toggle, 3D default, WebGL auto-fallback (flip commit)"
```

- [ ] **Step 5: Push + deploy via the trail (PR to main → Mini updates)**

```bash
git push -u origin feat/3d-battlefield
# open a PR (branch protection requires one), merge to main
# then: ssh robot@robotdeMac-mini.local '~/update-deepstone.sh'
```
Expected: the Mini pulls the 3D board, `npm run build` succeeds, and the site serves the 3D board by default.

---

## Self-Review Notes

- Spec coverage: board-only 3D (Tasks 3, 8–10, 14), R3F (Tasks 1, 8–10, 12), TripoSR heroes+meta pool + card-plane fallback (Tasks 5, 13; fallback in Unit3D/CardPlane), core animations (Task 10), 2D⇄3D toggle default 3D + WebGL fallback (Tasks 2, 14), branch+flip trajectory (Task 14), `/models` serving (Task 11), gitignore (Task 1).
- All model normalization is frontend-load-time (Task 12), single owner — the script (Task 13) only converts OBJ→GLB.
- The `?view=` dev param from Task 8 is replaced by the real toggle in Task 14.
- Backend remains a pure add-on: only the `/models` static mount + config.
