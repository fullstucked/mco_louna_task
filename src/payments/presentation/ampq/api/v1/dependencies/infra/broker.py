from fast_depends import Depends
import os

from faststream.rabbit import RabbitBroker

from payments.infrastructure.broker.event_bus import AMQPEventPublisher


def get_broker():
    return RabbitBroker(
        url=os.getenv("BROKER_URL"),
    )


async def get_event_bus(broker=Depends(get_broker)):
    await broker.connect()
    return AMQPEventPublisher(broker=broker)
