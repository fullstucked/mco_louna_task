from faststream import AckPolicy, Depends
from faststream.rabbit import RabbitMessage, RabbitRouter
from faststream.rabbit.annotations import RabbitBroker

from payments.application.handlers.events.process import ProcessPayment
from payments.domain.enums.task_status import TaskStatus
from payments.infrastructure.broker.event_bus import AMQPEventPublisher
from payments.infrastructure.broker.routes import (
    dlq,
    new_payments_q,
    payments_dlx,
    payments_exchange,
)
from payments.infrastructure.database.uow import PaymentsUoWSQLAlchemy
from payments.presentation.ampq.api.v1.dependencies.commands import (
    process_payment_command,
)
from payments.presentation.ampq.api.v1.dependencies.infra.broker import (
    get_broker,
    get_event_bus,
)
from payments.presentation.ampq.api.v1.dependencies.infra.database import get_uow
from payments.presentation.ampq.api.v1.schemas.payment import (
    NewPaymentEvent,
    new_pay_to_domain,
)
from shared.domain.errors import DomainBusinessRuleError
from shared.infra.broker.utils.retry_queue import create_retry_queues

process_router = RabbitRouter()

DELAY_BASE = 5  # in seconds for exponential-time retries
MAX_ATTEMPTS = 3  # max retty_attempts


retry_routing_queues = create_retry_queues(
    after_expire_exch=payments_exchange,
    base_queue=new_payments_q,
    retry_base=DELAY_BASE,
    max_attempt=MAX_ATTEMPTS,
)


@process_router.subscriber(
    queue=new_payments_q, exchange=payments_exchange, ack_policy=AckPolicy.MANUAL
)
async def handle_payment_processing(
    msg: RabbitMessage,
    uc: ProcessPayment = Depends(process_payment_command),
    uow: PaymentsUoWSQLAlchemy = Depends(get_uow),
    broker: RabbitBroker = Depends(get_broker),
    event_bus: AMQPEventPublisher = Depends(get_event_bus),
) -> None:
    """Handler for processing new payment events."""

    processed_event = NewPaymentEvent.model_validate_json(msg.body)
    # pyrefly: ignore [bad-argument-type]
    event = new_pay_to_domain(processed_event)

    headers = msg.headers or {}
    attempt = headers.get("x-attempt", 0)

    async with uow:
        claimed = await uow.outbox.mark_in_process(event.id)
    if claimed or attempt > 0 and attempt < MAX_ATTEMPTS:
        try:
            await uc(
                event=event,
                uow=uow,
                event_bus=event_bus,
            )

            async with uow:
                await uow.outbox.mark_processed(
                    # pyrefly: ignore [bad-argument-type]
                    event.id,
                    # pyrefly: ignore [bad-argument-type]
                    upd_status=TaskStatus.CONFIRMED,
                )
                await uow.commit()

        except DomainBusinessRuleError as e:
            # Already processed
            if e == DomainBusinessRuleError("Already processed"):
                pass

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
                        # pyrefly: ignore [bad-argument-type]
                        event_id=event.id,
                        # pyrefly: ignore [bad-argument-type]
                        upd_status=TaskStatus.FAILED,
                    )
                    await uow.commit()

                await broker.publish(
                    msg.body,
                    exchange=payments_dlx,
                    queue=dlq,
                )

    await msg.ack()
