from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus
from payments.domain.payment import Payment


@dataclass(frozen=True, slots=True, kw_only=True)
class CreatePaymentCommand:
    """
    DTO Command to create new payment instance
    """

    amount: Decimal
    currency: Currency
    key: UUID
    description: str
    metadata: dict[str, Any]
    webhook_url: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CreatePaymentResponse:
    """
    DTO for response to payment creating command
    """

    payment_id: str
    status: PaymentStatus
    created_at: datetime

    @classmethod
    def from_domain(cls, payment: Payment):
        return cls(
            payment_id=str(payment.id.value),
            status=payment.status,
            created_at=payment.created_at.value,
        )
