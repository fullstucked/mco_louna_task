from abc import ABC, abstractmethod

from payments.domain.payment import Payment
from payments.domain.value_objects.id import PaymentID
from payments.domain.value_objects.key import IdempotencyKey


class PaymentRepository(ABC):
    """Basic presistance abstraction"""

    @abstractmethod
    async def add(self, payment: Payment) -> None:
        """
        Saves new Payment record
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, payment_id: PaymentID) -> Payment:
        """
        Fetch Payment record by id
        raises `PaymentResourceNotFoundError` if not exists
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_key(self, key: IdempotencyKey) -> Payment | None:
        """
        Fetch Payment record by IdempotencyKey to avoid payment deduplication
        return `None` if not found
        """
        raise NotImplementedError

    @abstractmethod
    async def update(self, payment: Payment) -> None:
        """
        Update processed Payment record, writes processed_at mark
        and update status
        """
        raise NotImplementedError


# # In repo
# async def get_by_id_for_write(self, payment_id: PaymentID) -> Payment:
#     """For commands that will modify"""
#     stmt = select(payments).where(...).with_for_update()
#     ...
#
# async def get_by_id_for_read(self, payment_id: PaymentID) -> Payment:
#     """For queries (no lock needed)"""
#     stmt = select(payments).where(...)
#     ...
