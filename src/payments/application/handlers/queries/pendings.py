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
    """
    Background task processor for pending payment events.

    Polls outbox for unprocessed events and publishes them via event bus.
    Handles publisher failures gracefully—events remain PENDING for retry.

    Intended to run periodically (e.g., every 5-30 seconds) to ensure
    eventual delivery of events to external systems.
    """

    async def __call__(
        self,
        uow: PaymentUoW,
        event_bus: PaymentEventBus,
    ) -> None:
        """
        Fetch and publish pending events.
        Args:
            uow: PaymentUoW for outbox repository access
            event_bus: PaymentEventBus for external notifications
        Raises:
            PublisherUnavailableError, EventRoutingError, EventSerializationError
        """
        async with uow:
            events = await uow.outbox.get_pendings()
            try:
                await event_bus.publish_payment_events(events)
            except PublisherUnavailableError:
                #logger.warning("publisher_unavalible_fetching_impossible")
                raise
            except EventRoutingError:
                #logger.error("Routing misconfigured")
                raise
            except EventSerializationError:
                #logger.error("event_serialization_failed")
                raise
