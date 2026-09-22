import asyncio
import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = None
AsyncSessionLocal = None


def _build_engine(db_url: str | None):
    if not db_url or db_url.startswith("******"):
        db_url = "sqlite+aiosqlite:///./echoguard.db"

    try:
        return create_async_engine(
            db_url,
            echo=False,
        )
    except Exception as exc:
        logger.warning(
            "Could not configure database engine: %s",
            exc,
        )
        return None


db_url = getattr(settings, "DATABASE_URL", None)
engine = _build_engine(db_url)

if engine is not None:
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def _initialize_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if conn.dialect.name == "postgresql":
            await conn.execute(
                text(
                    "ALTER TABLE risk_events "
                    "ALTER COLUMN speaker_similarity DROP NOT NULL"
                )
            )


async def init_db() -> None:
    """Create database tables if they do not already exist."""
    if engine is None:
        raise RuntimeError(
            "Database engine is not configured; startup schema creation cannot continue."
        )

    # Import models so SQLAlchemy knows about all tables.
    from app.db.models import (
        User,
        Contact,
        CallSession,
        RiskEvent,
        SpeakerProfile,
    )

    try:
        await asyncio.wait_for(
            _initialize_schema(),
            timeout=30.0,
        )
    except Exception as exc:
        logger.exception("Database startup schema creation failed.")
        raise RuntimeError(
            "Database startup schema creation failed."
        ) from exc

    logger.info("Database tables initialized successfully.")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    global engine, AsyncSessionLocal

    if AsyncSessionLocal is None:
        engine = _build_engine(getattr(settings, "DATABASE_URL", None))
        if engine is None:
            raise RuntimeError("Database engine is not configured.")
        AsyncSessionLocal = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async with AsyncSessionLocal() as session:
        yield session