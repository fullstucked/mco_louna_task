from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from payments.application.handlers.commands.create import (
    CreatePaymentCommand,
    CreatePaymentResponse,
    CreatePaymentUseCase,
)
from payments.application.interfaces.event_publisher import PaymentEventBus
from payments.application.interfaces.uow import PaymentUoW
from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus
from payments.domain.events import PaymentCreatedEvent
from payments.domain.payment import Payment
from payments.domain.service import PaymentService
from payments.domain.value_objects.amount import Amount
from payments.domain.value_objects.description import Description
from payments.domain.value_objects.key import IdempotencyKey
from payments.domain.value_objects.metadata import Metadata
from payments.domain.value_objects.webhook import WebhookUrl
from shared.domain.errors import DomainResourceExistsError


@pytest.fixture
def mock_uow():
    """Fixture for mocked Unit of Work."""
    mock_uow = AsyncMock(spec=PaymentUoW)
    mock_uow.__aenter__.return_value = mock_uow
    mock_uow.__aexit__.return_value = None
    mock_uow.payments = AsyncMock()
    mock_uow.outbox = AsyncMock()
    mock_uow.commit = AsyncMock()
    return mock_uow


@pytest.fixture
def mock_event_bus():
    """Fixture for mocked Event Bus."""
    return AsyncMock(spec=PaymentEventBus)


@pytest.fixture
def sample_command():
    """Fixture for a standard CreatePaymentCommand."""
    return CreatePaymentCommand(
        amount=Decimal("100.00"),
        currency=Currency.USD,
        key=uuid4(),
        description="Test payment",
        metadata={"foo": "bar"},
        webhook_url="https://example.com/webhook",
    )


@pytest.fixture
def sample_payment(sample_command):
    """Fixture for a real Payment aggregate."""
    return Payment(
        amount=Amount(sample_command.amount),
        currency=sample_command.currency,
        description=Description(sample_command.description),
        metadata=Metadata(sample_command.metadata),
        key=IdempotencyKey(sample_command.key),
        webhook_url=WebhookUrl(sample_command.webhook_url),
    )


class TestCreatePaymentUseCase:
    """Tests for CreatePaymentUseCase."""

    @pytest.mark.asyncio
    async def test_create_payment_use_case_input_data(
        self, sample_command, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should create payment and return response DTO with correct fields."""
        with patch.object(
            PaymentService, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = sample_payment

            use_case = CreatePaymentUseCase()
            result = await use_case(
                command=sample_command, uow=mock_uow, event_bus=mock_event_bus
            )

        # Assert response DTO contains correct payment data
        assert isinstance(result, CreatePaymentResponse)
        assert result.payment_id == str(sample_payment.id.value)
        assert result.status == sample_payment.status
        assert result.created_at == sample_payment.created_at.value

    @pytest.mark.asyncio
    async def test_create_payment_use_case_service_parameters(
        self, sample_command, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should pass correct parameters to PaymentService.create."""
        with patch.object(
            PaymentService, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = sample_payment

            use_case = CreatePaymentUseCase()
            await use_case(
                command=sample_command, uow=mock_uow, event_bus=mock_event_bus
            )

        # Verify PaymentService.create was called with correct parameters
        mock_create.assert_awaited_once_with(
            amount=Amount(sample_command.amount),
            key=IdempotencyKey(sample_command.key),
            currency=sample_command.currency,
            metadata=Metadata(sample_command.metadata),
            webhook_url=WebhookUrl(sample_command.webhook_url),
            description=Description(sample_command.description),
        )

    @pytest.mark.asyncio
    async def test_create_payment_use_case_workflow_order(
        self, sample_command, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should execute workflow in correct order: create → outbox → commit → publish."""

        # Track the order of calls
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

        with patch.object(
            PaymentService, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = sample_payment

            use_case = CreatePaymentUseCase()
            await use_case(
                command=sample_command, uow=mock_uow, event_bus=mock_event_bus
            )

        # Verify workflow steps executed
        mock_uow.outbox.add.assert_awaited_once()
        mock_uow.commit.assert_awaited_once()
        mock_event_bus.publish_payment_events.assert_awaited_once()

        # Verify events were published
        published_events = mock_event_bus.publish_payment_events.call_args[0][0]
        assert len(published_events) == 1
        assert isinstance(published_events[0], PaymentCreatedEvent)

        # Verify order: outbox.add → commit → publish
        assert call_order == [
            "outbox_add",
            "commit",
            "publish_payment_events",
        ], f"Expected order [outbox_add, commit, publish], but got {call_order}"

    @pytest.mark.asyncio
    async def test_create_payment_use_case_duplicate_key(
        self, sample_command, mock_uow, mock_event_bus
    ):
        """UseCase should raise DomainResourceExistsError when idempotency key already exists."""
        with patch.object(
            PaymentService, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = DomainResourceExistsError(
                message="Payment already exists"
            )

            use_case = CreatePaymentUseCase()

            with pytest.raises(DomainResourceExistsError):
                await use_case(
                    command=sample_command, uow=mock_uow, event_bus=mock_event_bus
                )

        # Verify commit and publish were NOT called on error
        mock_uow.commit.assert_not_awaited()
        mock_event_bus.publish_payment_events.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_payment_use_case_outbox_add_failure(
        self, sample_command, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should not commit or publish if outbox.add fails."""
        mock_uow.outbox.add.side_effect = Exception("Database error")

        with patch.object(
            PaymentService, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = sample_payment

            use_case = CreatePaymentUseCase()

            with pytest.raises(Exception, match="Database error"):
                await use_case(
                    command=sample_command, uow=mock_uow, event_bus=mock_event_bus
                )

        # Verify transaction was not committed and events were not published
        mock_uow.commit.assert_not_awaited()
        mock_event_bus.publish_payment_events.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_payment_use_case_commit_failure(
        self, sample_command, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should not publish events if commit fails."""
        mock_uow.commit.side_effect = Exception("Transaction failed")

        with patch.object(
            PaymentService, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = sample_payment

            use_case = CreatePaymentUseCase()

            with pytest.raises(Exception, match="Transaction failed"):
                await use_case(
                    command=sample_command, uow=mock_uow, event_bus=mock_event_bus
                )

        # Verify events were not published after failed commit
        mock_event_bus.publish_payment_events.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_payment_use_case_events_content(
        self, sample_command, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should emit PaymentCreatedEvent with correct payload."""
        with patch.object(
            PaymentService, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = sample_payment

            use_case = CreatePaymentUseCase()
            await use_case(
                command=sample_command, uow=mock_uow, event_bus=mock_event_bus
            )

        # Verify events content
        published_events = mock_event_bus.publish_payment_events.call_args[0][0]
        assert len(published_events) == 1

        event = published_events[0]
        assert isinstance(event, PaymentCreatedEvent)
        assert event.payment_id == sample_payment.id.value

    @pytest.mark.asyncio
    async def test_create_payment_use_case_outbox_integration(
        self, sample_command, sample_payment, mock_uow, mock_event_bus
    ):
        """UseCase should add events to outbox with correct data."""
        with patch.object(
            PaymentService, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = sample_payment

            use_case = CreatePaymentUseCase()
            await use_case(
                command=sample_command, uow=mock_uow, event_bus=mock_event_bus
            )

        # Verify outbox.add was called with correct events
        outbox_add_call_args = mock_uow.outbox.add.call_args[0][0]
        assert len(outbox_add_call_args) == 1
        assert isinstance(outbox_add_call_args[0], PaymentCreatedEvent)

    @pytest.mark.asyncio
    async def test_create_payment_use_case_empty_metadata(
        self, mock_uow, mock_event_bus
    ):
        """UseCase should handle empty metadata correctly."""
        command = CreatePaymentCommand(
            amount=Decimal("50.00"),
            currency=Currency.EUR,
            key=uuid4(),
            description="Empty metadata test",
            metadata={},
            webhook_url="https://example.com/webhook",
        )

        payment = Payment(
            amount=Amount(command.amount),
            currency=command.currency,
            description=Description(command.description),
            metadata=Metadata(command.metadata),
            key=IdempotencyKey(command.key),
            webhook_url=WebhookUrl(command.webhook_url),
        )

        with patch.object(
            PaymentService, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = payment

            use_case = CreatePaymentUseCase()
            result = await use_case(
                command=command, uow=mock_uow, event_bus=mock_event_bus
            )

        assert isinstance(result, CreatePaymentResponse)
        assert result.payment_id == str(payment.id.value)


class TestCreatePaymentResponse:
    """Tests for CreatePaymentResponse DTO."""

    def test_create_payment_response_from_domain(self):
        """Response DTO should correctly map Payment aggregate fields."""
        payment = Payment(
            amount=Amount(Decimal("75.50")),
            currency=Currency.RUB,
            description=Description("Domain mapping test"),
            metadata=Metadata({"key": "value"}),
            key=IdempotencyKey(uuid4()),
            webhook_url=WebhookUrl("https://example.com/webhook"),
        )

        response = CreatePaymentResponse.from_domain(payment)

        assert isinstance(response, CreatePaymentResponse)
        assert response.payment_id == str(payment.id.value)
        assert response.status == payment.status
        assert (
            response.status == PaymentStatus.PENDING
        )  # Newly created payments start as PENDING
        assert response.created_at == payment.created_at.value
        assert isinstance(response.created_at, datetime)

    def test_create_payment_response_frozen(self):
        """Response DTO should be immutable."""
        response = CreatePaymentResponse(
            payment_id="test-id",
            status=PaymentStatus.PENDING,
            created_at=datetime.now(),
        )

        with pytest.raises(AttributeError):
            response.payment_id = "new-id"
