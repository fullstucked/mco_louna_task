from payments.domain.enums.currency import Currency
from payments.domain.payment import Payment
from payments.domain.repository import PaymentRepository
from payments.domain.value_objects.amount import Amount
from payments.domain.value_objects.description import Description
from payments.domain.value_objects.key import IdempotencyKey
from payments.domain.value_objects.metadata import Metadata
from payments.domain.value_objects.webhook import WebhookUrl
from shared.domain.errors import DomainResourceExistsError


class PaymentService:
    """
    Domain service orchestrating payment creation, processing, and persistence.

    Combines repository access with domain rules and event handling to provide
    high-level payment operations. Acts as the primary entry point for payment
    business logic, enforcing idempotency and coordinating with infrastructure.

    Responsibilities:
        - Create new payments with idempotency checks
        - Update payment status after processing by gateway
        - Emit and persist domain events
        - Enforce business rules (e.g., no duplicate payments)
    Args:
        repo: PaymentRepository
            The persistence layer for loading and saving payments.
    Attributes:
        repo: PaymentRepository
            Reference to the repository for payment I/O.
    Methods:
        create() -> Payment
            Create and persist a new payment with idempotency.
        update_processed_payment() -> Payment
            Update payment state after gateway processing and persist.
    """

    def __init__(self, repo: PaymentRepository):
        self.repo: PaymentRepository = repo

    async def create(
        self,
        amount: Amount,
        currency: Currency,
        description: Description,
        metadata: Metadata,
        key: IdempotencyKey,
        webhook_url: WebhookUrl,
    ) -> Payment:
        """
        Create a new payment with automatic idempotency deduplication.

        Checks if a payment with the given idempotency key already exists.
        Args:
            amount: Amount
                The monetary amount to charge (must be positive, ≤ 2 decimal places).
            currency: Currency
                The currency of the transaction (RUB, USD, EUR).
            description: Description
                A human-readable description of the payment (3-50 chars, no control chars).
            metadata: Metadata
                Optional JSON-serializable metadata
            key: IdempotencyKey
                UUID v4 for deduplication.
            webhook_url: WebhookUrl
                The endpoint to POST payment status updates to after processing.

        Returns:
            Payment
                The newly created Payment aggregate, persisted in the repository.

        Raises:
            DomainResourceExistsError
                If a payment with the given idempotency key already exists.
        """

        payment_exists = await self.repo.get_by_key(key)

        # or replace with same request same result logic
        if payment_exists:
            raise DomainResourceExistsError(message="Payment already exists")

        payment = Payment(
            amount=amount,
            currency=currency,
            description=description,
            metadata=metadata,
            key=key,
            webhook_url=webhook_url,
        )
        await self.repo.add(payment)

        return payment

    async def update_processed_payment(self, payment: Payment) -> Payment:
        """
        Update a payment after processing by the payment gateway.

        Persists status changes and processing metadata (e.g., processed_at timestamp,
        final status CONFIRMED/FAILED, failure reason) to the repository. This method
        is called after the payment gateway returns a processing result.
        Args:
            payment: Payment
                An existing Payment aggregate that has been processed and updated
                with new status and timing information.
        Returns:
            Payment
                The updated Payment aggregate (same instance as input).
        Raises
            DomainResourrceNotFoundError(internal)
        """
        await self.repo.update(payment=payment)
        return payment
