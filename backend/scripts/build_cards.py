"""Generate cards.json from Fireplace's own bundled CardDefs.xml.

Using Fireplace's bundled data (the same file its engine loads) guarantees the
deck-builder universe exactly matches the set of cards the engine can play.
"""
import json
import sys

from hearthstone.cardxml import load

from app.engine.fireplace_setup import ensure_carddefs

_DECK_TYPES = {"MINION", "SPELL", "WEAPON"}


def to_meta(c) -> dict:
    name = lambda v: v.name if hasattr(v, "name") else str(v)  # noqa: E731
    return {
        "id": c.card_id,
        "name": c.name,
        "text": getattr(c, "description", None) or "",
        "cost": getattr(c, "cost", None),
        "attack": getattr(c, "atk", None),
        "health": getattr(c, "health", None),
        "type": name(getattr(c, "type", "")),
        "cardClass": name(getattr(c, "card_class", "")),
        "rarity": name(getattr(c, "rarity", "")),
        "set": name(getattr(c, "card_set", "")),
        "collectible": bool(getattr(c, "collectible", False)),
    }


def main() -> None:
    carddefs = ensure_carddefs()
    db, _ = load(path=str(carddefs))
    out = sys.argv[1] if len(sys.argv) > 1 else "cards.json"
    cards = []
    for c in db.values():
        if not getattr(c, "collectible", False):
            continue
        if getattr(c, "type", None) and c.type.name not in _DECK_TYPES:
            continue
        cards.append(to_meta(c))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=1)
    print(f"Wrote {len(cards)} collectible cards to {out}")


if __name__ == "__main__":
    main()
