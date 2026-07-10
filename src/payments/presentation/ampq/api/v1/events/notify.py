from payments.infrastructure.database.outbox.task_status import TaskStatus
from shared.infra.broker.utils.retry_queue import create_retry_queues
from faststream import AckPolicy, Depends
from faststream.rabbit import RabbitBroker, RabbitMessage, RabbitRouter

from payments.application.use_cases.events.notify import SendNotificationUseCase
from payments.infrastructure.broker.routes import (
    dlq,
    notify_payments_q,
    payments_dlx,
    payments_exchange,
)
from payments.infrastructure.database.uow import PaymentsUoWSQLAlchemy
from payments.infrastructure.notifications.httpx_sender import HttpxWebhookSender
from payments.presentation.ampq.api.v1.dependencies.infra.broker import get_broker
from payments.presentation.ampq.api.v1.dependencies.infra.database import get_uow
from payments.presentation.ampq.api.v1.dependencies.infra.notifier import (
    get_webhook_sender,
)
from payments.presentation.ampq.api.v1.dependencies.queries import get_notify_uc
from payments.presentation.ampq.api.v1.schemas.notify import (
    NotifyEvent,
    notify_event_to_domain,
)

notify_router = RabbitRouter()

DELAY_BASE = 5  # in seconds for exponential-time retries
MAX_ATTEMPTS = 3  # max retty_attempts

retry_routing_queues = create_retry_queues(
    base_queue=notify_payments_q,
    after_expire_exch=payments_exchange,
    retry_base=DELAY_BASE,
    max_attempt=MAX_ATTEMPTS,
)


@notify_router.subscriber(
    queue=notify_payments_q, exchange=payments_exchange, ack_policy=AckPolicy.MANUAL
)
async def handle_notify_client(
    msg: RabbitMessage,
    uc: SendNotificationUseCase = Depends(get_notify_uc),
    uow: PaymentsUoWSQLAlchemy = Depends(get_uow),
    broker: RabbitBroker = Depends(get_broker),
    notifier: HttpxWebhookSender = Depends(get_webhook_sender),
) -> None:
    """Handler for events which should send notifications to webhook."""

    headers = msg.headers or {}
    attempt = headers.get("x-attempt", 0)

    notify_event = NotifyEvent.model_validate_json(msg.body)
    # pyrefly: ignore [bad-argument-type]
    event = notify_event_to_domain(notify_event)
    async with uow:
        claimed = await uow.outbox.mark_in_process(event.id)
    if claimed or attempt > 0 and attempt < MAX_ATTEMPTS:

        try:
            await uc(
                event=event,
                notifier=notifier,
            )
            async with uow:
                await uow.outbox.mark_processed(
                    event.id,
                    # pyrefly: ignore [bad-argument-type]
                    upd_status=TaskStatus.CONFIRMED,
                )
                await uow.commit()

        except Exception:

            await broker.connect()
            if attempt < MAX_ATTEMPTS:
                await broker.publish(
                    msg.body,
                    exchange=payments_dlx,
                    routing_key=retry_routing_queues[attempt].routing_key,
                    headers={"x-attempt": attempt + 1},
                )
            else:
                async with uow:
                    await uow.outbox.mark_processed(
                        event_id=event.id,
                        # pyrefly: ignore [bad-argument-type]
                        upd_status=TaskStatus.FAILED,
                    )
                    await uow.commit()

                await broker.publish(
                    msg.body,
                    exchange=payments_dlx,
                    routing_key=dlq.routing_key,
                    headers={"x-attempt": attempt},
                )

    await msg.ack()
