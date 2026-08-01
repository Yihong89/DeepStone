from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginIn(BaseModel):
    username: str
    password: str


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str

    model_config = {"from_attributes": True}


class DeckIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    hero_class: str
    card_ids: list[str]


class DeckOut(BaseModel):
    id: int
    user_id: int
    name: str
    hero_class: str
    card_ids: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
