import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user
from ..engine.heroes import HERO_BY_CLASS
from ..engine.manager import manager
from ..models import Deck, Match, User
from ..schemas import DeckIdIn
from ..security import decode_token

router = APIRouter(prefix="/api/games", tags=["games"])


async def _load_deck(db: AsyncSession, deck_id: int, user: User) -> Deck:
    deck = await db.get(Deck, deck_id)
    if deck is None or deck.user_id != user.id:
        raise HTTPException(status_code=404, detail="Deck not found")
    return deck


def _cards(deck: Deck) -> list[str]:
    return json.loads(deck.card_ids)


async def _persist_match(db, game_id, p1, p2, d1, d2, h1, h2):
    db.add(Match(game_id=game_id, player1_id=p1, player2_id=p2,
                 deck1_id=d1, deck2_id=d2, hero1=h1, hero2=h2))
    await db.commit()


@router.post("/challenges")
async def create_challenge(data: DeckIdIn, user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_session)):
    deck = await _load_deck(db, data.deck_id, user)
    code = manager.create_challenge(user.id, deck.id, deck.hero_class, _cards(deck))
    return {"code": code}


@router.post("/challenges/{code}/join")
async def join_challenge(code: str, data: DeckIdIn, user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_session)):
    deck = await _load_deck(db, data.deck_id, user)
    try:
        game_id, ch_user, ch_deck, ch_hero = manager.join_challenge(
            code, user.id, deck.id, deck.hero_class, _cards(deck)
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Challenge not found or expired")
    await _persist_match(db, game_id, ch_user, user.id, ch_deck, deck.id, ch_hero, deck.hero_class)
    return {"game_id": game_id}


@router.post("/ai")
async def create_ai_game(data: DeckIdIn, user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_session)):
    deck = await _load_deck(db, data.deck_id, user)
    game_id = manager.create_ai_game(user.id, deck.id, deck.hero_class, _cards(deck), user.username)
    bot_hero = HERO_BY_CLASS.get(deck.hero_class, "HERO_08")
    await _persist_match(db, game_id, user.id, None, deck.id, None, deck.hero_class, bot_hero)
    return {"game_id": game_id}


async def _authorize_ws(token: str, db: AsyncSession) -> User:
    try:
        user_id = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid or inactive user")
    return user


@router.websocket("/{game_id}/ws")
async def game_ws(websocket: WebSocket, game_id: str, token: str,
                  db: AsyncSession = Depends(get_session)):
    user = await _authorize_ws(token, db)
    match = (await db.execute(select(Match).where(Match.game_id == game_id))).scalars().first()
    if match is None:
        await websocket.close(code=4004)
        return
    player_index = manager.player_index_for(game_id, user.id, match.player1_id, match.player2_id)
    if player_index is None:
        await websocket.close(code=4003)
        return
    session = manager.get_session(game_id)
    if session is None:
        await websocket.close(code=4004)
        return
    await websocket.accept()
    loop = asyncio.get_running_loop()
    manager.register_ws(game_id, player_index, websocket, loop)
    try:
        while True:
            msg = await websocket.receive_json()
            t = msg.get("type")
            if t == "mulligan":
                session.submit_decision(player_index, {"cards": msg.get("cards", [])})
            elif t == "choice":
                session.submit_decision(player_index, {"card": msg.get("card")})
            elif t == "action":
                session.submit_decision(player_index, {"action": msg["action"]})
    except WebSocketDisconnect:
        session.submit_decision(player_index, {"kind": "concede"})
