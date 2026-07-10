from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import ClassVar
from uuid import UUID

from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus
from shared.domain.event import DomainEvent

# For registry of events related to payment and future rebuilds
EVENT_REGISTRY: dict[str, type[PaymentDomainEvent]] = {}


def register_event(cls: type[PaymentDomainEvent]):
    """Registry for future event rebuilds from raw data"""
    EVENT_REGISTRY[f"{cls.__event_group__}.{cls.__event_key__}"] = cls
    return cls


@register_event
@dataclass(slots=True, frozen=True)
class PaymentDomainEvent(DomainEvent):
    """
    Basic domain event class which stores
    __event_group__ param to handle
    by relative event handlers
    """

    payment_id: UUID = field(kw_only=True)

    __version__: ClassVar[int] = 1
    __event_group__: ClassVar[str] = "payments"
    __event_key__: ClassVar[str] = "*"


@register_event
@dataclass(slots=True, frozen=True)
class PaymentCreatedEvent(PaymentDomainEvent):
    """
    Emmits at creation new
    """

    __event_key__: ClassVar[str] = "new"


@register_event
@dataclass(slots=True, frozen=True)
class PaymentProcessedEvent(PaymentDomainEvent):
    """
    Emmits at processing
    """

    amount: Decimal = field(kw_only=True)
    currency: Currency = field(kw_only=True)
    webhook_url: str = field(kw_only=True)
    status: PaymentStatus = field(kw_only=True)
    reason: str | None = None

    __event_key__: ClassVar[str] = "processed"
