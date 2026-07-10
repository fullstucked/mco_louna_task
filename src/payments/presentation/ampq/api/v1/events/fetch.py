from payments.infrastructure.broker.event_bus import AMQPEventPublisher
from payments.infrastructure.broker.routes import broker
from payments.infrastructure.database.session import async_session_factory
from payments.infrastructure.database.uow import PaymentsUoWSQLAlchemy
from sqlalchemy.ext.asyncio import AsyncSession
from payments.presentation.ampq.api.v1.dependencies.queries import get_pending_events_uc


def get_uow(session: AsyncSession):
    return PaymentsUoWSQLAlchemy(session)


def get_broker():
    return broker


async def handle_bad_events() -> None:
    """Handler for fetching unprocessed tasks in case of broker failiure."""
    ## NOT AN ACTUAL FASTSTREAM ENDPOINT SO VIA DEFAULT FACTORIES
    ### INSTEAD DEPENDENCIES
    broker = get_broker()
    await broker.connect()

    uc = get_pending_events_uc()
    await uc(
        uow=get_uow(async_session_factory()),
        event_bus=AMQPEventPublisher(broker=broker),
    )
