"""Tests for the post-init card-stats sync (current hearthstone_data wins)."""
import pytest
from hearthstone import cardxml
from hearthstone.enums import GameTag

from app.engine.card_data_sync import sync_current_stats
from app.engine.fireplace_setup import carddefs_path, ensure_carddefs


def _frozen_db():
    # Bypass cardxml's module-level cache: sync mutates the parsed objects in
    # place, so each test must start from a clean parse of the frozen snapshot.
    cardxml.cardid_cache.clear()
    ensure_carddefs()
    db, _ = cardxml.load(path=str(carddefs_path()))
    return db


def test_sync_fixes_stale_stats_and_is_idempotent():
    db = _frozen_db()
    # Fireplace's frozen snapshot predates the Knife Juggler rebalance: 2/2.
    assert db["NEW1_019"].tags.get(GameTag.ATK) == 2
    assert db["NEW1_019"].tags.get(GameTag.HEALTH) == 2

    n = sync_current_stats(db)

    # Current hearthstone_data says 3/2 (matches the card art and real card).
    assert db["NEW1_019"].tags.get(GameTag.ATK) == 3
    assert db["NEW1_019"].tags.get(GameTag.HEALTH) == 2
    assert n > 0
    # Second pass has nothing left to fix.
    assert sync_current_stats(db) == 0


def test_sync_skips_non_collectible_and_unknown_cards(monkeypatch):
    class Fake:
        def __init__(self, tags):
            self.tags = dict(tags)

    fresh = {
        "COLL": Fake({GameTag.COLLECTIBLE: 1, GameTag.ATK: 3, GameTag.HEALTH: 2, GameTag.COST: 2}),
        "TOKEN": Fake({GameTag.ATK: 9}),  # no COLLECTIBLE tag -> must be skipped
    }
    monkeypatch.setattr(cardxml, "load", lambda locale="enUS": (fresh, None))

    card_db = {
        "COLL": Fake({GameTag.COLLECTIBLE: 1, GameTag.ATK: 2, GameTag.HEALTH: 2, GameTag.COST: 2}),
        "TOKEN": Fake({GameTag.ATK: 5}),  # in db but not collectible -> untouched
    }
    n = sync_current_stats(card_db)

    assert card_db["COLL"].tags[GameTag.ATK] == 3
    assert card_db["COLL"].tags[GameTag.HEALTH] == 2
    assert card_db["TOKEN"].tags[GameTag.ATK] == 5  # left alone
    assert n == 1


def test_sync_tolerates_missing_card(monkeypatch):
    class Fake:
        def __init__(self, tags):
            self.tags = dict(tags)

    fresh = {"ONLY_FRESH": Fake({GameTag.COLLECTIBLE: 1, GameTag.ATK: 3})}
    monkeypatch.setattr(cardxml, "load", lambda locale="enUS": (fresh, None))

    assert sync_current_stats({}) == 0  # no matching card, no crash
