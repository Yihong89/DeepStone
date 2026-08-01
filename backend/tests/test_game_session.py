from app.engine.game_session import GameSession
from app.engine.heroes import HERO_BY_CLASS
from tests.engine_utils import build_deck


def _bot_spec(name):
    deck = build_deck("MAGE", 15)
    return {"name": name, "hero": HERO_BY_CLASS["MAGE"], "deck": deck, "is_bot": True}


def test_bot_vs_bot_session_completes():
    session = GameSession(
        "sess1",
        _bot_spec("BotA"),
        _bot_spec("BotB"),
        seed=7,
    )
    snapshots = []
    session.set_send(0, lambda i, m: snapshots.append((i, m)))
    session.set_send(1, lambda i, m: snapshots.append((i, m)))
    session.start()
    session.join(timeout=60)
    assert session.game.ended
    assert any(m["type"] == "game_over" for _, m in snapshots)
    # snapshots were broadcast for both players
    assert any(i == 0 and m["type"] == "snapshot" for i, m in snapshots)
    assert any(i == 1 and m["type"] == "snapshot" for i, m in snapshots)


def test_snapshot_available_before_start():
    session = GameSession("sess2", _bot_spec("A"), _bot_spec("B"))
    snap = session.snapshot_for(0)
    assert "players" in snap and len(snap["players"]) == 2
