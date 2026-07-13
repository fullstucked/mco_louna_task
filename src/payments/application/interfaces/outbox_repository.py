from payments.domain.enums.task_status import TaskStatus
from abc import ABC, abstractmethod
from typing import Iterable
from uuid import UUID

from payments.domain.events import PaymentDomainEvent


class PaymentEventRepository(ABC):
    """
    Application-layer repository for persisting and tracking payment domain events.

    This repository implements event sourcing and the outbox pattern, enabling:
    - Durable capture of all payment state changes as immutable events
    - Exactly-once delivery semantics through event processing state tracking
    - Event replay and audit trails
    Event Lifecycle:
        1. Events are created by domain aggregates (PaymentCreatedEvent, PaymentProcessedEvent)
        2. add() persists them to storage in PENDING state
        3. Event processors poll get_pendings() for unprocessed events
        4. mark_in_process() atomically transitions event to IN_PROCESS (prevents duplicates)
        5. Event processor executes the event (sends webhook, emits to message queue, etc.)
        6. mark_processed() updates event status to match the final payment status
    Concurrency Safety:
        - mark_in_process() uses optimistic or pessimistic locking to ensure a single
          processor handles each event (preventing duplicate webhooks/notifications)
        - Multiple processors can safely poll and process events concurrently
    Pagination:
        - get_pendings() returns events in batches (limit, offset) for scalability
        - Prevents memory exhaustion when thousands of events are pending
        - Processors should repeatedly call get_pendings() until empty
    Methods:
        get_pendings() -> list[PaymentDomainEvent] | None
            Retrieve unprocessed events with pagination.
        add() -> None
            Persist newly emitted domain events.
        mark_processed() -> None
            Mark an event as successfully processed with final status.
        mark_in_process() -> bool
            Atomically claim an event for processing (prevents duplicate handlers).
    """

    @abstractmethod
    async def get_pendings(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PaymentDomainEvent]:
        """
        Retrieve unprocessed domain events with pagination.

        Fetches events in PENDING state that have not yet been
        successfully handled by event processors.
        Pagination allows processing events in batches, preventing memory exhaustion
        when large numbers of events accumulate.
        Args:
            limit: int = 50
                Maximum number of events to return per call.
                Adjust based on:
                - Available memory and CPU for processing
                - Network bandwidth
                - Desired latency (smaller batches = more frequent polls)
                Typical values: 10-100 events per batch.
            offset: int = 0
                Number of events to skip (for pagination).
        Returns:
            list[PaymentDomainEvent] | None
                List of unprocessed events, ordered by creation timestamp (oldest first).
                Returns None or empty list if no pending events exist.
                May return fewer than `limit` events if fewer are available.
        Raises:
            Implementations may raise storage-specific exceptions
        Ordering:
            Events are returned in FIFO order (oldest first) to ensure fair
            processing and preserve causality where possible.
        """
        raise NotImplementedError

    @abstractmethod
    async def add(self, events: Iterable[PaymentDomainEvent]) -> None:
        """
        Persist newly emitted domain events to storage.

        Saves one or more domain events (PaymentCreatedEvent, PaymentProcessedEvent, etc.)
        in PENDING state.
        This method should be called atomically with payment state updates to ensure
        that if the payment is saved, its events are also saved (and vice versa).
        Args:
            events: Iterable[PaymentDomainEvent]
        Returns:
            None
        Raises:
            Implementations may raise storage-specific exceptions
        """
        raise NotImplementedError

    @abstractmethod
    async def mark_processed(self, event_id: UUID, upd_status: TaskStatus) -> None:
        """
        Mark an event as successfully processed with its final status.
        Args:
            event_id: UUID
            upd_status: TaskStatus
                The final payment status associated with this event.
                - TaskStatus.CONFIRMED: Payment was successfully charged
                - TaskStatus.FAILED: Payment processing failed
                - TaskStatus.IN_PROCESS: Task handled
                - TaskStatus.PENDING: (Rare) Event processing deferred
        Returns:
            None
        Raises:
            DomainResourceNotFoundError - when not found event with id=`event_id`
        """
        raise NotImplementedError

    @abstractmethod
    async def mark_in_process(self, event_id: UUID) -> bool:
        """
        Atomically claim an event for processing (concurrent-safe lock).

        Transitions an event from PENDING to IN_PROCESS state in an atomic operation.
        This prevents multiple processors from handling the same event concurrently,
        ensuring exactly-once.
        Returns True if the event was successfully claimed by this processor.
        Returns False if another processor already claimed it (race condition).
        Args:
            event_id: UUID
                The unique identifier of the event to claim for processing.
                Must reference an event in PENDING state.
        Returns:
            bool
                True if event was successfully transitioned to IN_PROCESS.
                False if event is already IN_PROCESS (claimed by another processor)
                or does not exist / is already PROCESSED.
        """
        raise NotImplementedError
