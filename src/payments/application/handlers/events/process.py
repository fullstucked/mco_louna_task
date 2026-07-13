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
    """
    Event handler for PaymentCreatedEvent.

    Consumes payment creation events, simulates external gateway processing,
    updates payment state, and publishes outcome events.

    Ensures transaction boundaries: state changes committed before event
    publication to avoid loss if publisher fails.
    """

    async def __call__(
        self,
        event: PaymentCreatedEvent,
        uow: PaymentUoW,
        event_bus: PaymentEventBus,
    ):
        """
        Process a single payment event.
        Flow:
            1. Fetch payment by event.payment_id
            2. Simulate external gateway processing (2–5s delay, 90% success)
            3. Update payment state (succeeded or failed)
            4. Pull domain events from payment aggregate
            5. Persist events to outbox
            6. Commit transaction
            7. Publish events to external systems
        Args:
            event: PaymentCreatedEvent trigger
            uow: PaymentUoW for repository & outbox access
            event_bus: PaymentEventBus for external notifications
        Raises:
            PublisherUnavailableError, EventRoutingError, EventSerializationError
        """
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
        """
        Simulate external payment gateway call.

        Sleeps 2–5 seconds, then succeeds with 90% probability.
        On failure, marks payment with reason 'simulated error'.
        """
        await asyncio.sleep(uniform(2, 5))
        success = random() < 0.9

        if success:
            payment.mark_as_succeeded()
        else:
            payment.mark_as_failed(reason="simulated error")
