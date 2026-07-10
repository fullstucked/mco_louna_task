from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus


class GetPaymentResponse(BaseModel):
    payment_id: UUID
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any]
    status: PaymentStatus
    key: UUID
    created_at: datetime
    processed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
