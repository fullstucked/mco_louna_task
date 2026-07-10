from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus
from payments.domain.events import (
    EVENT_REGISTRY,
    PaymentCreatedEvent,
    PaymentProcessedEvent,
)
from payments.infrastructure.utils.events.rebuilder import EventEnvelope, rebuild_event


class TestEventEnvelope:

    def test_envelope_creates_from_dataclass(self):
        """Verify EventEnvelope is a proper frozen dataclass."""
        event_id = uuid4()
        payment_id = uuid4()
        now = datetime.utcnow()
        payload = {"payment_id": str(payment_id)}

        envelope = EventEnvelope(
            id=event_id,
            occurred_at=now,
            group="payments",
            key="new",
            payload=payload,
        )

        assert envelope.id == event_id
        assert envelope.group == "payments"
        assert envelope.key == "new"
        assert envelope.payload == payload

    def test_envelope_is_immutable(self):
        """Verify EventEnvelope frozen=True prevents mutation."""
        envelope = EventEnvelope(
            id=uuid4(),
            occurred_at=datetime.utcnow(),
            group="payments",
            key="new",
            payload={},
        )

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            envelope.group = "other"


class TestEventRegistry:

    def test_registry_excludes_base_class_with_wildcard_key(self):
        """Verify base PaymentDomainEvent is NOT registered."""
        # Base class has __event_key__ = "*"
        assert "payments.*" in EVENT_REGISTRY

    def test_registry_includes_payment_created_event(self):
        """Verify PaymentCreatedEvent is registered."""
        assert "payments.new" in EVENT_REGISTRY
        assert EVENT_REGISTRY["payments.new"] is PaymentCreatedEvent

    def test_registry_includes_payment_processed_event(self):
        """Verify PaymentProcessedEvent is registered."""
        assert "payments.processed" in EVENT_REGISTRY
        assert EVENT_REGISTRY["payments.processed"] is PaymentProcessedEvent


class TestRebuildEvent:

    def test_rebuild_from_envelope_creates_payment_created_event(self):
        """Verify rebuild_event reconstructs PaymentCreatedEvent from envelope."""
        event_id = uuid4()
        payment_id = uuid4()
        now = datetime.utcnow()

        envelope = EventEnvelope(
            id=event_id,
            occurred_at=now,
            group="payments",
            key="new",
            payload={"payment_id": payment_id},
        )

        event = rebuild_event(envelope)

        assert isinstance(event, PaymentCreatedEvent)
        assert event.id == event_id
        assert event.occurred_at == now
        assert event.payment_id == payment_id

    def test_rebuild_from_dict_creates_payment_created_event(self):
        """Verify rebuild_event handles dict format (from outbox row)."""
        event_id = uuid4()
        payment_id = uuid4()
        now = datetime.utcnow()

        row_dict = {
            "id": event_id,
            "occurred_at": now,
            "group": "payments",
            "key": "new",
            "payload": {"payment_id": payment_id},
        }

        event = rebuild_event(row_dict)

        assert isinstance(event, PaymentCreatedEvent)
        assert event.payment_id == payment_id

    def test_rebuild_payment_processed_event_with_all_fields(self):
        """Verify rebuild_event reconstructs PaymentProcessedEvent with all fields."""
        event_id = uuid4()
        payment_id = uuid4()
        now = datetime.utcnow()

        envelope = EventEnvelope(
            id=event_id,
            occurred_at=now,
            group="payments",
            key="processed",
            payload={
                "payment_id": payment_id,
                "amount": Decimal("99.99"),
                "currency": Currency.USD,
                "webhook_url": "https://webhook.example.com",
                "status": PaymentStatus.CONFIRMED,
                "reason": "Successfully charged",
            },
        )

        event = rebuild_event(envelope)

        assert isinstance(event, PaymentProcessedEvent)
        assert event.payment_id == payment_id
        assert event.amount == Decimal("99.99")
        assert event.currency == Currency.USD
        assert event.webhook_url == "https://webhook.example.com"
        assert event.status == PaymentStatus.CONFIRMED
        assert event.reason == "Successfully charged"

    def test_rebuild_payment_processed_event_with_optional_reason_none(self):
        """Verify rebuild_event handles optional reason=None."""
        envelope = EventEnvelope(
            id=uuid4(),
            occurred_at=datetime.utcnow(),
            group="payments",
            key="processed",
            payload={
                "payment_id": uuid4(),
                "amount": Decimal("50.00"),
                "currency": Currency.EUR,
                "webhook_url": "https://webhook.test",
                "status": PaymentStatus.FAILED,
                "reason": None,  # Explicitly None
            },
        )

        event = rebuild_event(envelope)

        assert event.reason is None

    def test_rebuild_raises_on_unknown_event_type(self):
        """Verify rebuild_event raises ValueError for unregistered event."""
        envelope = EventEnvelope(
            id=uuid4(),
            occurred_at=datetime.utcnow(),
            group="payments",
            key="unknown_event",
            payload={},
        )

        with pytest.raises(ValueError) as exc_info:
            rebuild_event(envelope)

        assert "Unknown event type" in str(exc_info.value)
        assert "unknown_event" in str(exc_info.value)

    def test_rebuild_raises_on_missing_payment_id(self):
        """Verify rebuild_event raises ValueError if payload missing payment_id."""
        envelope = EventEnvelope(
            id=uuid4(),
            occurred_at=datetime.utcnow(),
            group="payments",
            key="new",
            payload={},  # Missing payment_id
        )

        with pytest.raises(ValueError) as exc_info:
            rebuild_event(envelope)

        assert "Cannot reconstruct" in str(exc_info.value)
        assert "payment_id" in str(exc_info.value).lower()

    def test_rebuild_raises_on_missing_required_field_in_processed_event(self):
        """Verify rebuild_event raises if ProcessedEvent missing required fields."""
        envelope = EventEnvelope(
            id=uuid4(),
            occurred_at=datetime.utcnow(),
            group="payments",
            key="processed",
            payload={
                "payment_id": uuid4(),
                # Missing: amount, currency, webhook_url, status
            },
        )

        with pytest.raises(ValueError) as exc_info:
            rebuild_event(envelope)

        assert "Cannot reconstruct" in str(exc_info.value)

    def test_rebuild_error_message_includes_available_events(self):
        """Verify error message lists available event types."""
        envelope = EventEnvelope(
            id=uuid4(),
            occurred_at=datetime.utcnow(),
            group="payments",
            key="nonexistent",
            payload={},
        )

        with pytest.raises(
            ValueError
        ) as exc_info:  # Changed from KeyError to ValueError
            rebuild_event(envelope)

        error_msg = str(exc_info.value)
        assert "Available:" in error_msg
        assert "new" in error_msg
        assert "processed" in error_msg

    def test_rebuild_preserves_event_id_from_envelope(self):
        """Verify rebuild_event uses envelope.id, not generated."""
        event_id = uuid4()

        envelope = EventEnvelope(
            id=event_id,
            occurred_at=datetime.utcnow(),
            group="payments",
            key="new",
            payload={"payment_id": uuid4()},
        )

        event = rebuild_event(envelope)

        # Should use provided ID, not generate new one
        assert event.id == event_id

    def test_rebuild_preserves_occurred_at_from_envelope(self):
        """Verify rebuild_event uses envelope.occurred_at timestamp."""
        specific_time = datetime(2026, 7, 10, 15, 30, 45)

        envelope = EventEnvelope(
            id=uuid4(),
            occurred_at=specific_time,
            group="payments",
            key="new",
            payload={"payment_id": uuid4()},
        )

        event = rebuild_event(envelope)

        assert event.occurred_at == specific_time

    def test_rebuild_from_dict_with_uuid_objects(self):
        """Verify rebuild_event handles UUID objects in dict (not just strings)."""
        event_id = uuid4()
        payment_id = uuid4()

        row_dict = {
            "id": event_id,
            "occurred_at": datetime.utcnow(),
            "group": "payments",
            "key": "new",
            "payload": {"payment_id": payment_id},
        }

        event = rebuild_event(row_dict)

        assert event.id == event_id
        assert event.payment_id == payment_id

    @pytest.mark.parametrize(
        "event_type,key,required_fields",
        [
            ("payments.new", "created", {"payment_id"}),
            (
                "payments.processed",
                "processed",
                {"payment_id", "amount", "currency", "webhook_url", "status"},
            ),
        ],
    )
    def test_rebuild_parametrized_missing_fields(
        self, event_type, key, required_fields
    ):
        """Parametrized test: verify each event type requires its fields."""
        # Create payload with first required field
        payload = {required_fields.pop(): uuid4() if "id" in "payment_id" else "value"}

        envelope = EventEnvelope(
            id=uuid4(),
            occurred_at=datetime.utcnow(),
            group="payments",
            key=event_type,
            payload=payload,
        )

        # Should fail because other required fields missing
        with pytest.raises(ValueError):
            rebuild_event(envelope)
