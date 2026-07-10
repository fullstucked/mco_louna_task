from typing import Annotated

from fastapi import Depends, Request

from payments.infrastructure.broker.event_bus import AMQPEventPublisher


def get_broker(request: Request):
    return request.app.state.broker


def get_publisher(
    broker=Depends(get_broker),
):
    return AMQPEventPublisher(broker)


PublisherDep = Annotated[
    AMQPEventPublisher,
    Depends(get_publisher),
]
