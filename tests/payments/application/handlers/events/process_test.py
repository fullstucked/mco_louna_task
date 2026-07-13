from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from payments.application.handlers.events.process import ProcessPayment
from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus
from payments.domain.events import PaymentCreatedEvent
from payments.domain.payment import Payment
from payments.domain.value_objects.amount import Amount
from payments.domain.value_objects.description import Description
from payments.domain.value_objects.id import PaymentID
from payments.domain.value_objects.key import IdempotencyKey
from payments.domain.value_objects.metadata import Metadata
from payments.domain.value_objects.timestamp import Timestamp
from payments.domain.value_objects.webhook import WebhookUrl


@pytest.fixture
def mock_uow():
    """Fixture for mocked Unit of Work."""
    mock_uow = AsyncMock()
    mock_uow.__aenter__.return_value = mock_uow
    mock_uow.__aexit__.return_value = None
    mock_uow.payments = AsyncMock()
    mock_uow.outbox = AsyncMock()
    mock_uow.commit = AsyncMock()
    return mock_uow


@pytest.fixture
def mock_event_bus():
    """Fixture for mocked Event Bus."""
    return AsyncMock()


@pytest.fixture
def sample_payment():
    """Fixture for a real Payment aggregate in PENDING status."""
    payment_id = uuid4()
    return Payment.rebuild(
        id=PaymentID.rebuild(payment_id),
        amount=Amount.rebuild(Decimal("100")),
        currency=Currency.USD,
        description=Description.rebuild("Test Payment"),
        metadata=Metadata.rebuild({"order_id": "12345"}),
        status=PaymentStatus.PENDING,
        key=IdempotencyKey.rebuild(uuid4()),
        webhook_url=WebhookUrl.rebuild("https://example.com/webhook"),
        created_at=Timestamp.rebuild(datetime.now()),
        processed_at=None,
    )


class TestProcessPaymentUseCase:
    """Tests for ProcessPayment use case."""

    @pytest.mark.asyncio
    @patch("payments.application.handlers.events.process.random", return_value=0.5)
    @patch("payments.application.handlers.events.process.uniform", return_value=0)
    async def test_process_payment_success(
        self, mock_uniform, mock_random, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should mark payment as CONFIRMED and publish events on success."""
        payment_id = sample_payment.id.value
        mock_uow.payments.get_by_id = AsyncMock(return_value=sample_payment)

        event = PaymentCreatedEvent(payment_id=payment_id)
        use_case = ProcessPayment()
        await use_case(event=event, uow=mock_uow, event_bus=mock_event_bus)

        # Assert payment state changed
        assert sample_payment.status == PaymentStatus.CONFIRMED
        assert sample_payment.processed_at is not None

        # Assert outbox and publish were called
        mock_uow.outbox.add.assert_awaited_once()
        mock_uow.commit.assert_awaited_once()
        mock_event_bus.publish_payment_events.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("payments.application.handlers.events.process.random", return_value=0.95)
    @patch("payments.application.handlers.events.process.uniform", return_value=0)
    async def test_process_payment_failure(
        self, mock_uniform, mock_random, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should mark payment as FAILED when processing fails."""
        payment_id = sample_payment.id.value
        mock_uow.payments.get_by_id = AsyncMock(return_value=sample_payment)

        event = PaymentCreatedEvent(payment_id=payment_id)
        use_case = ProcessPayment()
        await use_case(event=event, uow=mock_uow, event_bus=mock_event_bus)

        # Assert payment state changed to failed
        assert sample_payment.status == PaymentStatus.FAILED
        assert sample_payment.processed_at is not None

        # Assert outbox and publish were called
        mock_uow.outbox.add.assert_awaited_once()
        mock_uow.commit.assert_awaited_once()
        mock_event_bus.publish_payment_events.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("payments.application.handlers.events.process.random", return_value=0.5)
    @patch("payments.application.handlers.events.process.uniform", return_value=0)
    async def test_process_payment_workflow_order(
        self, mock_uniform, mock_random, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should execute workflow in correct order: emulate → outbox → commit → publish."""
        call_order = []

        async def track_outbox_add(*args, **kwargs):
            call_order.append("outbox_add")

        async def track_commit(*args, **kwargs):
            call_order.append("commit")

        async def track_publish(*args, **kwargs):
            call_order.append("publish_payment_events")

        # Inject tracking into mock methods
        mock_uow.outbox.add.side_effect = track_outbox_add
        mock_uow.commit.side_effect = track_commit
        mock_event_bus.publish_payment_events.side_effect = track_publish
        mock_uow.payments.get_by_id = AsyncMock(return_value=sample_payment)

        event = PaymentCreatedEvent(payment_id=sample_payment.id.value)
        use_case = ProcessPayment()
        await use_case(event=event, uow=mock_uow, event_bus=mock_event_bus)

        # Verify workflow steps executed
        mock_uow.outbox.add.assert_awaited_once()
        mock_uow.commit.assert_awaited_once()
        mock_event_bus.publish_payment_events.assert_awaited_once()

        # Verify order: outbox.add → commit → publish
        assert call_order == [
            "outbox_add",
            "commit",
            "publish_payment_events",
        ], f"Expected order [outbox_add, commit, publish], but got {call_order}"

    @pytest.mark.asyncio
    @patch("payments.application.handlers.events.process.random", return_value=0.5)
    @patch("payments.application.handlers.events.process.uniform", return_value=0)
    async def test_process_payment_events_content(
        self, mock_uniform, mock_random, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should emit events with correct payload."""
        payment_id = sample_payment.id.value
        mock_uow.payments.get_by_id = AsyncMock(return_value=sample_payment)

        event = PaymentCreatedEvent(payment_id=payment_id)
        use_case = ProcessPayment()
        await use_case(event=event, uow=mock_uow, event_bus=mock_event_bus)

        # Verify events content
        published_events = mock_event_bus.publish_payment_events.call_args[0][0]
        assert len(published_events) >= 1

        # Check that at least one event is a PaymentStatusChangedEvent or similar
        event_types = [type(e).__name__ for e in published_events]
        assert any(
            "Payment" in event_type for event_type in event_types
        ), f"Expected payment events, got {event_types}"

    @pytest.mark.asyncio
    @patch("payments.application.handlers.events.process.random", return_value=0.5)
    @patch("payments.application.handlers.events.process.uniform", return_value=0)
    async def test_process_payment_outbox_integration(
        self, mock_uniform, mock_random, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should add events to outbox before commit."""
        payment_id = sample_payment.id.value
        mock_uow.payments.get_by_id = AsyncMock(return_value=sample_payment)

        event = PaymentCreatedEvent(payment_id=payment_id)
        use_case = ProcessPayment()
        await use_case(event=event, uow=mock_uow, event_bus=mock_event_bus)

        # Verify outbox.add was called with events
        outbox_add_call_args = mock_uow.outbox.add.call_args[0][0]
        assert len(outbox_add_call_args) >= 1, "Expected at least one event in outbox"

    @pytest.mark.asyncio
    @patch("payments.application.handlers.events.process.random", return_value=0.5)
    @patch("payments.application.handlers.events.process.uniform", return_value=0)
    async def test_process_payment_outbox_add_failure(
        self, mock_uniform, mock_random, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should not commit or publish if outbox.add fails."""
        mock_uow.outbox.add.side_effect = Exception("Database error")
        mock_uow.payments.get_by_id = AsyncMock(return_value=sample_payment)

        event = PaymentCreatedEvent(payment_id=sample_payment.id.value)
        use_case = ProcessPayment()

        with pytest.raises(Exception, match="Database error"):
            await use_case(event=event, uow=mock_uow, event_bus=mock_event_bus)

        # Verify commit and publish were NOT called
        mock_uow.commit.assert_not_awaited()
        mock_event_bus.publish_payment_events.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("payments.application.handlers.events.process.random", return_value=0.5)
    @patch("payments.application.handlers.events.process.uniform", return_value=0)
    async def test_process_payment_commit_failure(
        self, mock_uniform, mock_random, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should not publish events if commit fails."""
        mock_uow.commit.side_effect = Exception("Transaction failed")
        mock_uow.payments.get_by_id = AsyncMock(return_value=sample_payment)

        event = PaymentCreatedEvent(payment_id=sample_payment.id.value)
        use_case = ProcessPayment()

        with pytest.raises(Exception, match="Transaction failed"):
            await use_case(event=event, uow=mock_uow, event_bus=mock_event_bus)

        # Verify events were NOT published after failed commit
        mock_event_bus.publish_payment_events.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("payments.application.handlers.events.process.random", return_value=0.5)
    @patch("payments.application.handlers.events.process.uniform", return_value=0)
    async def test_process_payment_publish_failure_after_commit(
        self, mock_uniform, mock_random, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should raise exception if event publishing fails after commit."""
        mock_event_bus.publish_payment_events.side_effect = Exception(
            "Event bus unavailable"
        )
        mock_uow.payments.get_by_id = AsyncMock(return_value=sample_payment)

        event = PaymentCreatedEvent(payment_id=sample_payment.id.value)
        use_case = ProcessPayment()

        # Transaction was committed, but publishing failed
        # This is a critical state that needs to be handled
        with pytest.raises(Exception, match="Event bus unavailable"):
            await use_case(event=event, uow=mock_uow, event_bus=mock_event_bus)

        # Verify commit was called (transaction was persisted)
        mock_uow.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("payments.application.handlers.events.process.random", return_value=0.5)
    @patch("payments.application.handlers.events.process.uniform", return_value=0)
    async def test_process_payment_payment_not_found(
        self, mock_uniform, mock_random, mock_uow, mock_event_bus
    ):
        """UseCase should handle gracefully when payment is not found."""
        payment_id = uuid4()
        mock_uow.payments.get_by_id = AsyncMock(return_value=None)

        event = PaymentCreatedEvent(payment_id=payment_id)
        use_case = ProcessPayment()

        # This should raise an error or handle gracefully
        with pytest.raises((ValueError, AttributeError)):
            await use_case(event=event, uow=mock_uow, event_bus=mock_event_bus)

        # Verify no state changes occurred
        mock_uow.commit.assert_not_awaited()
        mock_event_bus.publish_payment_events.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("payments.application.handlers.events.process.random", return_value=0.89)
    @patch("payments.application.handlers.events.process.uniform", return_value=0)
    async def test_process_payment_boundary_success_threshold(
        self, mock_uniform, mock_random, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should mark payment as CONFIRMED when random < 0.9 (boundary test)."""
        mock_uow.payments.get_by_id = AsyncMock(return_value=sample_payment)

        event = PaymentCreatedEvent(payment_id=sample_payment.id.value)
        use_case = ProcessPayment()
        await use_case(event=event, uow=mock_uow, event_bus=mock_event_bus)

        # 0.89 < 0.9, so should succeed
        assert sample_payment.status == PaymentStatus.CONFIRMED

    @pytest.mark.asyncio
    @patch("payments.application.handlers.events.process.random", return_value=0.90)
    @patch("payments.application.handlers.events.process.uniform", return_value=0)
    async def test_process_payment_boundary_failure_threshold(
        self, mock_uniform, mock_random, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should mark payment as FAILED when random >= 0.9 (boundary test)."""
        mock_uow.payments.get_by_id = AsyncMock(return_value=sample_payment)

        event = PaymentCreatedEvent(payment_id=sample_payment.id.value)
        use_case = ProcessPayment()
        await use_case(event=event, uow=mock_uow, event_bus=mock_event_bus)

        # 0.90 >= 0.9, so should fail
        assert sample_payment.status == PaymentStatus.FAILED
