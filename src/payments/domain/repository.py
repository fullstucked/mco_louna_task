from abc import ABC, abstractmethod

from payments.domain.payment import Payment
from payments.domain.value_objects.id import PaymentID
from payments.domain.value_objects.key import IdempotencyKey


class PaymentRepository(ABC):
    """
    Abstract repository interface for Payment persistence and retrieval.
    Defines the contract between the domain layer and persistence infrastructure.

    Methods:
        add() -> None
            Save a new Payment record.
        get_by_id() -> Payment
            Retrieve a Payment by its unique PaymentID.
        get_by_key() -> Payment | None
            Retrieve a Payment by its idempotency key (for deduplication).
        update() -> None
            Update an existing Payment record with new state.
    """

    @abstractmethod
    async def add(self, payment: Payment) -> None:
        """
        Save a newly created Payment aggregate to persistent storage.
        Args:
            payment: Payment
                The new Payment aggregate to persist. Should be a freshly
                created Payment instance that has not yet been saved.
        Returns:
            None
        Raises:
            DomainResourceExistsError
                at attempt to create payment wiht existing IdempotencyKey
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, payment_id: PaymentID) -> Payment:
        """
        Retrieve a Payment aggregate by its ID.
        Reconstructs the Payment from persistent storage.
        Args:
            payment_id: PaymentID
                The unique identifier of the payment to retrieve.
        Returns:
            Payment
                The reconstructed Payment aggregate with current state.
        Raises:
            DomainResourceNotFoundError
                If no payment with the given ID exists in storage.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_key(self, key: IdempotencyKey) -> Payment | None:
        """
        Retrieve a Payment by its idempotency key (optional, for deduplication).
        Args:
            key: IdempotencyKey
                The idempotency key (UUID v4).
        Returns:
            Payment | None
                The existing Payment if found; None if no payment with this
                key exists (indicating the request is new).
        """
        raise NotImplementedError

    @abstractmethod
    async def update(self, payment: Payment) -> None:
        """
        Update an existing Payment record with new state.
        Args:
            payment: Payment
                The Payment aggregate with updated state to persist.
                Should be an existing payment (already saved via add())
                that has been modified.
        Returns:
            None
        Raises:
            DomainResourceNotFoundError
                When updating payment does not exists(ID)
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
