from dataclasses import dataclass, field
from typing import Self

from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus
from payments.domain.events import (
    PaymentCreatedEvent,
    PaymentDomainEvent,
    PaymentProcessedEvent,
)
from payments.domain.value_objects.amount import Amount
from payments.domain.value_objects.description import Description
from payments.domain.value_objects.id import PaymentID
from payments.domain.value_objects.key import IdempotencyKey
from payments.domain.value_objects.metadata import Metadata
from payments.domain.value_objects.timestamp import Timestamp
from payments.domain.value_objects.webhook import WebhookUrl
from shared.domain.aggregate import Aggregate
from shared.domain.entity import Entity
from shared.domain.errors import DomainBusinessRuleError
from shared.domain.value_object import ValueObject


@dataclass(kw_only=True, slots=True, eq=False)
class Payment(Aggregate[PaymentID, PaymentDomainEvent, ValueObject, Entity]):
    """
    Payment domain aggregate responsible for status updates and event emissions.

    Handles payment lifecycle: PENDING → CONFIRMED/FAILED
    Records domain events for each state transition.
    """

    id: PaymentID = field(default_factory=PaymentID)
    amount: Amount
    currency: Currency
    description: Description
    metadata: Metadata
    key: IdempotencyKey
    webhook_url: WebhookUrl
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: Timestamp = field(default_factory=Timestamp.now)
    processed_at: Timestamp | None = None

    def __post_init__(self):
        """Validate invariants and initialize creation event."""
        if not self._rebuilding:
            Aggregate.__post_init__(self)

            # Business rule: processed payments must have a timestamp
            if self.status != PaymentStatus.PENDING and self.processed_at is None:
                raise DomainBusinessRuleError(
                    "Cannot persist processed payment without processing timestamp"
                )

            # Only record creation event for new payments (not during rebuild)
            self.record_event(PaymentCreatedEvent(payment_id=self.id.value))

    # ---------------------------------------------------------
    # Behavior
    # ---------------------------------------------------------
    def _ensure_pending(self):
        """Ensure payment is in PENDING state before processing."""
        if self.status != PaymentStatus.PENDING:
            raise DomainBusinessRuleError("Already processed")

    def mark_as_succeeded(self) -> None:
        """Mark payment as successfully processed."""
        self._ensure_pending()

        object.__setattr__(self, "status", PaymentStatus.CONFIRMED)
        object.__setattr__(self, "processed_at", Timestamp.now())

        self.record_event(
            PaymentProcessedEvent(
                payment_id=self.id.value,
                status=self.status,
                amount=self.amount.value,
                currency=self.currency,
                webhook_url=self.webhook_url.value,
            )
        )

    def mark_as_failed(self, reason: str) -> None:
        """Mark payment as failed with reason."""
        self._ensure_pending()

        object.__setattr__(self, "status", PaymentStatus.FAILED)
        object.__setattr__(self, "processed_at", Timestamp.now())

        self.record_event(
            PaymentProcessedEvent(
                payment_id=self.id.value,
                status=self.status,
                reason=reason,
                amount=self.amount.value,
                currency=self.currency,
                webhook_url=self.webhook_url.value,
            )
        )

    @classmethod
    def rebuild(  # pyrefly: ignore [bad-override]
        cls,
        id: PaymentID,
        amount: Amount,
        currency: Currency,
        description: Description,
        metadata: Metadata,
        key: IdempotencyKey,
        webhook_url: WebhookUrl,
        status: PaymentStatus,
        created_at: Timestamp,
        processed_at: Timestamp | None = None,
        events: list[PaymentDomainEvent] | None = None,
    ) -> Self:
        """
        Rebuild Payment aggregate from persisted state.

        Reconstructs the aggregate from historical state without recording
        a new creation event. Business rule validation still applies.

        Args:
            id: Payment identifier
            amount: Payment amount value object
            currency: Payment currency enumeration
            description: Payment description value object
            metadata: Payment metadata value object
            key: Idempotency key for deduplication
            webhook_url: Webhook URL for notifications
            status: Current payment status
            created_at: Payment creation timestamp
            processed_at: Payment processing timestamp (if processed)
            events: domain events (defaults to empty list)

        Returns:
            Reconstructed Payment aggregate with optional events
        """
        if events is None:
            events = []
        obj = cls(
            id=id,
            amount=amount,
            currency=currency,
            description=description,
            metadata=metadata,
            key=key,
            webhook_url=webhook_url,
            status=status,
            created_at=created_at,
            processed_at=processed_at,
            _rebuilding=True,
        )

        object.__setattr__(obj, "_events", events)

        return obj
