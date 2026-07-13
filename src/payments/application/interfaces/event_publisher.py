from abc import ABC, abstractmethod
from typing import Iterable

from payments.domain.events import PaymentDomainEvent


class PublisherUnavailableError(Exception):
    """
    Raised when the event publisher is unavailable.

    This occurs when:
    - The broker  is down or unreachable
    - Circuit breaker is open (too many failures)
    - Connection timeout or network error

    Application layer response: Events are in outbox for later retry.
    """

    pass


class EventRoutingError(Exception):
    """
    Raised when event routing is not configured.

    This occurs when:
    - Event type has no configured queue/exchange
    - Routing configuration is missing

    Application layer response: Configuration error.
    """

    pass


class EventSerializationError(Exception):
    """
    Raised when an event cannot be serialized to a message.

    This occurs when:
    - Event has non-serializable fields
    - JSON encoding fails

    Application layer response: Log error and dead-letter event.
    """

    pass


class PaymentEventBus(ABC):
    """Interface for event publisher to publish domain events."""

    @abstractmethod
    async def publish_payment_events(
        self, events: Iterable[PaymentDomainEvent]
    ) -> None:
        """
        Publish multiple events in order.
        Raises:
            PublisherUnavailableError: Broker is down or unavailable.
            EventRoutingError: Event type has no routing configured.
            EventSerializationError: Event cannot be serialized.
        """
        raise NotImplementedError
