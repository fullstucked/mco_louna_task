from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from payments.application.interfaces.event_publisher import PaymentEventBus
from payments.application.interfaces.uow import PaymentUoW
from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus
from payments.domain.payment import Payment
from payments.domain.service import PaymentService
from payments.domain.value_objects.amount import Amount
from payments.domain.value_objects.description import Description
from payments.domain.value_objects.key import IdempotencyKey
from payments.domain.value_objects.metadata import Metadata
from payments.domain.value_objects.webhook import WebhookUrl


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


class CreatePaymentUseCase:

    async def __call__(
        self,
        command: CreatePaymentCommand,
        uow: PaymentUoW,
        event_bus: PaymentEventBus,
    ) -> "CreatePaymentResponse":

        # Building value objects from command DTO
        amount = Amount(command.amount)
        currency = command.currency
        key = IdempotencyKey(command.key)
        descr = Description(command.description)
        metadata = Metadata(command.metadata)
        webhook = WebhookUrl(command.webhook_url)

        async with uow:
            # Creating new payment with idempotency-check
            service = PaymentService(repo=uow.payments)
            payment = await service.create(
                amount=amount,
                key=key,
                currency=currency,
                metadata=metadata,
                webhook_url=webhook,
                description=descr,
            )

            # events
            events = payment.pull_events()
            await uow.outbox.add(events)
            await uow.commit()

        await event_bus.publish_payment_events(events)

        return CreatePaymentResponse.from_domain(payment)


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
