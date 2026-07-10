from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from payments.application.dto.commands.create import (
    CreatePaymentCommand,
    CreatePaymentResponse,
)
from payments.application.interfaces.event_publisher import PaymentEventBus
from payments.application.interfaces.uow import PaymentUoW
from payments.application.use_cases.commands.create import CreatePaymentUseCase
from payments.domain.enums.currency import Currency
from payments.domain.events import PaymentCreatedEvent
from payments.domain.payment import Payment
from payments.domain.service import PaymentService
from payments.domain.value_objects.amount import Amount
from payments.domain.value_objects.description import Description
from payments.domain.value_objects.key import IdempotencyKey
from payments.domain.value_objects.metadata import Metadata
from payments.domain.value_objects.webhook import WebhookUrl
from shared.domain.errors import DomainResourceExistsError


class TestCreatePaymentUseCase:
    """Tests for CreatePaymentUseCase."""

    @pytest.mark.asyncio
    async def test_create_payment_use_case_input_data(self):
        """UseCase should create payment and return response DTO with correct fields."""
        command = CreatePaymentCommand(
            amount=Decimal("100.00"),
            currency=Currency.USD,
            key=uuid4(),
            description="Test payment",
            metadata={"foo": "bar"},
            webhook_url="https://example.com/webhook",
        )

        # Create expected payment aggregate
        payment = Payment(
            amount=Amount(command.amount),
            currency=command.currency,
            description=Description(command.description),
            metadata=Metadata(command.metadata),
            key=IdempotencyKey(command.key),
            webhook_url=WebhookUrl(command.webhook_url),
        )

        # Mock UoW and dependencies
        mock_payments_repo = AsyncMock()
        mock_outbox_repo = AsyncMock()

        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.payments = mock_payments_repo
        mock_uow.outbox = mock_outbox_repo
        mock_uow.commit = AsyncMock()

        mock_event_bus = AsyncMock(spec=PaymentEventBus)
        mock_event_bus.publish_payment_events = AsyncMock()

        # Mock PaymentService.create to return our test payment
        with patch.object(
            PaymentService, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = payment

            use_case = CreatePaymentUseCase()
            result = await use_case(
                command=command, uow=mock_uow, event_bus=mock_event_bus
            )

        # Assert response DTO contains correct payment data
        assert isinstance(result, CreatePaymentResponse)
        assert result.payment_id == payment.id.value
        assert result.status == payment.status
        assert result.created_at == payment.created_at.value

    @pytest.mark.asyncio
    async def test_create_payment_use_case_workflow(self):
        """UseCase should execute full workflow: create, save, commit, publish."""
        command = CreatePaymentCommand(
            amount=Decimal("100.00"),
            currency=Currency.USD,
            key=uuid4(),
            description="Test payment",
            metadata={},
            webhook_url="https://example.com/webhook",
        )

        # Mock repositories
        mock_payments_repo = AsyncMock()
        mock_outbox_repo = AsyncMock()

        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.payments = mock_payments_repo
        mock_uow.outbox = mock_outbox_repo
        mock_uow.commit = AsyncMock()

        mock_event_bus = AsyncMock(spec=PaymentEventBus)

        # Create real payment to track events
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
            await use_case(command=command, uow=mock_uow, event_bus=mock_event_bus)

        # Assert workflow steps executed in order
        mock_outbox_repo.add.assert_awaited_once()
        mock_uow.commit.assert_awaited_once()
        mock_event_bus.publish_payment_events.assert_awaited_once()

        # Verify events were published
        published_events = mock_event_bus.publish_payment_events.call_args[0][0]
        assert len(published_events) == 1
        assert isinstance(published_events[0], PaymentCreatedEvent)

    @pytest.mark.asyncio
    async def test_create_payment_use_case_duplicate_key(self):
        """UseCase should raise PaymentExistsError when idempotency key already exists."""
        command = CreatePaymentCommand(
            amount=Decimal("100.00"),
            currency=Currency.USD,
            key=uuid4(),
            description="Test duplicate key",
            metadata={},
            webhook_url="https://example.com/webhook",
        )

        # Mock repositories
        mock_payments_repo = AsyncMock()
        mock_outbox_repo = AsyncMock()

        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.payments = mock_payments_repo
        mock_uow.outbox = mock_outbox_repo

        mock_event_bus = AsyncMock(spec=PaymentEventBus)

        # PaymentService.create raises PaymentExistsError for duplicate key
        with patch.object(
            PaymentService, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = DomainResourceExistsError(
                message="Payment already exists"
            )
            use_case = CreatePaymentUseCase()

            with pytest.raises(DomainResourceExistsError):
                await use_case(command=command, uow=mock_uow, event_bus=mock_event_bus)

        # Verify commit and publish were NOT called on error
        mock_uow.commit.assert_not_awaited()
        mock_event_bus.publish_payment_events.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_payment_use_case_events_content(self):
        """UseCase should emit PaymentCreatedEvent with correct payload."""
        command = CreatePaymentCommand(
            amount=Decimal("42.00"),
            currency=Currency.EUR,
            key=uuid4(),
            description="Event content test",
            metadata={"meta": "data"},
            webhook_url="https://example.com/webhook",
        )

        # Mock repositories
        mock_payments_repo = AsyncMock()
        mock_outbox_repo = AsyncMock()

        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.payments = mock_payments_repo
        mock_uow.outbox = mock_outbox_repo
        mock_uow.commit = AsyncMock()

        mock_event_bus = AsyncMock(spec=PaymentEventBus)

        # Create real payment to verify event content
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
            await use_case(command=command, uow=mock_uow, event_bus=mock_event_bus)

        # Verify events content
        published_events = mock_event_bus.publish_payment_events.call_args[0][0]
        assert len(published_events) == 1

        event = published_events[0]
        assert isinstance(event, PaymentCreatedEvent)
        assert event.payment_id == payment.id.value

    @pytest.mark.asyncio
    async def test_create_payment_use_case_outbox_integration(self):
        """UseCase should add events to outbox before publishing."""
        command = CreatePaymentCommand(
            amount=Decimal("50.00"),
            currency=Currency.RUB,
            key=uuid4(),
            description="Outbox test",
            metadata={},
            webhook_url="https://example.com/webhook",
        )

        mock_payments_repo = AsyncMock()
        mock_outbox_repo = AsyncMock()

        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.payments = mock_payments_repo
        mock_uow.outbox = mock_outbox_repo
        mock_uow.commit = AsyncMock()

        mock_event_bus = AsyncMock(spec=PaymentEventBus)

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
            await use_case(command=command, uow=mock_uow, event_bus=mock_event_bus)

        # Verify outbox.add was called with events before commit
        outbox_add_call_args = mock_outbox_repo.add.call_args[0][0]
        assert len(outbox_add_call_args) == 1
        assert isinstance(outbox_add_call_args[0], PaymentCreatedEvent)
