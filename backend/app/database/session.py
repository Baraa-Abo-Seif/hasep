import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from backend.app.core.config import settings

# Determine database URL and connect args
db_url = settings.DATABASE_URL
connect_args = {}
if "sqlite" in db_url:
    connect_args = {"check_same_thread": False}
    # Ensure storage directory exists for sqlite file
    if "./storage" in db_url or "storage/" in db_url:
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)

engine = create_async_engine(
    db_url,
    echo=(settings.APP_ENV == "development" and settings.LOG_LEVEL == "DEBUG"),
    connect_args=connect_args,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for yielding database session with automatic transaction management."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables for testing or local development."""
    import backend.app.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
