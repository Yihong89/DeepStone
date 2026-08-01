"""Shared helpers for engine integration tests (real Fireplace card data)."""
import json
import logging
from pathlib import Path

import fireplace.cards as fireplace_cards
from fireplace.exceptions import GameOver
from fireplace.game import Game
from fireplace.player import Player

# Fireplace logs every action at INFO; quiet it so engine tests run fast.
logging.getLogger("fireplace").setLevel(logging.WARNING)

# Fireplace lazily initializes its card DB (via db.filter); do it explicitly.
if not fireplace_cards.db.initialized:
    fireplace_cards.db.initialize()

CARDS = json.loads(Path("cards.json").read_text())


def build_deck(card_class: str, n: int = 30) -> list[str]:
    """Build a deterministic n-card deck from the real card universe."""
    pool = [c for c in CARDS if c["cardClass"] in (card_class, "NEUTRAL")]
    deck: list[str] = []
    for c in pool:
        copies = 1 if c["rarity"] == "LEGENDARY" else 2
        for _ in range(min(copies, n - len(deck))):
            deck.append(c["id"])
        if len(deck) >= n:
            break
    return deck


def run_scripted_game(deck1, deck2, hero1, hero2, seed=42) -> Game:
    """Play a full game where both players only pass (mulligan nothing, end turn).
    The game ends via fatigue. Exercises the real engine loop end-to-end."""
    p1 = Player("Bot1", deck1, hero1)
    p2 = Player("Bot2", deck2, hero2)
    game = Game([p1, p2], seed=seed)
    game.start()
    # Resolve both mulligan choices (keep all)
    for player in game.players:
        if player.choice is not None:
            player.choice.choose()
    # Drive turns until the game is over
    while not game.ended:
        if game.current_player.choice is not None:
            game.current_player.choice.choose(game.current_player.choice.cards[0])
            continue
        try:
            game.end_turn()
        except GameOver:
            break
    return game
