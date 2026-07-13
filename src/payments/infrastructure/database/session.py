import os
from typing import cast

from sqlalchemy import MetaData, QueuePool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

metadata = MetaData()

engine = create_async_engine(
    url=cast(str, os.getenv("DATABASE_URL")),
    echo=False,
    future=True,
    poolclass=QueuePool,
    pool_size=10,  # Base connections
    max_overflow=20,  # Max overflow beyond pool_size
    pool_timeout=30,  # Seconds to wait for available connection
    pool_recycle=3600,  # Recycle connections after 1hr (server timeout)
    pool_pre_ping=True,  # Test connection before reuse
)

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    class_=AsyncSession,
)
