import json
from typing import Iterable

import aio_pika
from faststream.rabbit import RabbitExchange
from faststream.rabbit.annotations import RabbitBroker
from pybreaker import CircuitBreaker, CircuitBreakerError
from structlog import get_logger

from payments.application.interfaces.event_publisher import (
    EventRoutingError,
    EventSerializationError,
    PaymentEventBus,
    PublisherUnavailableError,
)
from payments.domain.events import PaymentDomainEvent
from payments.infrastructure.broker.routes import (
    EXCHANGE_REGISTRY,
    QUEUE_REGISTRY,
)
from payments.infrastructure.utils.events.serializer import serialize_event

logger = get_logger()


class AMQPEventPublisher(PaymentEventBus):
    """Event publisher for publishing domain events to RabbitMQ."""

    def __init__(self, broker: RabbitBroker) -> None:
        self.broker = broker
        self.breaker = CircuitBreaker(
            fail_max=5,
            reset_timeout=60,
            exclude=[EventRoutingError, EventSerializationError],
            name="amqp_event_publisher",
        )

    async def publish_payment_events(
        self, events: Iterable[PaymentDomainEvent]
    ) -> None:
        """
        Publish events to RabbitMQ one-by-one under circuit breaker protection.

        Raises:
            PublisherUnavailableError: Broker is down or circuit is open.
            EventRoutingError: Event type has no routing configured.
            EventSerializationError: Event cannot be serialized.
        """
        for event in events:
            event_type = type(event).__name__
            event_id = getattr(event, "id", None)

            # Validate routing
            try:
                queue_config = QUEUE_REGISTRY[type(event)]
                exchange = EXCHANGE_REGISTRY[type(event)]
            except KeyError:
                logger.error(
                    "event_routing_not_configured",
                    event_type=event_type,
                    event_id=event_id,
                )
                raise EventRoutingError(
                    f"Event routing not configured for {event_type}"
                )

            # Serialize
            try:
                message = self._parse_event_to_message(event)
            except (TypeError, ValueError) as e:
                logger.error(
                    "event_serialization_failed",
                    event_type=event_type,
                    event_id=event_id,
                    error=str(e),
                )
                raise EventSerializationError(
                    f"Cannot serialize event {event_type}: {e}"
                )

            try:
                await self.breaker.call(
                    self._broker_publish,
                    message=message,
                    routing_key=queue_config.routing_key,
                    exchange=exchange,
                )
                logger.info(
                    "event_published",
                    event_type=event_type,
                    event_id=event_id,
                )
            except CircuitBreakerError:
                logger.error(
                    "event_publisher_circuit_open",
                    event_type=event_type,
                    event_id=event_id,
                )
                raise PublisherUnavailableError("Event publisher circuit is open")
            except (aio_pika.exceptions.AMQPError, Exception) as e:
                logger.error(
                    "event_publish_failed",
                    event_type=event_type,
                    event_id=event_id,
                    error=str(e),
                )
                raise PublisherUnavailableError(f"Failed to publish {event_type}: {e}")

    async def _broker_publish(
        self,
        message: aio_pika.Message,
        routing_key: str,
        exchange: RabbitExchange,
    ) -> None:
        """Actual AMQP publish call (wrapped by circuit breaker)."""
        await self.broker.publish(
            message=message,
            routing_key=routing_key,
            exchange=exchange,
        )

    def _parse_event_to_message(self, event: PaymentDomainEvent) -> aio_pika.Message:
        """
        Helper which translate event content to actual message.

        Raises:
            ValueError, TypeError: If serialization fails.
        """
        serialized = serialize_event(event, convert_to_iso=True)
        message_body = json.dumps(serialized)

        message = aio_pika.Message(
            body=message_body.encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        return message
