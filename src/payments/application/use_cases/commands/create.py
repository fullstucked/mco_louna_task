from payments.application.dto.commands.create import (
    CreatePaymentCommand,
    CreatePaymentResponse,
)
from payments.application.interfaces.event_publisher import PaymentEventBus
from payments.application.interfaces.uow import PaymentUoW
from payments.domain.service import PaymentService
from payments.domain.value_objects.amount import Amount
from payments.domain.value_objects.description import Description
from payments.domain.value_objects.key import IdempotencyKey
from payments.domain.value_objects.metadata import Metadata
from payments.domain.value_objects.webhook import WebhookUrl


class CreatePaymentUseCase:

    async def __call__(
        self,
        command: CreatePaymentCommand,
        uow: PaymentUoW,
        event_bus: PaymentEventBus,
    ) -> CreatePaymentResponse:

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
