import json
from typing import Iterable

import aio_pika
from faststream.rabbit.annotations import RabbitBroker

from payments.application.interfaces.event_publisher import PaymentEventBus
from payments.domain.events import PaymentDomainEvent
from payments.infrastructure.broker.routes import (
    EXCHANGE_REGISTRY,
    QUEUE_REGISTRY,
    dlq,
    payments_dlx,
)
from payments.infrastructure.utils.events.serializer import serialize_event


class AMQPEventPublisher(PaymentEventBus):
    """Event publisher for publishing domain events to RabbitMQ."""

    def __init__(self, broker: RabbitBroker) -> None:
        self.broker = broker  # SHOULD BE CONNECTED BEFORE

    async def publish_payment_events(
        self, events: Iterable[PaymentDomainEvent]
    ) -> None:
        """
        Publish event to RabbitMQ.
        routing and exchange via [QUEUE/EXCHANGE]_REGISTRY
        """
        for event in events:
            try:
                message = self._parse_event_to_message(event)
                await self.broker.publish(
                    message=message,
                    routing_key=QUEUE_REGISTRY[type(event)].routing_key,
                    exchange=EXCHANGE_REGISTRY[type(event)],
                )
            except KeyError as e:

                message = self._parse_event_to_message(event)
                await self.broker.publish(
                    message=message,
                    routing_key=dlq.routing_key,
                    exchange=payments_dlx,
                )
                raise ValueError(f"Event routing not configured for {e}")

            except Exception as e:
                raise e

    def _parse_event_to_message(self, event: PaymentDomainEvent) -> aio_pika.Message:
        """
        Helper which translate event content to actual message
        """

        serialized = serialize_event(event, convert_to_iso=True)
        message_body = json.dumps(serialized)

        message = aio_pika.Message(
            body=message_body.encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        return message
