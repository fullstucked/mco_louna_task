from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from payments.domain.events import EVENT_REGISTRY, PaymentDomainEvent


@dataclass(frozen=True, slots=False)
class EventEnvelope:
    id: UUID
    type: str
    group: str
    key: str
    occurred_at: datetime
    payload: dict[str, Any]


def rebuild_event(envelope: EventEnvelope) -> PaymentDomainEvent:
    cls = EVENT_REGISTRY.get(f"{envelope.group}.{envelope.key}")
    if not cls:
        raise ValueError(f"Unknown event: {envelope.group}.{envelope.key}")

    deserialized = {}
    for k, v in envelope.payload.items():
        if isinstance(v, dict) and v.get("_type") == "enum":
            # Rebuild enum from serialized form
            enum_cls = globals()[v["class"]]  # or use a registry
            deserialized[k] = enum_cls(v["value"])
        else:
            deserialized[k] = v

    return cls(id=envelope.id, occurred_at=envelope.occurred_at, **deserialized)


def _deserialize_envelope(data: dict) -> EventEnvelope:
    """Convert dict from redis back to EventEnvelope with proper types"""
    payment_id = data["payment_id"]
    if isinstance(payment_id, dict):
        payment_id = UUID(payment_id["id"])
    elif isinstance(payment_id, str):
        payment_id = UUID(payment_id)

    return EventEnvelope(
        id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
        type=data["type"],
        group=data["group"],
        key=data["key"],
        occurred_at=(
            data["occurred_at"]
            if isinstance(data["occurred_at"], datetime)
            else datetime.fromisoformat(data["occurred_at"])
        ),
        payload=data["payload"],
    )
