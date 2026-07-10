from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from payments.application.use_cases.events.process import ProcessPayment
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
from shared.domain.errors import DomainBusinessRuleError


@pytest.mark.asyncio
@patch(
    "payments.application.use_cases.events.process.random", return_value=0.5
)  # force success
@patch(
    "payments.application.use_cases.events.process.uniform", return_value=0
)  # skip sleep
async def test_process_payment_success(mock_uniform, mock_random):

    payment_id = uuid4()
    payment = Payment.rebuild(
        id=PaymentID.rebuild(payment_id),
        amount=Amount.rebuild(Decimal("100")),
        currency=Currency.USD,
        description=Description.rebuild("Test Payment"),
        metadata=Metadata.rebuild({}),
        status=PaymentStatus.PENDING,
        key=IdempotencyKey.rebuild(uuid4()),
        webhook_url=WebhookUrl.rebuild("http://example.com"),
        created_at=Timestamp.rebuild(None),
        processed_at=None,
    )

    ####### Mocks
    # Mock repo
    mock_payments_repo = AsyncMock()
    mock_payments_repo.get_by_id = AsyncMock(return_value=payment)
    mock_payments_repo.update = AsyncMock()

    # Mock UoW
    mock_uow = AsyncMock()
    mock_uow.__aenter__.return_value = mock_uow
    mock_uow.__aexit__.return_value = None
    mock_uow.payments = mock_payments_repo

    # Mock event bus
    mock_event_bus = AsyncMock()
    mock_event_bus.publish_payment_events = AsyncMock()

    ####### Mocks

    # Create fake event and run UC
    event = PaymentCreatedEvent(payment_id=payment_id)
    use_case = ProcessPayment()
    await use_case(event=event, uow=mock_uow, event_bus=mock_event_bus)

    # Assertions
    assert payment.status == PaymentStatus.CONFIRMED
    mock_event_bus.publish_payment_events.assert_awaited()
    mock_payments_repo.update.assert_awaited_once_with(payment=payment)


@pytest.mark.asyncio
@patch(
    "payments.application.use_cases.events.process.random", return_value=0.95
)  # force failure
@patch(
    "payments.application.use_cases.events.process.uniform", return_value=0
)  # skip sleep
async def test_process_payment_failure(mock_uniform, mock_random):
    # Prepare fake payment
    payment_id = uuid4()
    payment = Payment.rebuild(
        id=PaymentID.rebuild(payment_id),
        amount=Amount.rebuild(Decimal("100")),
        currency=Currency.USD,
        description=Description.rebuild("Test Payment"),
        metadata=Metadata.rebuild({}),
        status=PaymentStatus.PENDING,
        key=IdempotencyKey.rebuild(uuid4()),
        webhook_url=WebhookUrl.rebuild("http://example.com"),
        created_at=Timestamp.rebuild(None),
        processed_at=None,
    )

    # Mock repo
    mock_payments_repo = AsyncMock()
    mock_payments_repo.get_by_id = AsyncMock(return_value=payment)
    mock_payments_repo.update = AsyncMock()

    # Mock UoW
    mock_uow = AsyncMock()
    mock_uow.__aenter__.return_value = mock_uow
    mock_uow.__aexit__.return_value = None
    mock_uow.payments = mock_payments_repo

    # Mock event bus
    mock_event_bus = AsyncMock()
    mock_event_bus.publish_payment_events = AsyncMock()

    # Create use case
    use_case = ProcessPayment()

    # Create fake event
    event = PaymentCreatedEvent(payment_id=payment_id)

    # Run use case
    await use_case(event, uow=mock_uow, event_bus=mock_event_bus)

    # Assertions
    assert payment.status == PaymentStatus.FAILED
    mock_event_bus.publish_payment_events.assert_awaited()
    mock_payments_repo.update.assert_awaited_once_with(payment=payment)


@pytest.mark.asyncio
@patch("payments.application.use_cases.events.process.random", return_value=0.1)
@patch("payments.application.use_cases.events.process.uniform", return_value=0)
async def test_process_payment_already_processed(mock_uniform, mock_random):
    # Payment already succeeded
    payment_id = uuid4()
    payment = Payment.rebuild(
        id=PaymentID.rebuild(payment_id),
        amount=Amount.rebuild(Decimal("100")),
        currency=Currency.USD,
        description=Description.rebuild("Test Payment"),
        metadata=Metadata.rebuild({}),
        status=PaymentStatus.CONFIRMED,  # already succeeded
        key=IdempotencyKey.rebuild(uuid4()),
        webhook_url=WebhookUrl.rebuild("http://example.com"),
        created_at=Timestamp.rebuild(None),
        processed_at=Timestamp.now(),
    )

    mock_payments_repo = AsyncMock()
    mock_payments_repo.get_by_id = AsyncMock(return_value=payment)
    mock_payments_repo.update = AsyncMock()

    mock_uow = AsyncMock()
    mock_uow.__aenter__.return_value = mock_uow
    mock_uow.__aexit__.return_value = None
    mock_uow.payments = mock_payments_repo

    mock_event_bus = AsyncMock()
    mock_event_bus.publish_payment_events = AsyncMock()

    use_case = ProcessPayment()
    event = PaymentCreatedEvent(payment_id=payment_id)

    with pytest.raises(DomainBusinessRuleError):
        await use_case(event, uow=mock_uow, event_bus=mock_event_bus)

    # Assert: payment not re-processed
    assert payment.status == PaymentStatus.CONFIRMED
    mock_payments_repo.update.assert_not_awaited()
    mock_event_bus.publish_payment_events.assert_not_awaited()


@pytest.mark.asyncio
@patch("payments.application.use_cases.events.process.random", return_value=0.5)
@patch("payments.application.use_cases.events.process.uniform", return_value=0)
async def test_process_payment_service_failure(mock_uniform, mock_random):
    # Payment is pending
    payment_id = uuid4()
    payment = Payment.rebuild(
        id=PaymentID.rebuild(payment_id),
        amount=Amount.rebuild(Decimal("100")),
        currency=Currency.USD,
        description=Description.rebuild("Test Payment"),
        metadata=Metadata.rebuild({}),
        status=PaymentStatus.PENDING,
        key=IdempotencyKey.rebuild(uuid4()),
        webhook_url=WebhookUrl.rebuild("http://example.com"),
        created_at=Timestamp.rebuild(None),
        processed_at=None,
    )

    mock_payments_repo = AsyncMock()
    mock_payments_repo.get_by_id = AsyncMock(return_value=payment)
    mock_payments_repo.update = AsyncMock()

    mock_uow = AsyncMock()
    mock_uow.__aenter__.return_value = mock_uow
    mock_uow.__aexit__.return_value = None
    mock_uow.payments = mock_payments_repo
    mock_uow.commit = AsyncMock(side_effect=RuntimeError("DB commit failed"))

    mock_event_bus = AsyncMock()
    mock_event_bus.publish_payment_events = AsyncMock()

    use_case = ProcessPayment()
    event = PaymentCreatedEvent(payment_id=payment_id)

    # Act and Assert
    with pytest.raises(RuntimeError):
        await use_case(event, uow=mock_uow, event_bus=mock_event_bus)
