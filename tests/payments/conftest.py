import os
from dotenv import load_dotenv

load_dotenv(".env.test")

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock


@pytest.fixture
async def db_session() -> AsyncSession:
    """Provide AsyncSession for repository tests."""
    session = AsyncMock(spec=AsyncSession)
    return session
