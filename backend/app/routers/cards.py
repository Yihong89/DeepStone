from fastapi import APIRouter, Query

from ..engine.carddata import load_cards

router = APIRouter(prefix="/api/cards", tags=["cards"])


@router.get("")
async def list_cards(
    q: str | None = Query(default=None),
    card_class: str | None = Query(default=None, alias="class"),
    cost: int | None = Query(default=None),
):
    cards = load_cards()
    if card_class:
        cards = [c for c in cards if c["cardClass"] == card_class]
    if cost is not None:
        cards = [c for c in cards if c.get("cost") == cost]
    if q:
        ql = q.lower()
        cards = [c for c in cards if ql in c["name"].lower() or ql in c["text"].lower()]
    return cards
