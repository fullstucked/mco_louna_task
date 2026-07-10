from fast_depends import Depends
from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession

from payments.infrastructure.database.session import async_session_factory
from payments.infrastructure.database.uow import PaymentsUoWSQLAlchemy


async def get_session():
    async with async_session_factory() as session:
        yield session


SessionDep = Annotated[
    AsyncSession,
    Depends(get_session),
]


def get_uow(
    session: SessionDep,
):
    return PaymentsUoWSQLAlchemy(session)


UowDep = Annotated[
    PaymentsUoWSQLAlchemy,
    Depends(get_uow),
]
