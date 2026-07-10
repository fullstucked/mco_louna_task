from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus
from payments.domain.payment import Payment


@dataclass(frozen=True, slots=True, kw_only=True)
class GetPaymentQuery:
    """
    DTO query to get `Payment` instance by it's `id`
    """

    id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class GetPaymentQueryResponse:
    """
    DTO for response to payment creating command
    """

    payment_id: UUID
    amount: Decimal
    currency: Currency
    description: str
    key: UUID
    metadata: dict[str, Any]
    status: PaymentStatus
    created_at: datetime
    processed_at: datetime | None

    @classmethod
    def from_domain(cls, payment: Payment):
        return cls(
            payment_id=payment.id.value,
            amount=payment.amount.value,
            currency=payment.currency,
            description=payment.description.value,
            metadata={key: str(value) for key, value in payment.metadata.value.items()},
            key=payment.key.value,
            status=payment.status,
            created_at=payment.created_at.timestamp,
            processed_at=(payment.processed_at.value if payment.processed_at else None),
        )
