"""
Ilova konfiguratsiyasi.

Barcha sozlamalar environment variable'lardan o'qiladi (12-factor app
tamoyiliga mos). Hech qachon secret'larni kodga yozmang.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Ilova ---
    APP_NAME: str = "QueueManagerBot"
    # development | testing | staging | production
    # Fail-closed: "production" ni default qilamiz, chunki "development" qiymati
    # auth_deps.py/telegram_auth.py'da barcha JWT/HMAC tekshiruvlarini chetlab
    # o'tadi. APP_ENV o'zgaruvchisi deploy konfiguratsiyasida yo'qolib qolsa ham
    # ilova xavfsiz (yopiq) holatda ishga tushishi kerak.
    APP_ENV: str = Field(default="production")
    DEBUG: bool = Field(default=False)
    APP_TIMEZONE: str = "Asia/Tashkent"
    EMBEDDED_SCHEDULER_ENABLED: bool = Field(default=True)

    # --- CORS ---
    # Vergul bilan ajratilgan ruxsat etilgan origin'lar ro'yxati (masalan,
    # "https://miniapp.example.com,https://admin.example.com"). DEBUG bilan
    # bog'liq emas - CORS har doim shu ro'yxat orqali boshqariladi, aks holda
    # DEBUG=false bo'lganda ham xatolik bilan production Mini App uzilib qolishi mumkin.
    ALLOWED_ORIGINS: str = Field(default="")

    @property
    def cors_origins(self) -> list[str]:
        if self.DEBUG and not self.ALLOWED_ORIGINS:
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

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

    @model_validator(mode="after")
    def _fail_fast_on_insecure_production_defaults(self) -> "Settings":
        """
        APP_ENV=production bo'lganda ilova hech qachon placeholder maxfiy
        kalitlar (masalan, "CHANGE_ME_IN_PRODUCTION") bilan ishga tushmasligi
        kerak - bu qiymatlar ochiq kodda ko'rinib turibdi, shuning uchun
        ularni o'zgartirmasdan production'ga chiqarish token/JWT'ni har kimga
        soxtalashtirish imkonini beradi.
        """
        if self.APP_ENV != "production":
            return self

        insecure_fields = []
        if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY == "CHANGE_ME_IN_PRODUCTION":
            insecure_fields.append("JWT_SECRET_KEY")
        if not self.BOT_INTERNAL_SECRET or self.BOT_INTERNAL_SECRET == "CHANGE_ME_IN_PRODUCTION":
            insecure_fields.append("BOT_INTERNAL_SECRET")
        if not self.BOT_TOKEN:
            insecure_fields.append("BOT_TOKEN")

        if insecure_fields:
            raise ValueError(
                "APP_ENV=production bo'lganda quyidagi maxfiy sozlamalar hali ham "
                f"bo'sh/standart (placeholder) qiymatda: {', '.join(insecure_fields)}. "
                ".env faylida ularni haqiqiy, tasodifiy qiymatlar bilan to'ldiring "
                "(yoki lokal ishlash uchun APP_ENV=development/testing qiling)."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
