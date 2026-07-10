import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from aio_pika import DeliveryMode, Message

from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus
from payments.domain.events import (
    PaymentCreatedEvent,
    PaymentDomainEvent,
    PaymentProcessedEvent,
)
from payments.infrastructure.broker.event_bus import AMQPEventPublisher
from payments.infrastructure.broker.routes import (
    EXCHANGE_REGISTRY,
    QUEUE_REGISTRY,
    dlq,
    payments_dlx,
)

# ===== FIXTURES =====


@pytest.fixture
def mock_broker():
    """Mock RabbitBroker instance."""
    broker = AsyncMock()
    broker.publish = AsyncMock()
    return broker


@pytest.fixture
def publisher(mock_broker):
    """Publisher instance with mocked broker."""
    return AMQPEventPublisher(broker=mock_broker)


@pytest.fixture
def payment_id():
    """Sample payment UUID."""
    return UUID("550e8400-e29b-41d4-a716-446655440000")


@pytest.fixture
def sample_payment_created_event(payment_id):
    """Sample PaymentCreatedEvent."""
    return PaymentCreatedEvent(
        id=UUID("550e8400-e29b-41d4-a716-446655440001"),
        payment_id=payment_id,
        occurred_at=datetime.now(),
    )


@pytest.fixture
def sample_payment_processed_event(payment_id):
    """Sample PaymentProcessedEvent."""
    return PaymentProcessedEvent(
        id=UUID("550e8400-e29b-41d4-a716-446655440002"),
        payment_id=payment_id,
        amount=Decimal("100.50"),
        currency=Currency.USD,
        webhook_url="https://example.com/webhook",
        status=PaymentStatus.CONFIRMED,
        reason=None,
        occurred_at=datetime.now(),
    )


@pytest.fixture(autouse=True)
def setup_registries():
    """Ensure registries are populated before each test."""
    # The registries should already be populated by the imports above
    # But we verify they have the expected entries
    assert PaymentCreatedEvent in QUEUE_REGISTRY, "PaymentCreatedEvent not registered"
    assert (
        PaymentProcessedEvent in QUEUE_REGISTRY
    ), "PaymentProcessedEvent not registered"
    assert (
        PaymentCreatedEvent in EXCHANGE_REGISTRY
    ), "PaymentCreatedEvent not in exchange registry"
    assert (
        PaymentProcessedEvent in EXCHANGE_REGISTRY
    ), "PaymentProcessedEvent not in exchange registry"
    yield


# ===== BASIC PUBLISHING TESTS =====


@pytest.mark.asyncio
async def test_publish_single_payment_created_event(
    publisher, mock_broker, sample_payment_created_event
):
    """Test successful publishing of PaymentCreatedEvent."""
    await publisher.publish_payment_events([sample_payment_created_event])

    # Verify publish was called once
    mock_broker.publish.assert_called_once()

    # Extract call arguments
    call_args = mock_broker.publish.call_args
    message = call_args.kwargs["message"]
    routing_key = call_args.kwargs["routing_key"]
    exchange = call_args.kwargs["exchange"]

    # Verify message properties
    assert isinstance(message, Message)
    assert message.content_type == "application/json"
    assert message.delivery_mode == DeliveryMode.PERSISTENT

    # Verify routing
    assert routing_key == PaymentCreatedEvent.__event_key__  # "new"
    assert exchange == EXCHANGE_REGISTRY[PaymentCreatedEvent]


@pytest.mark.asyncio
async def test_publish_payment_processed_event(
    publisher, mock_broker, sample_payment_processed_event
):
    """Test publishing of PaymentProcessedEvent with additional fields."""
    await publisher.publish_payment_events([sample_payment_processed_event])

    mock_broker.publish.assert_called_once()
    call_args = mock_broker.publish.call_args

    assert (
        call_args.kwargs["routing_key"] == PaymentProcessedEvent.__event_key__
    )  # "processed"
    assert call_args.kwargs["exchange"] == EXCHANGE_REGISTRY[PaymentProcessedEvent]


# ===== MULTIPLE EVENTS TESTS =====


@pytest.mark.asyncio
async def test_publish_multiple_events(
    publisher, mock_broker, sample_payment_created_event, sample_payment_processed_event
):
    """Test publishing multiple events in a single call."""
    events = [sample_payment_created_event, sample_payment_processed_event]
    await publisher.publish_payment_events(events)

    # Verify publish was called twice
    assert mock_broker.publish.call_count == 2

    # Verify first event
    first_call = mock_broker.publish.call_args_list[0]
    assert first_call.kwargs["routing_key"] == "new"

    # Verify second event
    second_call = mock_broker.publish.call_args_list[1]
    assert second_call.kwargs["routing_key"] == "processed"


@pytest.mark.asyncio
async def test_publish_empty_events_list(publisher, mock_broker):
    """Test handling of empty events list."""
    await publisher.publish_payment_events([])

    mock_broker.publish.assert_not_called()


# ===== MESSAGE SERIALIZATION TESTS =====


@pytest.mark.asyncio
async def test_message_body_is_valid_json(
    publisher, mock_broker, sample_payment_created_event
):
    """Test that message body is valid JSON."""
    await publisher.publish_payment_events([sample_payment_created_event])

    message = mock_broker.publish.call_args.kwargs["message"]
    decoded_body = json.loads(message.body.decode())

    # Verify structure
    assert "id" in decoded_body
    assert "occurred_at" in decoded_body
    assert "queue" in decoded_body
    assert "payload" in decoded_body


@pytest.mark.asyncio
async def test_message_contains_serialized_event_data(
    publisher, mock_broker, sample_payment_created_event
):
    """Test that message contains correctly serialized event data."""
    await publisher.publish_payment_events([sample_payment_created_event])

    message = mock_broker.publish.call_args.kwargs["message"]
    decoded_body = json.loads(message.body.decode())

    # Verify payload contains payment_id
    assert decoded_body["payload"]["payment_id"] == str(
        sample_payment_created_event.payment_id
    )
    assert decoded_body["queue"] == "payments.new"


@pytest.mark.asyncio
async def test_complex_event_serialization(
    publisher, mock_broker, sample_payment_processed_event
):
    """Test serialization of event with complex types (Decimal, Enum)."""
    await publisher.publish_payment_events([sample_payment_processed_event])

    message = mock_broker.publish.call_args.kwargs["message"]
    decoded_body = json.loads(message.body.decode())
    payload = decoded_body["payload"]

    # Verify Decimal serialization
    assert payload["amount"] == "100.50"

    # Verify Enum serialization
    assert payload["status"] == PaymentStatus.CONFIRMED.value

    # Verify Currency Enum serialization
    assert payload["currency"] == Currency.USD.value


# ===== ERROR HANDLING & DLQ TESTS =====


@pytest.mark.asyncio
async def test_unknown_event_type_sent_to_dlq(publisher, mock_broker, payment_id):
    """Test that unknown event types are sent to DLQ before raising error."""

    unknown_event = MagicMock(spec=PaymentDomainEvent)
    unknown_event.__event_group__ = "payments"
    unknown_event.__event_key__ = "unknown"
    unknown_event.id = UUID("550e8400-e29b-41d4-a716-446655440003")
    unknown_event.occurred_at = datetime.now()
    unknown_event.payment_id = payment_id

    # Patch where serialize_event is USED, not where it's defined
    with patch(
        "payments.infrastructure.broker.event_bus.serialize_event",  # ← Corrected path
        return_value={"id": "123", "queue": "payments.unknown", "payload": {}},
    ):
        with pytest.raises(ValueError, match="Event routing not configured"):
            await publisher.publish_payment_events([unknown_event])

    assert mock_broker.publish.call_count == 1
    dlq_call = mock_broker.publish.call_args_list[0]
    assert dlq_call.kwargs["routing_key"] == dlq.routing_key
    assert dlq_call.kwargs["exchange"] == payments_dlx


@pytest.mark.asyncio
async def test_partial_failure_with_valid_event_then_invalid(
    publisher, mock_broker, sample_payment_created_event, payment_id
):
    """Test that publishing continues until unknown event is encountered."""

    unknown_event = MagicMock(spec=PaymentDomainEvent)
    unknown_event.__event_group__ = "payments"
    unknown_event.__event_key__ = "unknown"
    unknown_event.id = UUID("550e8400-e29b-41d4-a716-446655440003")
    unknown_event.occurred_at = datetime.now()
    unknown_event.payment_id = payment_id

    mock_serialize = MagicMock()
    mock_serialize.side_effect = lambda event: {
        "id": str(event.id),
        "queue": f"{event.__event_group__}.{event.__event_key__}",
        "payload": {},
    }

    with patch(
        "payments.infrastructure.broker.event_bus.serialize_event",
        side_effect=mock_serialize.side_effect,
    ):
        with pytest.raises(ValueError):
            await publisher.publish_payment_events(
                [sample_payment_created_event, unknown_event]
            )

    assert mock_broker.publish.call_count == 2


@pytest.mark.asyncio
async def test_broker_exception_propagated(
    publisher, mock_broker, sample_payment_created_event
):
    """Test that broker exceptions are propagated."""
    mock_broker.publish.side_effect = Exception("Connection failed")

    with pytest.raises(Exception, match="Connection failed"):
        await publisher.publish_payment_events([sample_payment_created_event])


# ===== REGISTRY INTEGRATION TESTS =====


@pytest.mark.asyncio
async def test_correct_exchange_lookup(
    publisher, mock_broker, sample_payment_created_event
):
    """Test that correct exchange is looked up from EXCHANGE_REGISTRY."""
    await publisher.publish_payment_events([sample_payment_created_event])

    exchange = mock_broker.publish.call_args.kwargs["exchange"]
    assert exchange == EXCHANGE_REGISTRY[PaymentCreatedEvent]


@pytest.mark.asyncio
async def test_correct_queue_routing_key_lookup(
    publisher, mock_broker, sample_payment_created_event
):
    """Test that correct routing key is looked up from QUEUE_REGISTRY."""
    await publisher.publish_payment_events([sample_payment_created_event])

    routing_key = mock_broker.publish.call_args.kwargs["routing_key"]
    assert routing_key == QUEUE_REGISTRY[PaymentCreatedEvent].routing_key


# ===== MESSAGE STRUCTURE TESTS =====


@pytest.mark.asyncio
async def test_message_content_type_is_json(
    publisher, mock_broker, sample_payment_created_event
):
    """Test that message content type is set to application/json."""
    await publisher.publish_payment_events([sample_payment_created_event])

    message = mock_broker.publish.call_args.kwargs["message"]
    assert message.content_type == "application/json"


@pytest.mark.asyncio
async def test_message_delivery_mode_is_persistent(
    publisher, mock_broker, sample_payment_created_event
):
    """Test that message delivery mode is persistent."""
    await publisher.publish_payment_events([sample_payment_created_event])

    message = mock_broker.publish.call_args.kwargs["message"]
    assert message.delivery_mode == DeliveryMode.PERSISTENT


@pytest.mark.asyncio
async def test_message_body_is_bytes(
    publisher, mock_broker, sample_payment_created_event
):
    """Test that message body is encoded as bytes."""
    await publisher.publish_payment_events([sample_payment_created_event])

    message = mock_broker.publish.call_args.kwargs["message"]
    assert isinstance(message.body, bytes)


# ===== EDGE CASE TESTS =====


@pytest.mark.asyncio
async def test_event_with_none_optional_field(publisher, mock_broker, payment_id):
    """Test event with None optional field serializes correctly."""
    # Create new instance with reason=None (can't modify frozen dataclass)
    event = PaymentProcessedEvent(
        id=UUID("550e8400-e29b-41d4-a716-446655440004"),
        payment_id=payment_id,
        amount=Decimal("50.00"),
        currency=Currency.EUR,
        webhook_url="https://example.com/webhook",
        status=PaymentStatus.CONFIRMED,
        reason=None,
        occurred_at=datetime.now(),
    )

    await publisher.publish_payment_events([event])

    message = mock_broker.publish.call_args.kwargs["message"]
    decoded_body = json.loads(message.body.decode())

    assert decoded_body["payload"]["reason"] is None


@pytest.mark.asyncio
async def test_uuid_fields_serialized_as_strings(
    publisher, mock_broker, sample_payment_created_event
):
    """Test that UUID fields are serialized as strings."""
    await publisher.publish_payment_events([sample_payment_created_event])

    message = mock_broker.publish.call_args.kwargs["message"]
    decoded_body = json.loads(message.body.decode())

    # Both id and payment_id should be strings
    assert isinstance(decoded_body["id"], str)
    assert isinstance(decoded_body["payload"]["payment_id"], str)
    assert decoded_body["id"] == str(sample_payment_created_event.id)


@pytest.mark.asyncio
async def test_datetime_fields_serialized_as_iso_format(
    publisher, mock_broker, sample_payment_created_event
):
    """Test that datetime fields are serialized as ISO format strings."""
    await publisher.publish_payment_events([sample_payment_created_event])

    message = mock_broker.publish.call_args.kwargs["message"]
    decoded_body = json.loads(message.body.decode())

    # occurred_at should be ISO format string
    assert isinstance(decoded_body["occurred_at"], str)
    assert "T" in decoded_body["occurred_at"]  # ISO format includes T


@pytest.mark.asyncio
async def test_generator_of_events(
    publisher, mock_broker, sample_payment_created_event, sample_payment_processed_event
):
    """Test that events can be passed as generator (Iterable)."""

    def event_generator():
        yield sample_payment_created_event
        yield sample_payment_processed_event

    await publisher.publish_payment_events(event_generator())

    assert mock_broker.publish.call_count == 2


@pytest.mark.asyncio
async def test_multiple_processed_events_with_different_data(
    publisher, mock_broker, payment_id
):
    """Test publishing multiple processed events with different data."""
    event1 = PaymentProcessedEvent(
        id=UUID("550e8400-e29b-41d4-a716-446655440005"),
        payment_id=payment_id,
        amount=Decimal("100.00"),
        currency=Currency.USD,
        webhook_url="https://example.com/webhook1",
        status=PaymentStatus.CONFIRMED,
        reason=None,
        occurred_at=datetime.now(),
    )

    event2 = PaymentProcessedEvent(
        id=UUID("550e8400-e29b-41d4-a716-446655440006"),
        payment_id=UUID("550e8400-e29b-41d4-a716-446655440010"),
        amount=Decimal("250.75"),
        currency=Currency.EUR,
        webhook_url="https://example.com/webhook2",
        status=PaymentStatus.FAILED,
        reason="Insufficient funds",
        occurred_at=datetime.now(),
    )

    await publisher.publish_payment_events([event1, event2])

    assert mock_broker.publish.call_count == 2

    # Verify first event
    first_call = mock_broker.publish.call_args_list[0]
    first_body = json.loads(first_call.kwargs["message"].body.decode())
    assert first_body["payload"]["amount"] == "100.00"
    assert first_body["payload"]["currency"] == "USD"
    assert first_body["payload"]["status"] == "CONFIRMED"
    assert first_body["payload"]["reason"] is None

    # Verify second event
    second_call = mock_broker.publish.call_args_list[1]
    second_body = json.loads(second_call.kwargs["message"].body.decode())
    assert second_body["payload"]["amount"] == "250.75"
    assert second_body["payload"]["currency"] == "EUR"
    assert second_body["payload"]["status"] == "FAILED"
    assert second_body["payload"]["reason"] == "Insufficient funds"


@pytest.mark.asyncio
async def test_event_metadata_fields_excluded_from_payload(
    publisher, mock_broker, sample_payment_processed_event
):
    """Test that metadata fields are excluded from payload."""
    await publisher.publish_payment_events([sample_payment_processed_event])

    message = mock_broker.publish.call_args.kwargs["message"]
    decoded_body = json.loads(message.body.decode())
    payload = decoded_body["payload"]

    # These should NOT be in payload (they're at top level)
    assert "id" not in payload
    assert "occurred_at" not in payload
    assert "__version__" not in payload
    assert "__event_key__" not in payload
    assert "__event_group__" not in payload

    # These SHOULD be in payload
    assert "payment_id" in payload
    assert "amount" in payload
    assert "status" in payload


@pytest.mark.asyncio
async def test_decimal_precision_preserved(publisher, mock_broker, payment_id):
    """Test that Decimal precision is preserved in serialization."""
    event = PaymentProcessedEvent(
        id=UUID("550e8400-e29b-41d4-a716-446655440007"),
        payment_id=payment_id,
        amount=Decimal("99.99"),
        currency=Currency.USD,
        webhook_url="https://example.com/webhook",
        status=PaymentStatus.CONFIRMED,
        reason=None,
        occurred_at=datetime.now(),
    )

    await publisher.publish_payment_events([event])

    message = mock_broker.publish.call_args.kwargs["message"]
    decoded_body = json.loads(message.body.decode())

    # Should preserve the exact decimal value as string
    assert decoded_body["payload"]["amount"] == "99.99"


@pytest.mark.asyncio
async def test_all_payment_statuses_serialize_correctly(
    publisher, mock_broker, payment_id
):
    """Test that all PaymentStatus enum values serialize correctly."""
    statuses = [PaymentStatus.PENDING, PaymentStatus.CONFIRMED, PaymentStatus.FAILED]

    for i, status in enumerate(statuses):
        event = PaymentProcessedEvent(
            id=UUID(f"550e8400-e29b-41d4-a716-44665544000{i}"),
            payment_id=payment_id,
            amount=Decimal("100.00"),
            currency=Currency.USD,
            webhook_url="https://example.com/webhook",
            status=status,
            reason=None,
            occurred_at=datetime.now(),
        )

        await publisher.publish_payment_events([event])

    assert mock_broker.publish.call_count == 3

    for i, expected_status in enumerate(statuses):
        call = mock_broker.publish.call_args_list[i]
        body = json.loads(call.kwargs["message"].body.decode())
        assert body["payload"]["status"] == expected_status.value


@pytest.mark.asyncio
async def test_all_currencies_serialize_correctly(publisher, mock_broker, payment_id):
    """Test that all Currency enum values serialize correctly."""
    currencies = [Currency.USD, Currency.EUR, Currency.RUB]

    for i, currency in enumerate(currencies):
        event = PaymentProcessedEvent(
            id=UUID(f"550e8400-e29b-41d4-a716-44665544001{i}"),
            payment_id=payment_id,
            amount=Decimal("100.00"),
            currency=currency,
            webhook_url="https://example.com/webhook",
            status=PaymentStatus.CONFIRMED,
            reason=None,
            occurred_at=datetime.now(),
        )

        await publisher.publish_payment_events([event])

    assert mock_broker.publish.call_count == 3

    for i, expected_currency in enumerate(currencies):
        call = mock_broker.publish.call_args_list[i]
        body = json.loads(call.kwargs["message"].body.decode())
        assert body["payload"]["currency"] == expected_currency.value


@pytest.mark.asyncio
async def test_message_headers_set_correctly(
    publisher, mock_broker, sample_payment_created_event
):
    """Test that message headers are set (if applicable)."""
    await publisher.publish_payment_events([sample_payment_created_event])

    message = mock_broker.publish.call_args.kwargs["message"]

    # Verify basic message structure
    assert message.body is not None
    assert message.content_type == "application/json"


@pytest.mark.asyncio
async def test_large_event_batch(publisher, mock_broker ):
    """Test publishing a large batch of events."""
    events = [
        PaymentCreatedEvent(
            id=UUID(f"550e8400-e29b-41d4-a716-446655440{i:03d}"),
            payment_id=UUID(f"550e8400-e29b-41d4-a716-446655441{i:03d}"),
            occurred_at=datetime.now(),
        )
        for i in range(50)
    ]

    await publisher.publish_payment_events(events)

    assert mock_broker.publish.call_count == 50


@pytest.mark.asyncio
async def test_event_group_in_message(
    publisher, mock_broker, sample_payment_created_event
):
    """Test that event group is accessible in message."""
    await publisher.publish_payment_events([sample_payment_created_event])

    message = mock_broker.publish.call_args.kwargs["message"]
    decoded_body = json.loads(message.body.decode())

    # Event group should be available in the queue name
    assert (
        decoded_body["queue"]
        == f"{PaymentCreatedEvent.__event_group__}.{PaymentCreatedEvent.__event_key__}"
    )
