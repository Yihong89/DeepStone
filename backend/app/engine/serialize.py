from __future__ import annotations

from fireplace.actions import MulliganChoice
from fireplace.game import Game


def _hand_card(card, hidden: bool) -> dict:
    if hidden:
        return {"entity_id": card.entity_id}
    return {
        "entity_id": card.entity_id,
        "id": card.id,
        "name": card.data.name,
        "cost": card.cost,
        "text": getattr(card, "description", "") or "",
    }


def _character(card) -> dict:
    return {
        "entity_id": card.entity_id,
        "id": card.id,
        "name": card.data.name,
        "atk": card.atk,
        "max_health": card.max_health,
        "damage": card.damage,
        "taunt": card.taunt,
        "stealthed": card.stealthed,
        "divine_shield": getattr(card, "divine_shield", False),
        "frozen": card.frozen,
        "exhausted": card.exhausted,
        "num_attacks": getattr(card, "num_attacks", 0),
        "can_attack": card.can_attack() if hasattr(card, "can_attack") else False,
        "zone_position": getattr(card, "zone_position", None),
    }


def _hero(hero) -> dict:
    d = _character(hero)
    d["armor"] = hero.armor
    return d


def _hero_power(hp) -> dict | None:
    if hp is None:
        return None
    return {"entity_id": hp.entity_id, "id": hp.id, "name": hp.data.name, "cost": hp.cost}


def _weapon(w) -> dict | None:
    if w is None:
        return None
    return {
        "entity_id": w.entity_id,
        "id": w.id,
        "name": w.data.name,
        "atk": w.atk,
        "max_health": w.max_durability,
    }


def _player(player, index: int, hidden: bool) -> dict:
    return {
        "index": index,
        "hero": _hero(player.hero),
        "hero_power": _hero_power(player.hero.power),
        "weapon": _weapon(player.weapon),
        "deck_count": len(player.deck),
        "hand": [_hand_card(c, hidden) for c in player.hand],
        "field": [_character(c) for c in player.field],
        "secrets": [{"entity_id": c.entity_id} for c in player.secrets],
        "max_mana": player.max_mana,
        "mana": player.mana,
        "playstate": player.playstate.name,
    }


def _result(game: Game) -> dict | None:
    if not game.ended:
        return None
    states = [p.playstate for p in game.players]
    if "WON" in [s.name for s in states]:
        winner = 0 if states[0].name == "WON" else 1
    else:
        winner = None
    return {"winner": winner, "playstates": [s.name for s in states]}


def serialize(game: Game, for_player_index: int) -> dict:
    me = game.players[for_player_index]
    opp = game.players[1 - for_player_index]
    pending = None
    for i, p in enumerate(game.players):
        if p.choice is not None:
            kind = "mulligan" if isinstance(p.choice, MulliganChoice) else "choice"
            pending = {"player": i, "kind": kind}
            break
    cur = game.current_player
    return {
        "turn": game.turn,
        "current_player": 0 if cur is None or cur is game.players[0] else 1,
        "ended": game.ended,
        "result": _result(game),
        "players": [
            _player(me, for_player_index, hidden=False),
            _player(opp, 1 - for_player_index, hidden=True),
        ],
        "pending": pending,
    }


def card_summary(card) -> dict:
    return {
        "entity_id": card.entity_id,
        "id": card.id,
        "name": card.data.name,
        "cost": getattr(card, "cost", None),
        "atk": getattr(card, "atk", None),
        "max_health": getattr(card, "max_health", None),
        "text": getattr(card, "description", "") or "",
    }


def choice_payload(choice) -> dict:
    return {
        "cards": [card_summary(c) for c in choice.cards],
        "min": getattr(choice, "min_count", 1),
        "max": getattr(choice, "max_count", 1),
    }
