from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from payments.domain.events import PaymentDomainEvent
from shared.infra.errors import SerializationError

# Metadata that shouldn't leak into payload
METADATA_FIELDS = {
    "id",
    "occurred_at",
    "payload",
    "__version__",
    "__event_key__",
    "__event_group__",
}


def _serialize_value(value: Any, convert_to_iso: bool = False) -> Any:
    """Recursively serialize non-JSON types"""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    if isinstance(value, datetime) and not convert_to_iso:
        return value
    if isinstance(value, datetime) and convert_to_iso:
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    if is_dataclass(value):
        return {f.name: _serialize_value(getattr(value, f.name)) for f in fields(value)}

    raise SerializationError(f"Cannot serialize {type(value).__name__}: {value}")


def serialize_event(
    event: PaymentDomainEvent, convert_to_iso: bool = False
) -> dict[str, Any]:
    """Convert event to outbox record"""
    event_dict = asdict(event)

    # Extract payload (everything except metadata)
    payload = {
        k: _serialize_value(v, convert_to_iso)
        for k, v in event_dict.items()
        if k not in METADATA_FIELDS
    }
    return {
        "id": str(event.id),
        "occurred_at": (
            event.occurred_at.isoformat() if convert_to_iso else event.occurred_at
        ),
        "queue": f"{event.__event_group__}.{event.__event_key__}",
        "payload": payload,
    }
