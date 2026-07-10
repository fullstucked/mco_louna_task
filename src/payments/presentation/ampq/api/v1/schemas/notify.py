from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus
from payments.domain.events import PaymentProcessedEvent
from payments.presentation.ampq.api.v1.schemas.base import EventData, event


@event
class NotifyEvent(BaseModel):
    payment_id: str
    amount: str
    currency: str
    webhook_url: str
    status: str
    reason: str | None = None


def notify_event_to_domain(event: EventData[NotifyEvent]) -> PaymentProcessedEvent:
    return PaymentProcessedEvent(
        payment_id=UUID(event.payload.payment_id),
        amount=Decimal(event.payload.amount),
        currency=Currency(event.payload.currency),
        reason=event.payload.reason,
        status=PaymentStatus(event.payload.status),
        webhook_url=event.payload.webhook_url,
        id=UUID(event.id),
        occurred_at=datetime.fromisoformat(event.occurred_at),
    )
