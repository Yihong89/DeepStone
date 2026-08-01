from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import require_admin
from ..models import User
from ..routers.auth import hash_password

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_session)):
    users = (await db.execute(select(User).order_by(User.id))).scalars().all()
    return users


@router.patch("/users/{user_id}")
async def set_active(user_id: int, body: dict, db: AsyncSession = Depends(get_session)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = bool(body["is_active"])
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password")
async def reset_password(user_id: int, body: dict, db: AsyncSession = Depends(get_session)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = hash_password(body["new_password"])
    await db.commit()
    return {"status": "ok"}
