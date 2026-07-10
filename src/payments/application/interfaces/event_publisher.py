from abc import ABC, abstractmethod
from typing import Iterable

from payments.domain.events import PaymentDomainEvent


class PaymentEventBus(ABC):
    """Interface for event publisher to publish domain events."""

    @abstractmethod
    async def publish_payment_events(
        self, events: Iterable[PaymentDomainEvent]
    ) -> None:
        """Publish multiple events in order."""
        raise NotImplementedError
