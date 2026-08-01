from fireplace.game import Game
from fireplace.player import Player

from app.engine.bot import choose_main_action, choose_mulligan
from app.engine.heroes import HERO_BY_CLASS
from tests.engine_utils import build_deck


def test_bot_mulligan_returns_entity_ids():
    deck = build_deck("MAGE", 10)
    p = Player("Bot", deck, HERO_BY_CLASS["MAGE"])
    game = Game([p, Player("Bot2", deck, HERO_BY_CLASS["MAGE"])], seed=3)
    game.start()
    assert p.choice is not None
    result = choose_mulligan(p)
    assert isinstance(result, list)
    assert all(isinstance(x, int) for x in result)


def test_bot_main_action_is_well_formed():
    deck = build_deck("MAGE", 10)
    p = Player("Bot", deck, HERO_BY_CLASS["MAGE"])
    game = Game([p, Player("Bot2", deck, HERO_BY_CLASS["MAGE"])], seed=3)
    game.start()
    for player in game.players:
        if player.choice is not None:
            player.choice.choose()
    action = choose_main_action(game.current_player)
    assert action["kind"] in {"play_card", "attack", "hero_power", "end_turn"}
    if action["kind"] in {"play_card", "attack", "hero_power"}:
        assert action.get("target") is None or isinstance(action.get("target"), int)
