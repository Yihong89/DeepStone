import json
from typing import TypedDict

from ..config import settings


class CardMeta(TypedDict, total=False):
    id: str
    name: str
    text: str
    cost: int | None
    attack: int | None
    health: int | None
    type: str
    cardClass: str
    rarity: str
    set: str
    collectible: bool


_cards: list[CardMeta] = []
_map: dict[str, CardMeta] = {}


def load_cards() -> list[CardMeta]:
    """Load cards.json once and cache it. Returns the list of card metas."""
    global _cards, _map
    if _cards:
        return _cards
    with open(settings.cards_json_path, encoding="utf-8") as f:
        _cards = json.load(f)
    _map = {c["id"]: c for c in _cards}
    return _cards


def get_card_map() -> dict[str, CardMeta]:
    return _map


def get_card(card_id: str) -> CardMeta | None:
    return _map.get(card_id)


def build_ai_deck(hero_class: str) -> list[str]:
    """Build a legal 30-card deck for an AI opponent from the card universe."""
    pool = [c for c in load_cards() if c["cardClass"] in (hero_class, "NEUTRAL")]
    deck: list[str] = []
    for c in pool:
        copies = 1 if c["rarity"] == "LEGENDARY" else 2
        for _ in range(min(copies, 30 - len(deck))):
            deck.append(c["id"])
        if len(deck) >= 30:
            break
    return deck
