from faststream import FastStream

from payments.infrastructure.broker.routes import (
    dlq,
    new_payments_q,
    notify_payments_q,
    payments_dlx,
    payments_exchange,
)
from payments.presentation.ampq.api.v1.dependencies.infra.broker import get_broker
from payments.presentation.ampq.api.v1.events.notify import (
    DELAY_BASE as NOTIFY_DELAY_BASE,
)
from payments.presentation.ampq.api.v1.events.notify import (
    MAX_ATTEMPTS as NOTIFY_MAX_ATTEMPTS,
)
from payments.presentation.ampq.api.v1.events.notify import notify_router
from payments.presentation.ampq.api.v1.events.process import (
    DELAY_BASE as PROCESS_DELAY_BASE,
)
from payments.presentation.ampq.api.v1.events.process import (
    MAX_ATTEMPTS as PROCESS_MAX_ATTEMTS,
)
from payments.presentation.ampq.api.v1.events.process import process_router
from shared.infra.broker.utils.bind_queues import (
    bind_queues_to_exch,
    bind_queues_with_retry_to_exch,
)


async def create_app() -> FastStream:
    """
    Default app factory with creating retry queues
    """

    broker = get_broker()
    await broker.connect()

    ### Dead letter queue
    await bind_queues_to_exch(broker=broker, exch=payments_dlx, queues=[dlq])

    ## New payment creation
    await bind_queues_with_retry_to_exch(
        broker=broker,
        exch=payments_exchange,
        dead_exch=payments_dlx,
        base_queue=new_payments_q,
        retry_base=PROCESS_DELAY_BASE,
        max_attempt=PROCESS_MAX_ATTEMTS,
    )

    # Notification_creation
    await bind_queues_with_retry_to_exch(
        broker=broker,
        exch=payments_exchange,
        dead_exch=payments_dlx,
        base_queue=notify_payments_q,
        retry_base=NOTIFY_DELAY_BASE,
        max_attempt=NOTIFY_MAX_ATTEMPTS,
    )

    broker.include_router(notify_router)
    broker.include_router(process_router)

    app = FastStream(broker)

    return app


async def run_consumer():
    app = await create_app()
    await app.run()
