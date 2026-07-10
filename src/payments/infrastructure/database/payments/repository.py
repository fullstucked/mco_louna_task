from typing import Optional

from sqlalchemy import RowMapping, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus
from payments.domain.payment import Payment
from payments.domain.repository import PaymentRepository
from payments.domain.value_objects.amount import Amount
from payments.domain.value_objects.description import Description
from payments.domain.value_objects.id import PaymentID
from payments.domain.value_objects.key import IdempotencyKey
from payments.domain.value_objects.metadata import Metadata
from payments.domain.value_objects.timestamp import Timestamp
from payments.domain.value_objects.webhook import WebhookUrl
from payments.infrastructure.database.payments.table import payments
from shared.domain.errors import DomainResourceNotFoundError


class SqlAlchemyPaymentRepository(PaymentRepository):
    """
    PostgreSQL implementation of repo
    to change DB replace insert postgres dialect with complimentary one
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, payment: Payment) -> None:
        """
        Saves payment aggregate with idempotency via ON CONFLICT DO NOTHING.
        Multiple inserts with same idempotency_key are silently ignored.
        """
        stmt = (
            pg_insert(payments)
            .values(
                id=payment.id.value,
                amount=payment.amount.value,
                currency=payment.currency.value,
                description=payment.description.value,
                metadata=payment.metadata.value,
                status=payment.status.value,
                idempotency_key=payment.key.value,
                created_at=payment.created_at.value,
                webhook_url=payment.webhook_url.value,
            )
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def update(self, payment: Payment) -> None:
        """
        Updates payment status and timestamp when processed.
        Raises DomainResourceNotFoundError if payment no longer exists.
        """
        stmt = (
            update(payments)
            .where(payments.c.id == payment.id.value)
            .values(
                status=payment.status.value,
                # pyrefly: ignore [missing-attribute]
                processed_at=payment.processed_at.value,
            )
            .returning(payments.c.id)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()

        if result.scalar_one_or_none() == 0:
            raise DomainResourceNotFoundError(
                f"Cannot update: Payment {payment.id.value} not found"
            )

    async def get_by_id(self, payment_id: PaymentID) -> Payment:
        """
        Fetch payment by ID with pessimistic lock.
        skip_locked=True prevents waiting if row is already locked.
        """
        stmt = (
            select(payments)
            .where(payments.c.id == payment_id.value)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        row = result.mappings().first()

        if not row:
            raise DomainResourceNotFoundError(f"Payment not found: {payment_id.value}")

        return self._to_domain(row)

    async def get_by_key(self, key: IdempotencyKey) -> Optional[Payment]:
        """
        Fetch payment by idempotency key with pessimistic lock.
        Returns None if key not found (idempotent retrieval).
        """
        stmt = (
            select(payments)
            .where(payments.c.idempotency_key == key.value)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        row = result.mappings().first()

        return self._to_domain(row) if row else None

    def _to_domain(self, row: RowMapping) -> Payment:
        """
        Map database row to Payment aggregate.
        Uses .rebuild() on value objects to skip validation (data already validated).
        """
        return Payment.rebuild(
            id=PaymentID.rebuild(row["id"]),
            amount=Amount.rebuild(row["amount"]),
            currency=Currency(row["currency"]),
            description=Description.rebuild(row["description"]),
            metadata=Metadata.rebuild(row["metadata"]),
            status=PaymentStatus(row["status"]),
            key=IdempotencyKey.rebuild(row["idempotency_key"]),
            webhook_url=WebhookUrl.rebuild(row["webhook_url"]),
            created_at=Timestamp.rebuild(row["created_at"]),
            processed_at=(
                Timestamp.rebuild(row["processed_at"]) if row["processed_at"] else None
            ),
        )
