"""
Database connection management.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession, 
    async_sessionmaker
)
from sqlalchemy.pool import NullPool

from app.config.settings import settings
from app.database.models import Base

# Initialize logger
logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,  # settings.database_echo if needed
    pool_size=10,  # Reduced pool size to prevent connection exhaustion
    max_overflow=20,  # Reduced max overflow
    pool_pre_ping=True,  # Enable connection health checks
    pool_recycle=3600,  # Recycle connections every hour
    poolclass=NullPool if "sqlite" in settings.database_url else None,
)

# Create session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_database() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    """Close database connections."""
    await engine.dispose()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session with improved error handling for concurrent operations.
    
    Usage:
        async with get_db_session() as session:
            # Use session here
            pass
    """
    session = None
    try:
        session = async_session_factory()
        yield session
        await session.commit()
    except Exception as e:
        if session:
            await session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        if session:
            await session.close()


class DatabaseManager:
    """Database manager for dependency injection."""
    
    def __init__(self):
        self.engine = engine
        self.session_factory = async_session_factory
    
    async def get_session(self) -> AsyncSession:
        """Get database session."""
        return self.session_factory()
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager for database session."""
        async with get_db_session() as session:
            yield session
    
    async def init_db(self) -> None:
        """Initialize database."""
        await init_database()
    
    async def close(self) -> None:
        """Close database connections."""
        await close_database()


# Global database manager instance
db_manager = DatabaseManager() 