"""
Ilova konfiguratsiyasi.

Barcha sozlamalar environment variable'lardan o'qiladi (12-factor app
tamoyiliga mos). Hech qachon secret'larni kodga yozmang.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Ilova ---
    APP_NAME: str = "QueueManagerBot"
    APP_ENV: str = Field(default="development")  # development | staging | production
    DEBUG: bool = Field(default=True)
    APP_TIMEZONE: str = "Asia/Tashkent"
    EMBEDDED_SCHEDULER_ENABLED: bool = Field(default=True)

    # --- Database ---
    # --- Database ---
    POSTGRES_USER: str = "postgres"  # qmb_user edi -> postgres qildik
    POSTGRES_PASSWORD: str = "0980"  # qmb_pass edi -> 0980 qildik
    POSTGRES_DB: str = "queue_manager_bot"  # qmb_db edi -> queue_manager_bot qildik
    POSTGRES_HOST: str = "localhost"  # postgres edi -> localhost qildik
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- Redis ---
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # --- JWT ---
    JWT_SECRET_KEY: str = Field(default="CHANGE_ME_IN_PRODUCTION")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # --- Telegram ---
    BOT_TOKEN: str = Field(default="")
    TELEGRAM_WEBHOOK_SECRET: str = Field(default="change_me")
    BOT_INTERNAL_SECRET: str = Field(default="CHANGE_ME_IN_PRODUCTION")
    """Bot <-> Backend orasidagi ichki so'rovlarni himoya qilish uchun umumiy maxfiy kalit."""

    SUPER_ADMIN_TELEGRAM_IDS: str = Field(default="")
    """Vergul bilan ajratilgan Telegram ID'lar ro'yxati - Bot Owner (Super Admin) sifatida belgilanadi."""

    @property
    def super_admin_ids(self) -> set[int]:
        return {
            int(raw.strip())
            for raw in self.SUPER_ADMIN_TELEGRAM_IDS.split(",")
            if raw.strip().isdigit()
        }

    # --- Fayl saqlash ---
    PHOTOS_STORAGE_PATH: str = str((Path(__file__).resolve().parents[3] / "storage" / "photos"))
    MAX_PHOTO_SIZE_MB: int = 10

    # --- Til ---
    DEFAULT_LANGUAGE: str = "uz"
    SUPPORTED_LANGUAGES: list[str] = ["uz", "en", "ru"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
