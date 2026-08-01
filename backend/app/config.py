import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DEEPCHARD_DB_URL", "sqlite+aiosqlite:///./deepcards.db")
    jwt_secret: str = os.getenv("DEEPCHARD_SECRET", "dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    cards_json_path: str = os.getenv("CARDS_JSON_PATH", "cards.json")
    admin_username: str = os.getenv("DEEPCHARD_ADMIN_USER", "")
    admin_password: str = os.getenv("DEEPCHARD_ADMIN_PASS", "")


settings = Settings()
