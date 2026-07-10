from pydantic import BaseModel
from datetime import datetime
from payments.presentation.ampq.api.v1.schemas.base import event
from uuid import UUID

from payments.domain.events import PaymentCreatedEvent
from payments.presentation.ampq.api.v1.schemas.base import EventData


@event
class NewPaymentEvent(BaseModel):
    payment_id: str


def new_pay_to_domain(event: EventData[NewPaymentEvent]) -> PaymentCreatedEvent:
    return PaymentCreatedEvent(
        id=UUID(event.id),
        occurred_at=datetime.fromisoformat(event.occurred_at),
        payment_id=UUID(event.payload.payment_id),
    )
