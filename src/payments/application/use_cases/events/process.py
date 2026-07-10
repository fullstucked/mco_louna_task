import asyncio
from random import random, uniform

from payments.application.interfaces.event_publisher import PaymentEventBus
from payments.application.interfaces.uow import PaymentUoW
from payments.domain.events import PaymentCreatedEvent
from payments.domain.payment import Payment
from payments.domain.service import PaymentService
from payments.domain.value_objects.id import PaymentID


class ProcessPayment:

    async def __call__(
        self,
        event: PaymentCreatedEvent,
        uow: PaymentUoW,
        event_bus: PaymentEventBus,
    ):
        async with uow:
            service = PaymentService(repo=uow.payments)
            payment = await uow.payments.get_by_id(PaymentID(event.payment_id))

            await self._emulate_processing(payment=payment)
            await service.update_processed_payment(payment)

            events = payment.pull_events()
            await uow.outbox.add(events)
            await uow.commit()

        await event_bus.publish_payment_events(events)

    async def _emulate_processing(self, payment: Payment) -> None:
        await asyncio.sleep(uniform(2, 5))
        success = random() < 0.9

        if success:
            payment.mark_as_succeeded()
        else:
            payment.mark_as_failed(reason="simulated error")
