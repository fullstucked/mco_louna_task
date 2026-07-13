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
    """
    Decorator to register domain event classes in the global event registry.

    Enables event sourcing and reconstruction by mapping
    event identifiers (event_group.event_key) to their corresponding classes.

    Args:
        cls: A PaymentDomainEvent subclass to register.

    Returns:
        The unmodified class (to allow stacking with @dataclass).
    """
    EVENT_REGISTRY[f"{cls.__event_group__}.{cls.__event_key__}"] = cls
    return cls


@register_event
@dataclass(slots=True, frozen=True)
class PaymentDomainEvent(DomainEvent):
    """
    Base class for all payment-related domain events.

    Represents immutable events that capture changes to payments throughout
    their lifecycle. Serves as the root for an event hierarchy, establishing
    common structure (payment_id) and metadata (__version__, __event_group__,
    __event_key__) used for event sourcing and routing to appropriate handlers.

    Events are automatically registered upon definition, enabling deserialization
    from persisted event data via the EVENT_REGISTRY.

    Attributes:
        payment_id: UUID
            The unique identifier of the payment this event relates to.

    Class Variables:
        __version__: int = 1
            Event schema version for handling evolution of event formats
            and backward/forward compatibility in event sourcing.

        __event_group__: str = "payments"
            Hierarchical namespace grouping related events. Used to route
            events to appropriate domain handlers.

        __event_key__: str = "*"
            Unique identifier within the event group. Subclasses override
            to distinguish specific event types (e.g., "new", "processed").

    Inheritance:
        Subclasses must override __event_key__ to provide a unique identifier.
        __version__ should be incremented when the event schema changes.
    """

    payment_id: UUID = field(kw_only=True)

    __version__: ClassVar[int] = 1
    __event_group__: ClassVar[str] = "payments"
    __event_key__: ClassVar[str] = "*"


@register_event
@dataclass(slots=True, frozen=True)
class PaymentCreatedEvent(PaymentDomainEvent):
    """
    Domain event emitted when a new payment is successfully created.

    Attributes:
        Inherits all attributes from PaymentDomainEvent:
        - payment_id: UUID of the created payment

    Event Metadata:
        __event_key__: "new"

    Typical Usage:
        Emitted by PaymentService.create() after successfully saving
        a new Payment aggregate to the repository.
    """

    __event_key__: ClassVar[str] = "new"


@register_event
@dataclass(slots=True, frozen=True)
class PaymentProcessedEvent(PaymentDomainEvent):
    """
    Domain event emitted when a payment has been processed by the payment gateway.

    Attributes:
        payment_id: UUID
            Inherited from PaymentDomainEvent. The payment being processed.

        amount: Decimal
            The processed monetary amount. Must match the original request.

        currency: Currency
            The currency of the transaction (RUB, USD, EUR).

        webhook_url: str
            The endpoint that receives a notification about this processing result.

        status: PaymentStatus
            The final outcome: PENDING, CONFIRMED, or FAILED.

        reason: str | None
            Optional explanation if status is FAILED.

    Event Metadata:
        __event_key__: "processed"

    Typical Usage:
        Emitted by PaymentService.update_processed_payment() after the payment
        gateway returns a processing result and the Payment aggregate is updated.
    """

    amount: Decimal = field(kw_only=True)
    currency: Currency = field(kw_only=True)
    webhook_url: str = field(kw_only=True)
    status: PaymentStatus = field(kw_only=True)
    reason: str | None = None

    __event_key__: ClassVar[str] = "processed"
