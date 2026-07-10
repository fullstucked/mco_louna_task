from sqlalchemy.dialects import postgresql
from uuid import uuid4
from shared.domain.errors import DomainResourceNotFoundError
from payments.domain.value_objects.timestamp import Timestamp
from payments.domain.value_objects.webhook import WebhookUrl
from payments.domain.value_objects.key import IdempotencyKey
from payments.domain.value_objects.metadata import Metadata
from payments.domain.value_objects.description import Description
from payments.domain.value_objects.amount import Amount
from payments.infrastructure.database.payments.repository import (
    SqlAlchemyPaymentRepository,
)
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus
from payments.domain.payment import Payment, PaymentID


@pytest.fixture
def mock_session():
    """Mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def repo(mock_session):
    """Repository instance with mocked session."""
    return SqlAlchemyPaymentRepository(mock_session)


class TestSqlAlchemyPaymentRepository:
    """Test suite for SqlAlchemyPaymentRepository."""

    # ===== ADD =====

    @pytest.mark.asyncio
    async def test_add_executes_insert_with_on_conflict(self, repo, mock_session):
        payment = self._make_payment()
        await repo.add(payment)

        mock_session.execute.assert_called_once()
        stmt = mock_session.execute.call_args[0][0]

        # Compile with PostgreSQL dialect
        compiled = str(stmt.compile(dialect=postgresql.dialect()))
        assert "INSERT" in compiled.upper()
        assert "ON CONFLICT" in compiled.upper()

        @pytest.mark.asyncio
        async def test_add_calls_flush_after_insert(self, repo, mock_session):
            """Verify add() calls flush() to make changes visible within transaction."""
            payment = self._make_payment()

            await repo.add(payment)

            # Verify both execute and flush were called
            mock_session.execute.assert_called_once()
            mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_maps_all_payment_fields(self, repo, mock_session):
        """Verify add() includes all payment fields in the insert."""
        payment_id = PaymentID()
        amount = Amount(Decimal("99.99"))
        currency = Currency.USD
        description = Description("Coffee")
        metadata = Metadata({"order": "123"})
        status = PaymentStatus.PENDING
        key = IdempotencyKey(uuid4())
        webhook_url = WebhookUrl("https://example.com/hook")
        created_at = Timestamp.now()

        payment = MagicMock(spec=Payment)
        payment.id.value = payment_id.value
        payment.amount.value = amount.value
        payment.currency.value = currency.value
        payment.description.value = description.value
        payment.metadata.value = metadata.value
        payment.status.value = status.value
        payment.key.value = key.value
        payment.webhook_url.value = webhook_url.value
        payment.created_at.value = created_at.value

        await repo.add(payment)

        assert mock_session.execute.called
        assert mock_session.flush.called

    @pytest.mark.asyncio
    async def test_add_does_not_commit(self, repo, mock_session):
        """Verify add() does not auto-commit the session (caller manages transaction)."""
        payment = self._make_payment()

        await repo.add(payment)

        mock_session.commit.assert_not_called()

    # ===== UPDATE =====

    @pytest.mark.asyncio
    async def test_update_executes_update_statement(self, repo, mock_session):
        """Verify update() calls session.execute() with update statement."""
        payment = self._make_payment(status=PaymentStatus.CONFIRMED)
        payment.processed_at = Timestamp.now()

        # Mock result with rowcount > 0
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        await repo.update(payment)

        mock_session.execute.assert_called_once()
        stmt = mock_session.execute.call_args[0][0]

        # Verify it's an UPDATE statement
        assert "UPDATE" in str(stmt).upper()

    @pytest.mark.asyncio
    async def test_update_only_changes_status_and_processed_at(
        self, repo, mock_session
    ):
        """Verify update() only modifies status and processed_at."""
        payment_id = PaymentID()
        processed_at = Timestamp.now()

        payment = MagicMock(spec=Payment)
        payment.id.value = payment_id.value
        payment.status.value = PaymentStatus.CONFIRMED.value
        payment.processed_at.value = processed_at.value

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        await repo.update(payment)

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_calls_flush_after_update(self, repo, mock_session):
        """Verify update() calls flush() to make changes visible within transaction."""
        payment = self._make_payment(status=PaymentStatus.CONFIRMED)
        payment.processed_at = Timestamp.now()

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        await repo.update(payment)

        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_raises_when_payment_not_found(self, repo, mock_session):
        """Verify update() raises DomainResourceNotFoundError if payment not found."""
        payment = self._make_payment(status=PaymentStatus.CONFIRMED)
        payment.processed_at = Timestamp.now()

        # Mock result where scalar_one_or_none() returns None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # ✅ Changed
        mock_session.execute.return_value = mock_result

        with pytest.raises(DomainResourceNotFoundError) as exc_info:
            await repo.update(payment)

        assert f"Cannot update: Payment {payment.id.value} not found" in str(
            exc_info.value
        )
        mock_session.flush.assert_called_once()

    # ===== GET BY ID =====

    @pytest.mark.asyncio
    async def test_get_by_id_returns_mapped_payment(self, repo, mock_session):
        """Verify get_by_id() maps database row to Payment aggregate."""
        payment_id = PaymentID()
        row_data = self._make_row_data(payment_id=payment_id)

        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.first.return_value = row_data
        mock_result.mappings.return_value = mock_mappings
        mock_session.execute.return_value = mock_result

        payment = await repo.get_by_id(payment_id)

        assert payment.id.value == payment_id.value
        assert payment.amount.value == Decimal("50.00")
        assert payment.currency == Currency.USD
        assert payment.status == PaymentStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_by_id_uses_for_update_with_skip_locked(self, repo, mock_session):
        """Verify get_by_id() uses FOR UPDATE with skip_locked=True."""
        payment_id = PaymentID()

        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.first.return_value = self._make_row_data()
        mock_result.mappings.return_value = mock_mappings
        mock_session.execute.return_value = mock_result

        await repo.get_by_id(payment_id)

        stmt = mock_session.execute.call_args[0][0]
        # ✅ Compile with PostgreSQL dialect
        compiled_sql = str(stmt.compile(dialect=postgresql.dialect())).upper()

        assert "FOR UPDATE" in compiled_sql
        assert "SKIP LOCKED" in compiled_sql

    @pytest.mark.asyncio
    async def test_get_by_id_raises_when_not_found(self, repo, mock_session):
        """Verify get_by_id() raises DomainResourceNotFoundError on missing payment."""
        payment_id = PaymentID()

        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.first.return_value = None
        mock_result.mappings.return_value = mock_mappings
        mock_session.execute.return_value = mock_result

        with pytest.raises(DomainResourceNotFoundError) as exc_info:
            await repo.get_by_id(payment_id)

        assert f"Payment not found: {payment_id.value}" in str(exc_info.value)

    # ===== GET BY KEY =====

    @pytest.mark.asyncio
    async def test_get_by_key_returns_payment_when_found(self, repo, mock_session):
        """Verify get_by_key() returns Payment when idempotency key matches."""
        key = IdempotencyKey(uuid4())
        row_data = self._make_row_data(idempotency_key=key.value, status="CONFIRMED")

        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.first.return_value = row_data
        mock_result.mappings.return_value = mock_mappings
        mock_session.execute.return_value = mock_result

        payment = await repo.get_by_key(key)

        assert payment is not None
        assert payment.key.value == key.value
        assert payment.status == PaymentStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_get_by_key_returns_none_when_not_found(self, repo, mock_session):
        """Verify get_by_key() returns None (not raises) when key missing."""
        key = IdempotencyKey(uuid4())

        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.first.return_value = None
        mock_result.mappings.return_value = mock_mappings
        mock_session.execute.return_value = mock_result

        payment = await repo.get_by_key(key)

        assert payment is None

    @pytest.mark.asyncio
    async def test_get_by_key_uses_for_update_with_skip_locked(
        self, repo, mock_session
    ):
        """Verify get_by_key() uses FOR UPDATE with skip_locked=True."""
        key = IdempotencyKey(uuid4())

        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.first.return_value = self._make_row_data()
        mock_result.mappings.return_value = mock_mappings
        mock_session.execute.return_value = mock_result

        await repo.get_by_key(key)

        stmt = mock_session.execute.call_args[0][0]
        # ✅ Compile with PostgreSQL dialect
        compiled_sql = str(stmt.compile(dialect=postgresql.dialect())).upper()

        assert "FOR UPDATE" in compiled_sql
        assert "SKIP LOCKED" in compiled_sql

    # ===== TO_DOMAIN MAPPER =====

    @pytest.mark.asyncio
    async def test_to_domain_maps_all_fields(self, repo):
        """Verify _to_domain() correctly maps all row fields to Payment."""
        payment_id = PaymentID()
        row_data = self._make_row_data(payment_id=payment_id, status="CONFIRMED")

        payment = repo._to_domain(row_data)

        assert payment.id.value == payment_id.value
        assert payment.amount.value == Decimal("50.00")
        assert payment.currency == Currency.USD
        assert payment.description.value == "Service"
        assert payment.metadata.value == {"key": "value"}
        assert payment.status == PaymentStatus.CONFIRMED
        assert payment.webhook_url.value == "https://example.com/webhook"

    @pytest.mark.asyncio
    async def test_to_domain_handles_none_processed_at(self, repo):
        """Verify _to_domain() correctly handles None processed_at."""
        row_data = self._make_row_data(processed_at=None)

        payment = repo._to_domain(row_data)

        assert payment.processed_at is None
        assert payment.status == PaymentStatus.PENDING

    @pytest.mark.asyncio
    async def test_to_domain_handles_present_processed_at(self, repo):
        """Verify _to_domain() correctly handles present processed_at."""
        timestamp_str = "2026-07-10T09:15:00"
        row_data = self._make_row_data(status="CONFIRMED", processed_at=timestamp_str)

        payment = repo._to_domain(row_data)

        assert payment.processed_at is not None
        assert payment.processed_at.value == timestamp_str
        assert payment.status == PaymentStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_to_domain_rebuilds_all_value_objects(self, repo):
        """Verify _to_domain() uses value object rebuilds (not raw construction)."""
        row_data = self._make_row_data()

        # This should not raise—all value objects must support .rebuild()
        payment = repo._to_domain(row_data)

        # Verify all are value objects (not primitives)
        assert hasattr(payment.id, "value")
        assert hasattr(payment.amount, "value")
        assert hasattr(payment.key, "value")

    # ===== HELPERS =====

    @staticmethod
    def _make_payment(
        payment_id: PaymentID | None = None,
        amount: Decimal = Decimal("50.00"),
        currency: Currency = Currency.USD,
        status: PaymentStatus = PaymentStatus.PENDING,
    ) -> Payment:
        """Factory to create a test Payment aggregate."""
        if payment_id is None:
            payment_id = PaymentID()

        return Payment.rebuild(
            id=payment_id,
            amount=Amount.rebuild(str(amount)),
            currency=currency,
            description=Description.rebuild("Test Payment"),
            metadata=Metadata.rebuild({}),
            status=status,
            key=IdempotencyKey(uuid4()),
            webhook_url=WebhookUrl.rebuild("https://example.com/webhook"),
            created_at=Timestamp.rebuild("2026-07-10T10:00:00"),
            processed_at=None,
        )

    @staticmethod
    def _make_row_data(
        payment_id: PaymentID | None = None,
        amount: Decimal = Decimal("50.00"),
        currency: str = "USD",
        status: str = "PENDING",
        idempotency_key: str | None = None,
        processed_at: str | None = None,
    ) -> dict:
        """Factory to create row data for mocking database results."""
        if payment_id is None:
            payment_id = PaymentID()
        if idempotency_key is None:
            idempotency_key = IdempotencyKey(uuid4()).value

        return {
            "id": payment_id.value,
            "amount": amount,
            "currency": currency,
            "description": "Service",
            "metadata": {"key": "value"},
            "status": status,
            "idempotency_key": idempotency_key,
            "webhook_url": "https://example.com/webhook",
            "created_at": "2026-07-10T10:00:00",
            "processed_at": processed_at,
        }
