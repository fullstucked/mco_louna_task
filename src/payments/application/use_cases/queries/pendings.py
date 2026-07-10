from payments.application.interfaces.event_publisher import PaymentEventBus
from payments.application.interfaces.uow import PaymentUoW


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
                await event_bus.publish_payment_events(events)
