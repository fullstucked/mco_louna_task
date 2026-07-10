import os
from typing import cast

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

metadata = MetaData()

engine = create_async_engine(
    url=cast(str, os.getenv("DATABASE_URL")),
    echo=False,
    future=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    class_=AsyncSession,
)
