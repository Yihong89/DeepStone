from fireplace.game import Game
from fireplace.player import Player

from app.engine.heroes import HERO_BY_CLASS
from app.engine.serialize import choice_payload, serialize
from tests.engine_utils import build_deck


def _fresh_game() -> Game:
    deck = build_deck("MAGE", 10)
    p1 = Player("P1", deck, HERO_BY_CLASS["MAGE"])
    p2 = Player("P2", deck, HERO_BY_CLASS["MAGE"])
    return Game([p1, p2], seed=1)


def test_snapshot_shape():
    game = _fresh_game()
    game.start()
    snap = serialize(game, 0)
    assert snap["turn"] == 0
    assert snap["current_player"] == 0
    assert len(snap["players"]) == 2
    me, opp = snap["players"]
    assert me["index"] == 0
    assert opp["index"] == 1
    assert me["hero"]["name"]
    assert "hand" in me and "field" in me and "mana" in me and "max_mana" in me


def test_joiner_perspective_is_first():
    """serialize always puts the viewer first — players[0] is the viewer's own
    side, regardless of the actual game index. The board UI relies on this
    (it renders players[0] as 'me'), so the joiner (index 1) must also see
    their own hero/hand first and the challenger hidden."""
    game = _fresh_game()
    game.start()
    me, opp = serialize(game, 1)["players"]
    assert me["index"] == 1
    assert opp["index"] == 0
    assert len(me["hand"]) == len(game.players[1].hand)
    for card in me["hand"]:
        assert "name" in card  # viewer's own hand is visible
    for card in opp["hand"]:
        assert "name" not in card  # opponent's hand is hidden


def test_opponent_hand_is_hidden():
    game = _fresh_game()
    game.start()
    me, opp = serialize(game, 0)["players"]
    assert len(me["hand"]) == len(game.players[0].hand)
    assert len(opp["hand"]) == len(game.players[1].hand)
    for card in opp["hand"]:
        assert "name" not in card and "cost" not in card


def test_choice_payload():
    game = _fresh_game()
    game.start()
    for player in game.players:
        if player.choice is not None:
            payload = choice_payload(player.choice)
            assert "cards" in payload and payload["cards"]
            break
    else:
        raise AssertionError("Expected a pending mulligan choice after game.start()")
