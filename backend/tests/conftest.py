"""
Pytest umumiy fixture'lari.

Test uchun alohida PostgreSQL bazasi ishlatiladi (`qmb_test_db`).
Har bir test funksiyasi tugagach, jadvallar tozalanadi (transaction rollback).

DIQQAT: `engine` fixture funksiya darajasida (function-scoped), chunki
asyncpg ulanishlari muayyan event loop'ga bog'langan bo'ladi - pytest-asyncio
har bir testga yangi event loop yaratadi. Session-scoped engine ishlatilsa,
"another operation is in progress" xatosi chiqadi (loop mismatch).
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Loyiha ildizi: .../queue-manager-bot (conftest -> tests -> backend -> ildiz).
# Ilgari bu yerda `load_dotenv("../.env")` va `from backend.src...` importi
# bor edi - ikkalasi ham pytest qaysi papkadan chaqirilganiga bog'liq edi,
# shuning uchun `backend/` ichidan `pytest` ishlamas edi.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env.local", override=True)

# Testda auth chetlab o'tilmasin
os.environ["APP_ENV"] = "testing"
os.environ["DEV_AUTH_BYPASS"] = "false"

# MUHIM: `src.core.config.settings` import qilinishidan OLDIN environment
# o'zgaruvchilarini o'rnatamiz, aks holda production default'lar ishlatiladi.
# POSTGRES_* qiymatlari .env/.env.local dan keladi (yuqorida yuklandi), shuning
# uchun test bazasi ham ishchi baza bilan bir xil serverda bo'ladi. Faqat
# baza NOMI boshqacha - ishchi ma'lumotlar hech qachon o'chirilmasligi uchun.
os.environ["POSTGRES_DB"] = "qmb_test_db"
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_for_pytest")
os.environ.setdefault("BOT_TOKEN", "test_bot_token")
os.environ.setdefault("BOT_INTERNAL_SECRET", "test_internal_secret_for_pytest")
os.environ.setdefault("PHOTOS_STORAGE_PATH", "/tmp/test_photos_storage")

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.src.infrastructure.db.session import Base

db_user = os.environ.get("POSTGRES_USER", "postgres")
db_pass = os.environ.get("POSTGRES_PASSWORD", "")
db_host = os.environ.get("POSTGRES_HOST", "localhost")
db_port = os.environ.get("POSTGRES_PORT", "5432")
TEST_DATABASE_URL = f"postgresql+asyncpg://{db_user}:{db_pass}@{db_host}:{db_port}/qmb_test_db"
_ADMIN_DATABASE_URL = f"postgresql+asyncpg://{db_user}:{db_pass}@{db_host}:{db_port}/postgres"


async def _ensure_test_database() -> None:
    """`qmb_test_db` yo'q bo'lsa yaratadi - aks holda birinchi test
    "database does not exist" bilan yiqiladi va sababi tushunarsiz bo'ladi."""
    import asyncpg

    conn = await asyncpg.connect(
        user=db_user, password=db_pass, host=db_host, port=int(db_port), database="postgres"
    )
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", "qmb_test_db")
        if not exists:
            await conn.execute('CREATE DATABASE "qmb_test_db"')
    finally:
        await conn.close()


@pytest_asyncio.fixture
async def engine():
    """Har bir test o'z engine'ini oladi - shu testning event loop'iga bog'lanadi."""
    await _ensure_test_database()
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
        connect_args={"server_settings": {"timezone": "Asia/Tashkent"}},
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _patch_global_session_factory(engine, monkeypatch):
    """
    `main.py` ichidagi middleware va global exception handler o'z holicha
    (request-scoped Depends() dan tashqarida) global `async_session_factory`
    orqali DB'ga ulanadi - bu production'da bitta doimiy event loop bilan
    ishlagani uchun muammo emas. Lekin pytest-asyncio har testga YANGI event
    loop yaratadi, va o'sha global engine oldingi test'ning (endi yopilgan)
    loop'iga bog'langanicha qoladi - shu sabab "attached to a different loop"
    xatosi chiqadi. Shuning uchun har bir test uchun global session factory'ni
    shu testning O'Z engine'iga ko'rsatib qo'yamiz.
    """
    import backend.src.infrastructure.db.session as db_session_module

    test_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(db_session_module, "async_session_factory", test_factory)
    yield


@pytest_asyncio.fixture
async def session(engine) -> AsyncSession:
    """
    Har bir test o'z transaction'ida ishlaydi va test tugagach
    ROLLBACK qilinadi - shuning uchun testlar bir-biriga ta'sir qilmaydi.
    """
    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    test_session = session_factory()

    yield test_session

    await test_session.close()
    if transaction.is_active:
        await transaction.rollback()
    await connection.close()
