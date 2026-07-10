from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from payments.domain.events import EVENT_REGISTRY, PaymentDomainEvent


@dataclass(frozen=True)
class EventEnvelope:
    """Represents raw event data from outbox table."""

    id: UUID
    occurred_at: datetime
    queue: str
    payload: dict[str, Any]


def rebuild_event(envelope: EventEnvelope | dict) -> PaymentDomainEvent:
    """
    Reconstructs domain event from envelope.

    Args:
        envelope: EventEnvelope or dict with id, occurred_at, group, key, payload

    Returns:
        PaymentDomainEvent subclass instance

    Raises:
        ValueError: If event type not registered
        KeyError: If payload missing required fields
    """
    # Handle both dict and EventEnvelope
    if isinstance(envelope, dict):
        queue = envelope["queue"]
        payload = envelope["payload"]
        event_id = envelope["id"]
        occurred_at = envelope["occurred_at"]
    else:
        queue = envelope.queue
        payload = envelope.payload
        event_id = envelope.id
        occurred_at = envelope.occurred_at

    registry_key = queue
    event_cls = EVENT_REGISTRY.get(registry_key)

    if not event_cls:
        raise ValueError(
            f"Unknown event type: {registry_key}. "
            f"Available: {', '.join(EVENT_REGISTRY.keys())}"
        )

    # Reconstruct event with id and occurred_at + payload fields
    try:
        return event_cls(id=event_id, occurred_at=occurred_at, **payload)
    except TypeError as e:
        raise ValueError(
            f"Cannot reconstruct {registry_key}: {e}. "
            f"Payload missing required fields?"
        ) from e
