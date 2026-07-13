import asyncio
from random import random, uniform

from structlog import get_logger

from payments.application.interfaces.event_publisher import (
    EventRoutingError,
    EventSerializationError,
    PaymentEventBus,
    PublisherUnavailableError,
)
from payments.application.interfaces.uow import PaymentUoW
from payments.domain.events import PaymentCreatedEvent
from payments.domain.payment import Payment
from payments.domain.service import PaymentService
from payments.domain.value_objects.id import PaymentID

logger = get_logger()


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

        try:
            await event_bus.publish_payment_events(events)
        except PublisherUnavailableError:
            logger.warning("publisher_unavailable_events_in_outbox")
            raise
        except EventRoutingError:
            logger.error("Routing misconfigured")
            raise
        except EventSerializationError:
            logger.error("event_serialization_failed")
            raise

    async def _emulate_processing(self, payment: Payment) -> None:
        await asyncio.sleep(uniform(2, 5))
        success = random() < 0.9

        if success:
            payment.mark_as_succeeded()
        else:
            payment.mark_as_failed(reason="simulated error")
