from payments.application.interfaces.outbox_repository import PaymentEventRepository
from payments.domain.repository import PaymentRepository
from shared.application.interfaces.uow import AbstractUnitOfWork


class PaymentUoW(AbstractUnitOfWork):
    """
    Unit of Work for payment domain operations.

    Coordinates transactional boundaries and repository access for all payment-related
    operations. Implements the Unit of Work pattern to provide:
    - Atomic transactions: Multiple repository operations succeed or fail together
    - Explicit transaction control: Commit/rollback are called explicitly, not on context exit
    - Consistent aggregate management: Single source of truth for payment data access
    - Event persistence: Domain events are captured alongside aggregate state changes
    Repositories:
        payments: PaymentRepository
            Repository for accessing and modifying Payment aggregates.
            Handles:
            - Creating new payments (PaymentAggregate instances)
            - Retrieving payments by ID or filtering criteria
            - Persisting payment state changes to the database
        outbox: PaymentEventRepository
            Repository for managing payment domain events using the outbox pattern.
            Handles:
            - Persisting domain events emitted by Payment aggregates
            - Tracking event processing state (PENDING → IN_PROCESS → PROCESSED)
            - Enabling event processors to reliably deliver events to external systems
              (webhooks, message queues, audit logs, etc.)
    Transaction Lifecycle:
        1. UoW is created and entered as an async context manager
        2. Application logic calls methods on payment and outbox repositories
        3. Aggregates emit domain events (e.g., PaymentProcessedEvent)
        4. Events are added to outbox via outbox.add()
        5. Payment state is persisted via payments.save()
        6. Application explicitly calls uow.commit() to finalize transaction
           - All changes (aggregates + events) are committed atomically
           - If commit succeeds, external processors can safely begin event delivery
        7. If an error occurs before commit(), application calls uow.rollback()
           - All uncommitted changes are discarded
           - External processors never see incomplete state
    """

    payments: PaymentRepository
    outbox: PaymentEventRepository
