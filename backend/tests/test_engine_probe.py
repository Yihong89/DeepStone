from tests.engine_utils import build_deck, run_scripted_game
from app.engine.heroes import HERO_BY_CLASS


def test_full_game_bot_vs_bot():
    deck1 = build_deck("MAGE")
    deck2 = build_deck("MAGE")
    game = run_scripted_game(deck1, deck2, HERO_BY_CLASS["MAGE"], HERO_BY_CLASS["MAGE"])
    assert game.ended
    states = [p.playstate.name for p in game.players]
    assert any(s in ("WON", "LOST", "TIED") for s in states)
