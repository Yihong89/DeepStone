"""GameSession — bridges the synchronous Fireplace engine to async WebSockets.

Each match runs a Fireplace Game in a dedicated worker thread. Whenever the
engine needs a decision (mulligan, Discover choice, main action) the thread
blocks on a threading.Event while the async WS layer delivers the prompt to
the player's browser and submits the reply. Bots decide inline.
"""
import logging
import threading

from fireplace.actions import Concede, MulliganChoice, PlayHeroPower
from fireplace.exceptions import GameOver
from fireplace.game import Game
from fireplace.player import Player
from hearthstone.enums import BlockType

from . import bot
from .serialize import choice_payload, serialize

log = logging.getLogger(__name__)


def entity_map(game: Game) -> dict[int, object]:
    """Map every entity_id to its entity, covering all zones.

    Fireplace's Game.entities only yields heroes/powers/players — it does NOT
    include hand, field, deck, graveyard, or secret cards. Actions reference
    cards by entity_id, so the map must walk every zone explicitly.
    """
    m: dict[int, object] = {}

    def add(e) -> None:
        if e is not None:
            m[e.entity_id] = e

    add(game)
    for p in game.players:
        add(p)
        add(p.hero)
        if p.hero is not None:
            add(p.hero.power)
        add(p.weapon)
        for zone in (p.hand, p.field, p.deck, p.graveyard, p.secrets):
            for c in zone:
                add(c)
    for c in game.setaside:
        add(c)
    return m


class _PendingDecision:
    def __init__(self, player_index: int, kind: str, data: dict):
        self.player_index = player_index
        self.kind = kind
        self.data = data
        self._event = threading.Event()
        self.result = None

    def resolve(self, result) -> None:
        self.result = result
        self._event.set()


class GameSession:
    def __init__(self, game_id: str, player1: dict, player2: dict, seed=None):
        self.game_id = game_id
        self._players = [player1, player2]
        self._sends = {0: None, 1: None}
        self._decisions: dict[int, _PendingDecision] = {}
        self._lock = threading.Lock()
        self._game = Game(
            [
                Player(player1["name"], player1["deck"], player1["hero"]),
                Player(player2["name"], player2["deck"], player2["hero"]),
            ],
            seed=seed,
        )
        self._thread: threading.Thread | None = None

    @property
    def game(self) -> Game:
        return self._game

    # ---- wiring ----
    def set_send(self, player_index: int, callback) -> None:
        self._sends[player_index] = callback

    def _send(self, player_index: int, message: dict) -> None:
        cb = self._sends[player_index]
        if cb is not None:
            cb(player_index, message)

    def submit_decision(self, player_index: int, decision: dict) -> None:
        with self._lock:
            pending = self._decisions.get(player_index)
            if pending is not None:
                pending.resolve(decision)

    # ---- decision plumbing ----
    def _ask(self, player_index: int, kind: str, data: dict) -> dict:
        if self._players[player_index]["is_bot"]:
            return self._bot_decision(player_index, kind)
        pending = _PendingDecision(player_index, kind, data)
        with self._lock:
            self._decisions[player_index] = pending
        self._send(player_index, data)
        pending._event.wait(120)  # 120s grace; treat as concede on timeout
        with self._lock:
            self._decisions.pop(player_index, None)
        if pending.result is None:
            return {"kind": "concede"}
        return pending.result

    def _bot_decision(self, player_index: int, kind: str) -> dict:
        player = self._game.players[player_index]
        if kind == "mulligan":
            return {"cards": bot.choose_mulligan(player)}
        if kind == "choice":
            return {"card": bot.choose_choice(player)}
        return bot.choose_main_action(player)

    def _apply_mulligan(self, player_index: int, decision: dict) -> None:
        player = self._game.players[player_index]
        choice = player.choice
        if choice is None:
            return
        entity_ids = decision.get("cards", [])
        cards = {c.entity_id: c for c in choice.cards}
        choice.choose(*[cards[eid] for eid in entity_ids if eid in cards])

    def _apply_choice(self, player_index: int, decision: dict) -> None:
        player = self._game.players[player_index]
        choice = player.choice
        if choice is None:
            return
        eid = decision.get("card")
        card = next((c for c in choice.cards if c.entity_id == eid), choice.cards[0])
        choice.choose(card)

    def _apply_main_action(self, player_index: int, decision: dict) -> None:
        game = self._game
        player = game.players[player_index]
        action = decision.get("action", decision)
        kind = action.get("kind")
        by_id = entity_map(game)
        try:
            if kind == "end_turn":
                game.end_turn()
            elif kind == "play_card":
                card = by_id.get(action["card"])
                if card is None:
                    raise ValueError(f"unknown card entity {action.get('card')}")
                target = by_id.get(action["target"]) if action.get("target") else None
                choose = by_id.get(action["choose"]) if action.get("choose") else None
                game.play_card(card, target, action.get("index", 0), choose)
            elif kind == "attack":
                src = by_id.get(action["source"])
                tgt = by_id.get(action["target"])
                if src is None or tgt is None:
                    raise ValueError(f"unknown attack entities {action.get('source')}->{action.get('target')}")
                game.attack(src, tgt)
            elif kind == "hero_power":
                hp = player.hero.power
                target = by_id.get(action["target"]) if action.get("target") else None
                game.main_power(hp, [PlayHeroPower(hp, target)], target)
            elif kind == "concede":
                game.action_block(player, [Concede()], BlockType.PLAY)
            else:
                raise ValueError(f"unknown action kind: {kind}")
        except GameOver:
            pass
        except Exception as e:
            # Defensive: a bad action must never freeze the match. End the turn.
            log.warning("Action %r failed (%s); ending turn", action, e)
            if not game.ended:
                try:
                    game.end_turn()
                except GameOver:
                    pass

    def _prompt(self, player_index: int, kind: str, data: dict) -> None:
        decision = self._ask(player_index, kind, data)
        if kind == "mulligan":
            self._apply_mulligan(player_index, decision)
        elif kind == "choice":
            self._apply_choice(player_index, decision)
        else:
            self._apply_main_action(player_index, decision)

    # ---- game loop ----
    def _run(self) -> None:
        game = self._game
        game.start()
        self._broadcast()
        while not game.ended:
            # Resolve any pending choices (mulligan, discover, choose-one...)
            pending = [i for i, p in enumerate(game.players) if p.choice is not None]
            if pending:
                i = pending[0]
                choice = game.players[i].choice
                if isinstance(choice, MulliganChoice):
                    data = {"type": "mulligan", "cards": [c.entity_id for c in choice.cards]}
                    self._prompt(i, "mulligan", data)
                else:
                    data = {"type": "choice", "choice": choice_payload(choice)}
                    self._prompt(i, "choice", data)
                self._broadcast()
                continue
            # Main action phase for the current player
            i = 0 if game.current_player is game.players[0] else 1
            self._prompt(i, "main_action", {"type": "your_turn", "player": i})
            self._broadcast()
        for i in range(2):
            self._send(i, {"type": "game_over", "result": serialize(game, i)["result"]})

    def _broadcast(self) -> None:
        game = self._game
        for i in range(2):
            self._send(i, {"type": "snapshot", "state": serialize(game, i)})

    # ---- lifecycle ----
    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def join(self, timeout=None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    def snapshot_for(self, player_index: int) -> dict:
        return serialize(self._game, player_index)
