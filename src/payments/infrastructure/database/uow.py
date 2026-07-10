from payments.infrastructure.database.payments.repository import (
    SqlAlchemyPaymentRepository,
)
from payments.infrastructure.database.outbox.repository import (
    SqlAlchemyOutboxRepository,
)
from sqlalchemy.ext.asyncio import AsyncSession
from payments.application.interfaces.uow import PaymentUoW


class PaymentsUoWSQLAlchemy(PaymentUoW):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        self.payments = SqlAlchemyPaymentRepository(self.session)
        self.outbox = SqlAlchemyOutboxRepository(self.session)

        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session is None:
            return
        try:
            if exc:
                await self.rollback()
        finally:
            await self.session.close()

    async def commit(self) -> None:
        if not self.session:
            raise RuntimeError("Session not initialized")
        await self.session.commit()

    async def rollback(self) -> None:
        if not self.session:
            raise RuntimeError("Session not initialized")
        await self.session.rollback()
