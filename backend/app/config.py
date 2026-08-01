import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DEEPSTONE_DB_URL", "sqlite+aiosqlite:///./deepstone.db")
    jwt_secret: str = os.getenv("DEEPSTONE_SECRET", "dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    cards_json_path: str = os.getenv("CARDS_JSON_PATH", "cards.json")
    admin_username: str = os.getenv("DEEPSTONE_ADMIN_USER", "")
    admin_password: str = os.getenv("DEEPSTONE_ADMIN_PASS", "")


settings = Settings()
