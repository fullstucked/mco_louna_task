import os

from faststream.rabbit import (
    ExchangeType,
    QueueType,
    RabbitBroker,
    RabbitExchange,
    RabbitQueue,
)

from payments.domain.events import (
    PaymentCreatedEvent,
    PaymentDomainEvent,
    PaymentProcessedEvent,
)

broker = RabbitBroker(url=os.getenv("BROKER_URL"))

###
# EXCHANGES
###
EXCHANGE_REGISTRY: dict[type[PaymentDomainEvent], RabbitExchange] = {}


def register_exchange(exch: RabbitExchange, events: list[type[PaymentDomainEvent]]):
    """Registry for group of events with the same `__event_group__`"""
    for event in events:
        EXCHANGE_REGISTRY[event] = exch
    exch.name = event.__event_group__
    return exch


payments_exchange = register_exchange(
    exch=RabbitExchange(
        name=PaymentDomainEvent.__event_group__, type=ExchangeType.TOPIC
    ),
    events=[PaymentDomainEvent, PaymentCreatedEvent, PaymentProcessedEvent],
)

### DEAD SHOULD BE INSTANTIATED DIRECTLY
payments_dlx = RabbitExchange(name="payments.dlx", type=ExchangeType.TOPIC)

###_
# QUEUES
###

QUEUE_REGISTRY: dict[type[PaymentDomainEvent], RabbitQueue] = {}


def register_queue(queue: RabbitQueue, event: type[PaymentDomainEvent]):
    """Registry for future event rebuilds from raw data"""
    queue.routing_key = event.__event_key__
    QUEUE_REGISTRY[event] = queue
    return queue


new_payments_q = register_queue(
    queue=RabbitQueue(
        name="new",
        routing_key=PaymentCreatedEvent.__event_key__,
        durable=True,
        queue_type=QueueType.QUORUM,
    ),
    event=PaymentCreatedEvent,
)


notify_payments_q = register_queue(
    queue=RabbitQueue(
        name="processed",
        routing_key=PaymentProcessedEvent.__event_key__,
        durable=True,
        queue_type=QueueType.QUORUM,
    ),
    event=PaymentProcessedEvent,
)


### DEAD SHOULD BE INSTANTIATED DIRECTLY
dlq = RabbitQueue(name="dead", durable=True, queue_type=QueueType.QUORUM)
