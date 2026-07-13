from structlog import get_logger

from payments.application.interfaces.event_publisher import (
    EventRoutingError,
    EventSerializationError,
    PaymentEventBus,
    PublisherUnavailableError,
)
from payments.application.interfaces.uow import PaymentUoW

logger = get_logger()


class FetchPendingTasks:
    """ """

    async def __call__(
        self,
        uow: PaymentUoW,
        event_bus: PaymentEventBus,
    ) -> None:
        async with uow:
            events = await uow.outbox.get_pendings()
            if events:
                try:
                    await event_bus.publish_payment_events(events)
                except PublisherUnavailableError:
                    logger.warning("publisher_unavalible_fetching_impossible")
                    raise
                except EventRoutingError:
                    logger.error("Routing misconfigured")
                    raise
                except EventSerializationError:
                    logger.error("event_serialization_failed")
                    raise
