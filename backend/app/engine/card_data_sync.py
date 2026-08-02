"""Sync base card stats from the current hearthstone_data package.

Fireplace's bundled CardDefs.xml is a frozen snapshot (its last upstream
change was 2025-12, and the card data inside predates recent balance
patches). Fireplace's db.initialize() merges that frozen snapshot ON TOP of
the current hearthstone_data, so stale attack/health/cost win. This module
copies the current values back onto collectible cards after the DB is built,
fixing the drift (e.g. Knife Juggler showing 2/2 instead of the current 3/2).

Called at engine init and by scripts/build_cards.py so the board and the
deck-builder agree with each other and with the real card.
"""
from hearthstone import cardxml
from hearthstone.enums import GameTag

# Base stats that change with balance patches. Non-collectible enchantments
# and tokens are deliberately untouched: their stats come from card scripts.
_STAT_TAGS = (GameTag.ATK, GameTag.HEALTH, GameTag.COST)


def sync_current_stats(card_db) -> int:
    """Overwrite ATK/HEALTH/COST on collectible cards from current hearthstone_data.

    Mutates card_db in place (fireplace's CardDB and hearthstone's cardxml both
    expose a ``.tags`` dict keyed by GameTag). Returns how many cards changed;
    a second call is a no-op, so it is safe to run repeatedly.
    """
    fresh, _ = cardxml.load(locale="enUS")
    corrected = 0
    for card_id, fresh_card in fresh.items():
        if fresh_card.tags.get(GameTag.COLLECTIBLE) != 1:
            continue
        card = card_db.get(card_id)
        if card is None:
            continue
        changed = False
        for tag in _STAT_TAGS:
            value = fresh_card.tags.get(tag)
            if value is not None and card.tags.get(tag) != value:
                card.tags[tag] = value
                changed = True
        if changed:
            corrected += 1
    return corrected
