from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue

from shared.infra.broker.utils.retry_queue import create_retry_queues


async def bind_queues_to_exch(
    broker: RabbitBroker, exch: RabbitExchange, queues: list[RabbitQueue]
):
    """
    Binds queues to exchange
    """
    ch = (await broker.declare_exchange(exch),)

    for queue in queues:
        q = await broker.declare_queue(queue)
        await q.bind(ch[0], routing_key=queue.routing_key)


async def bind_queues_with_retry_to_exch(
    broker: RabbitBroker,
    exch: RabbitExchange,
    dead_exch: RabbitExchange,
    base_queue: RabbitQueue,
    retry_base: int = 5,
    max_attempt: int = 3,
):
    """
    Creates dead retry queues with exponential expiration time;
    after expiration message routes to main exchange+base_queue
    bind base queue and retries to exchange
    """
    # bind base_queue to main related exch
    await bind_queues_to_exch(broker=broker, exch=exch, queues=[base_queue])

    ## create retries routed to dead because they have no any responsability except expire and push new event
    retry_queues = create_retry_queues(
        base_queue=base_queue,
        after_expire_exch=exch,
        retry_base=retry_base,
        max_attempt=max_attempt,
    )
    # binds retries to exchange
    await bind_queues_to_exch(broker=broker, exch=dead_exch, queues=retry_queues)
