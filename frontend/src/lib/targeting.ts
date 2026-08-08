import type { GameCard } from "../api/types";

/** The kinds of target selection the board UI can be in. */
export type SelectionType = "attack" | "play" | "hero_power";

export interface Selection {
  type: SelectionType;
  /** The attacking minion / card being played / hero power source. */
  source: GameCard;
}

/** A message the board sends over the game WebSocket (see app/engine/serialize.py). */
export interface ActionMessage {
  type: "action";
  action: {
    kind: "play_card" | "attack" | "hero_power";
    card?: number;
    source?: number;
    target: number | null;
    index?: number;
    choose?: unknown;
  };
}

/**
 * Decide what to do when a character (friendly or enemy) is clicked while a
 * target selection is pending.
 *
 * Returns the action message to send, or null when the character isn't a valid
 * target (the caller then cancels the selection instead of sending anything).
 * This is shared by the friendly-minion and opponent-minion click handlers so
 * spells, battlecries and hero powers can target either side identically.
 */
export function resolveTargetAction(
  selection: Selection | null,
  card: GameCard,
  targetIds: ReadonlySet<number>,
): ActionMessage | null {
  if (!selection || !targetIds.has(card.entity_id)) return null;
  if (selection.type === "play") {
    return {
      type: "action",
      action: { kind: "play_card", card: selection.source.entity_id, target: card.entity_id, index: 0, choose: null },
    };
  }
  if (selection.type === "attack") {
    return {
      type: "action",
      action: { kind: "attack", source: selection.source.entity_id, target: card.entity_id },
    };
  }
  return {
    type: "action",
    action: { kind: "hero_power", target: card.entity_id },
  };
}
