"""
Alembic muhit sozlamalari.

Bizning engine async (asyncpg) bo'lgani uchun, migratsiyalarni
`asyncio.run` orqali sync context'ga o'rab bajaramiz - bu SQLAlchemy 2.x
rasmiy tavsiya qilingan usuli.
"""
import os
import sys

# `env.py`dan BIR daraja yuqoridagi papkani sys.path-ga qo'shadi - lokalda
# bu `backend/` (repo ildizi ichidagi), Docker konteynerida esa `/app`
# (chunki docker-compose "./backend:/app" qilib bog'laydi - konteyner
# ichida "backend" nomli qo'shimcha papka UMUMAN YO'Q, `/app` o'zi aynan
# shu papkaning ichi). Ikkala holatda ham `src/` shu papkaning ichida
# joylashgan. ILGARI ikki daraja yuqoriga chiqilardi ("..", ".." - repo
# ildizi) va `backend.src...` ko'rinishida import qilinardi - bu lokalda
# ishlardi, lekin Docker ichida ikki daraja yuqoriga chiqish fayl tizimi
# "/" ga olib borardi va `ModuleNotFoundError: No module named 'backend'`
# bilan yiqilardi (`docker compose exec backend alembic upgrade head`
# doim shu xato bilan to'xtardi).
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# --- Loyiha modellari va sozlamalarini import qilamiz ---
from src.core.config import settings
from src.infrastructure.db.session import Base
from src.infrastructure.models import *  # noqa: F401,F403 - Base.metadata to'ldirish uchun

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
