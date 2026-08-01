import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user
from ..engine.deck_rules import validate_deck
from ..models import Deck, User
from ..schemas import DeckIn, DeckOut

router = APIRouter(prefix="/api/decks", tags=["decks"])


def _to_out(deck: Deck) -> dict:
    return {
        "id": deck.id,
        "user_id": deck.user_id,
        "name": deck.name,
        "hero_class": deck.hero_class,
        "card_ids": json.loads(deck.card_ids),
        "created_at": deck.created_at,
        "updated_at": deck.updated_at,
    }


@router.get("", response_model=list[DeckOut])
async def list_decks(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    decks = (
        await db.execute(select(Deck).where(Deck.user_id == user.id).order_by(Deck.updated_at.desc()))
    ).scalars().all()
    return [_to_out(d) for d in decks]


@router.post("", status_code=201, response_model=DeckOut)
async def create_deck(data: DeckIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    errors = validate_deck(data.hero_class, data.card_ids)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    deck = Deck(
        user_id=user.id,
        name=data.name,
        hero_class=data.hero_class,
        card_ids=json.dumps(data.card_ids),
    )
    db.add(deck)
    await db.commit()
    await db.refresh(deck)
    return _to_out(deck)


@router.get("/{deck_id}", response_model=DeckOut)
async def get_deck(deck_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    deck = await db.get(Deck, deck_id)
    if deck is None or deck.user_id != user.id:
        raise HTTPException(status_code=404, detail="Deck not found")
    return _to_out(deck)


@router.put("/{deck_id}", response_model=DeckOut)
async def update_deck(deck_id: int, data: DeckIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    deck = await db.get(Deck, deck_id)
    if deck is None or deck.user_id != user.id:
        raise HTTPException(status_code=404, detail="Deck not found")
    errors = validate_deck(data.hero_class, data.card_ids)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    deck.name = data.name
    deck.hero_class = data.hero_class
    deck.card_ids = json.dumps(data.card_ids)
    await db.commit()
    await db.refresh(deck)
    return _to_out(deck)


@router.delete("/{deck_id}", status_code=204)
async def delete_deck(deck_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    deck = await db.get(Deck, deck_id)
    if deck is None or deck.user_id != user.id:
        raise HTTPException(status_code=404, detail="Deck not found")
    await db.delete(deck)
    await db.commit()
