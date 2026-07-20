"""
Async SQLAlchemy engine va session factory.

Repository Layer shu yerdan session oladi (Dependency Injection orqali),
hech qachon to'g'ridan-to'g'ri global session ishlatilmaydi.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from ...core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={"server_settings": {"timezone": settings.APP_TIMEZONE}},
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Barcha ORM modellari uchun asos klass."""

    pass


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: har bir request uchun alohida session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
