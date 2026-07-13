from datetime import datetime
from decimal import Decimal
from typing import Any, Dict
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from payments.application.handlers.commands.create import CreatePaymentCommand
from payments.domain.enums.currency import Currency


class CreatePaymentRequest(BaseModel):
    amount: Decimal = Field(
        default=...,
        description="Amount must be greater than 0, max 2 decimal places",
        json_schema_extra={"example": 123.45},
    )
    currency: Currency = Field(...)
    description: str = Field(
        default=...,
        description=(
            "Payment description. Must be 10–250 characters. "
            "Allowed characters: letters, numbers, spaces, .,,-!?"
        ),
        json_schema_extra={"example": "Invoice test_123"},
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for payment (JSON object)",
        json_schema_extra={"example": {"order_id": "ABC123"}},
    )
    webhook_url: HttpUrl = Field(
        default=...,
        description="Webhook callback URL (http or https, cannot point to localhost)",
        json_schema_extra={"example": "https://example.com/webhook"},
    )

    model_config = ConfigDict(from_attributes=True)
    model_config = ConfigDict(from_attributes=True)

    def to_domain(self, key) -> CreatePaymentCommand:
        return CreatePaymentCommand(
            amount=self.amount,
            currency=self.currency,
            key=UUID(key),
            description=self.description,
            metadata=self.metadata,
            webhook_url=str(self.webhook_url),
        )


class CreatePaymentResponse(BaseModel):
    payment_id: str = Field(
        ...,
        description="Unique payment ID",
        json_schema_extra={"example": "f47ac10b-58cc-4372-a567-0e02b2c3d479"},
    )
    status: str = Field(
        ..., description="Payment status", json_schema_extra={"example": "PENDING"}
    )
    created_at: datetime = Field(
        ...,
        description="Creation timestamp",
        json_schema_extra={"example": "2026-04-02T12:34:56Z"},
    )

    model_config = ConfigDict(from_attributes=True)
