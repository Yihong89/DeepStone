"""Generate cards.json from hearthstone_data (the same card data Fireplace uses).

The deck-builder universe is restricted to cards from sets that Fireplace's
engine actually implements. "Supported sets" are defined as the card sets that
contain at least one Fireplace-scripted card — this keeps vanilla (unscripted)
cards from supported expansions while excluding later sets Fireplace cannot play.
"""
import json
import re
import sys
from importlib import import_module

from hearthstone.cardxml import load

from fireplace.cards import CARD_SETS

_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*_\d+[A-Za-z0-9_]*$")
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


def supported_sets(db) -> set[str]:
    """CardSet enum names that contain at least one Fireplace-scripted card."""
    scripted: set[str] = set()
    for cardset in CARD_SETS:
        mod = import_module(f"fireplace.cards.{cardset}")
        for name in dir(mod):
            if _ID_RE.match(name):
                scripted.add(name)
    return {db[i].card_set.name for i in scripted if i in db}


def main() -> None:
    db, _ = load()
    out = sys.argv[1] if len(sys.argv) > 1 else "cards.json"
    sets = supported_sets(db)
    cards = []
    for c in db.values():
        if not getattr(c, "collectible", False):
            continue
        if c.card_set.name not in sets:
            continue
        if getattr(c, "type", None) and c.type.name not in _DECK_TYPES:
            continue
        cards.append(to_meta(c))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=1)
    print(f"Wrote {len(cards)} collectible cards to {out} (supported sets: {len(sets)})")


if __name__ == "__main__":
    main()
