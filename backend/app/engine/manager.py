"""GameManager — registry of challenges, live sessions, and WebSocket wiring."""
import asyncio
import secrets
import time

from fastapi import WebSocket

from .carddata import build_ai_deck
from .game_session import GameSession
from .heroes import HERO_BY_CLASS


def _hero_id(hero_class: str) -> str:
    """Map a deck's hero class name to the hero card ID Fireplace expects."""
    return HERO_BY_CLASS.get(hero_class, "HERO_08")


class _Challenge:
    def __init__(self, code, user_id, deck_id, hero, card_ids, expires_at):
        self.code = code
        self.user_id = user_id
        self.deck_id = deck_id
        self.hero = hero
        self.card_ids = card_ids
        self.expires_at = expires_at


class GameManager:
    def __init__(self):
        self._challenges: dict[str, _Challenge] = {}
        self._game_by_code: dict[str, str] = {}  # challenge code -> game_id once joined
        self._sessions: dict[str, GameSession] = {}
        self._ws: dict[str, dict[int, WebSocket]] = {}
        self._loops: dict[str, asyncio.AbstractEventLoop] = {}
        self._started: set[str] = set()

    # ---- challenges ----
    def create_challenge(self, user_id, deck_id, hero, card_ids) -> str:
        code = "".join(
            secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6)
        )
        self._challenges[code] = _Challenge(
            code, user_id, deck_id, hero, card_ids, time.time() + 1800
        )
        return code

    def join_challenge(self, code, user_id, deck_id, hero_class, card_ids):
        ch = self._challenges.get(code)
        if ch is None or ch.expires_at < time.time():
            raise KeyError("Challenge not found or expired")
        del self._challenges[code]
        game_id = secrets.token_hex(8)
        session = GameSession(
            game_id,
            {"name": "Challenger", "hero": _hero_id(ch.hero), "deck": ch.card_ids, "is_bot": False},
            {"name": "Joiner", "hero": _hero_id(hero_class), "deck": card_ids, "is_bot": False},
        )
        self._sessions[game_id] = session
        self._game_by_code[code] = game_id  # lets the challenger discover the game
        return game_id, ch.user_id, ch.deck_id, ch.hero

    def get_game_id_for_code(self, code: str) -> str | None:
        return self._game_by_code.get(code)

    def create_ai_game(self, user_id, deck_id, hero_class, card_ids, username) -> str:
        game_id = secrets.token_hex(8)
        session = GameSession(
            game_id,
            {"name": username, "hero": _hero_id(hero_class), "deck": card_ids, "is_bot": False},
            {"name": "AI", "hero": _hero_id(hero_class), "deck": build_ai_deck(hero_class), "is_bot": True},
        )
        self._sessions[game_id] = session
        return game_id

    # ---- sessions ----
    def get_session(self, game_id: str) -> GameSession | None:
        return self._sessions.get(game_id)

    def player_index_for(self, game_id: str, user_id: int, player1_id, player2_id):
        if player1_id == user_id:
            return 0
        if player2_id == user_id:
            return 1
        return None

    # ---- websocket ----
    def register_ws(self, game_id: str, player_index: int, ws: WebSocket, loop) -> None:
        self._ws.setdefault(game_id, {})[player_index] = ws
        self._loops[game_id] = loop
        session = self._sessions.get(game_id)
        if session is None:
            return
        session.set_send(player_index, lambda idx, msg: self._ws_send(game_id, idx, msg))
        self._maybe_start(game_id, session)

    def _ws_send(self, game_id: str, player_index: int, message: dict) -> None:
        loop = self._loops.get(game_id)
        ws = self._ws.get(game_id, {}).get(player_index)
        if loop is not None and ws is not None:
            loop.call_soon_threadsafe(self._do_send, ws, message)

    def _do_send(self, ws: WebSocket, message: dict) -> None:
        async def _send():
            try:
                await ws.send_json(message)
            except Exception:
                pass  # client disconnected — ignore

        asyncio.ensure_future(_send())

    def _maybe_start(self, game_id: str, session: GameSession) -> None:
        if game_id in self._started or session.game.ended:
            return
        ws = self._ws.get(game_id, {})
        for i in range(2):
            if not session.player_is_bot(i) and i not in ws:
                return
        self._started.add(game_id)
        session.start()


manager = GameManager()
