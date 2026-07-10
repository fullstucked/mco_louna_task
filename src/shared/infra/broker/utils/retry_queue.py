from faststream.rabbit import RabbitExchange
from faststream.rabbit import QueueType
from faststream.rabbit import RabbitQueue


def create_retry_queues(
    base_queue: RabbitQueue,
    after_expire_exch: RabbitExchange,
    retry_base: int = 5,
    max_attempt: int = 3,
) -> list[RabbitQueue]:
    """
    Creates instances of Rabbit dead queue
    with exponential timeout retries
    """

    return [
        RabbitQueue(
            name=f"payments.{base_queue.routing_key}.retry.{retry_base * 2**attempt}s",
            routing_key=f"{base_queue.routing_key}.retry.{retry_base * 2**attempt}s",
            durable=True,
            queue_type=QueueType.QUORUM,
            arguments={
                "x-message-ttl": 1000 * retry_base * 2**attempt,
                "x-dead-letter-exchange": after_expire_exch.name,
                "x-dead-letter-routing-key": base_queue.routing_key,
                "x-overflow": "reject-publish",
                "x-dead-letter-strategy": "at-least-once",
            },
        )
        for attempt in range(1, max_attempt + 1)
    ]
