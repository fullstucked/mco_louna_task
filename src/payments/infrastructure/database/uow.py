from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession

from payments.application.interfaces.uow import (
    PaymentUoW,
    RepositoriesExhaustedError,
    RepositoriesUnavailableError,
)
from payments.infrastructure.database.outbox.repository import (
    SqlAlchemyOutboxRepository,
)
from payments.infrastructure.database.payments.repository import (
    SqlAlchemyPaymentRepository,
)


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
        """
        Commit transaction with connection error mapping.

        Raises:
            RepositoryDatabaseUnavailableError
                On OperationalError (connection lost, database unavailable).
            RepositoryConnectionPoolExhaustedError
                On TimeoutError (all connections occupied).
        """
        try:
            await self.session.commit()
        except SQLTimeoutError as e:
            await self.session.rollback()
            raise RepositoriesExhaustedError(
                "Connection pool exhausted; unable to acquire connection within timeout"
            ) from e
        except OperationalError as e:
            await self.session.rollback()
            raise RepositoriesUnavailableError(f"Database unavailable: {str(e)}") from e

    async def rollback(self) -> None:
        """Rollback transaction. Swallows errors to prevent masking original failure."""
        try:
            await self.session.rollback()
        except Exception:
            pass
