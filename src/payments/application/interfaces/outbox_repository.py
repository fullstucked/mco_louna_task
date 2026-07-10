from abc import ABC, abstractmethod
from typing import Iterable
from uuid import UUID

from payments.domain.enums.status import PaymentStatus
from payments.domain.events import PaymentDomainEvent


class PaymentEventRepository(ABC):
    """Event presistance abstraction for Payment entity"""

    @abstractmethod
    async def get_pendings(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PaymentDomainEvent] | None:
        """
        Fetch last pending events with pagination
        """
        raise NotImplementedError

    @abstractmethod
    async def add(self, events: Iterable[PaymentDomainEvent]) -> None:
        """
        Saves new Payment event
        """
        raise NotImplementedError

    @abstractmethod
    async def mark_processed(self, event_id: UUID, upd_status: PaymentStatus) -> None:
        """
        Mark event as done
        """
        raise NotImplementedError

    @abstractmethod
    async def mark_in_process(self, event_id: UUID) -> bool:
        raise NotImplementedError
