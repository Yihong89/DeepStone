import { describe, expect, it } from "vitest";
import type { GameCard } from "../api/types";
import { resolveTargetAction } from "./targeting";

// Realistic board entities.
const friendlyMinion: GameCard = { entity_id: 1, id: "BT_194", name: "Shadowhoof Slayer" };
const enemyMinion: GameCard = { entity_id: 2, id: "CS2_120", name: "River Crocolisk" };
const enemyHero: GameCard = { entity_id: 3, name: "Enemy Hero" };
// The card being played / the attacker.
const cleric: GameCard = { entity_id: 10, id: "EX1_019", name: "Shattered Sun Cleric" };
const attacker: GameCard = { entity_id: 20, name: "My Attacker" };
const heroPower: GameCard = { entity_id: 30, name: "Hero Power" };

describe("resolveTargetAction — play selection", () => {
  it("applies a spell/battlecry to a friendly minion that is a valid target (regression)", () => {
    // Shattered Sun Cleric's battlecry targets a friendly minion.
    const selection = { type: "play" as const, source: cleric };
    const targets = new Set([friendlyMinion.entity_id]);

    const msg = resolveTargetAction(selection, friendlyMinion, targets);

    expect(msg).toEqual({
      type: "action",
      action: { kind: "play_card", card: 10, target: 1, index: 0, choose: null },
    });
  });

  it("applies a spell/battlecry to an enemy minion that is a valid target", () => {
    const selection = { type: "play" as const, source: cleric };
    const targets = new Set([enemyMinion.entity_id]);

    const msg = resolveTargetAction(selection, enemyMinion, targets);

    expect(msg?.action.kind).toBe("play_card");
    expect(msg?.action).toMatchObject({ card: 10, target: enemyMinion.entity_id });
  });

  it("returns null when the clicked character is not a valid target (selection is cancelled)", () => {
    const selection = { type: "play" as const, source: cleric };
    // Only the enemy hero is a valid target; the friendly minion isn't.
    const targets = new Set([enemyHero.entity_id]);

    expect(resolveTargetAction(selection, friendlyMinion, targets)).toBeNull();
  });
});

describe("resolveTargetAction — attack selection", () => {
  it("sends an attack action when the clicked enemy is a valid attack target", () => {
    const selection = { type: "attack" as const, source: attacker };
    const targets = new Set([enemyMinion.entity_id, enemyHero.entity_id]);

    const msg = resolveTargetAction(selection, enemyMinion, targets);

    expect(msg).toEqual({
      type: "action",
      action: { kind: "attack", source: 20, target: enemyMinion.entity_id },
    });
  });

  it("returns null for a friendly minion (friendly minions are never attack targets)", () => {
    const selection = { type: "attack" as const, source: attacker };
    const targets = new Set([enemyMinion.entity_id]);

    expect(resolveTargetAction(selection, friendlyMinion, targets)).toBeNull();
  });
});

describe("resolveTargetAction — hero power selection", () => {
  it("applies a hero power to a friendly target (e.g. healing your own minion)", () => {
    const selection = { type: "hero_power" as const, source: heroPower };
    const targets = new Set([friendlyMinion.entity_id, enemyHero.entity_id]);

    const msg = resolveTargetAction(selection, friendlyMinion, targets);

    expect(msg).toEqual({
      type: "action",
      action: { kind: "hero_power", target: friendlyMinion.entity_id },
    });
  });

  it("applies a hero power to an enemy target", () => {
    const selection = { type: "hero_power" as const, source: heroPower };
    const targets = new Set([enemyHero.entity_id]);

    const msg = resolveTargetAction(selection, enemyHero, targets);

    expect(msg?.action).toMatchObject({ kind: "hero_power", target: enemyHero.entity_id });
  });
});

describe("resolveTargetAction — edge cases", () => {
  it("returns null when there is no active selection (plain click, nothing to resolve)", () => {
    expect(resolveTargetAction(null, friendlyMinion, new Set([friendlyMinion.entity_id]))).toBeNull();
  });

  it("returns null when the target set is empty", () => {
    const selection = { type: "play" as const, source: cleric };
    expect(resolveTargetAction(selection, friendlyMinion, new Set())).toBeNull();
  });

  it("returns null when the clicked entity id is not in the target set", () => {
    const selection = { type: "hero_power" as const, source: heroPower };
    expect(resolveTargetAction(selection, friendlyMinion, new Set([999]))).toBeNull();
  });
});
