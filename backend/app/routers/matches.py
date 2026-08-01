from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user
from ..models import Match, User

router = APIRouter(prefix="/api/matches", tags=["matches"])


@router.get("")
async def list_matches(user: User = Depends(get_current_user),
                       db: AsyncSession = Depends(get_session)):
    rows = (
        await db.execute(
            select(Match)
            .where((Match.player1_id == user.id) | (Match.player2_id == user.id))
            .order_by(Match.started_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return rows
