from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from structlog import get_logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from payments.application.interfaces.event_publisher import (
    EventRoutingError,
    EventSerializationError,
    PaymentEventBus,
    PublisherUnavailableError,
)
from payments.application.interfaces.uow import (
    PaymentUoW,
    RepositoriesExhaustedError,
    RepositoriesUnavailableError,
)
from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus
from payments.domain.payment import Payment
from payments.domain.service import PaymentService
from payments.domain.value_objects.amount import Amount
from payments.domain.value_objects.description import Description
from payments.domain.value_objects.key import IdempotencyKey
from payments.domain.value_objects.metadata import Metadata
from payments.domain.value_objects.webhook import WebhookUrl


@dataclass(frozen=True, slots=True, kw_only=True)
class CreatePaymentCommand:
    """
    DTO Command to create new payment instance
    """

    amount: Decimal
    currency: Currency
    key: UUID
    description: str
    metadata: dict[str, Any]
    webhook_url: str


logger = get_logger()


@retry(  # COMMENT TO SWITCH OFF RETRY LOGIC TO DATABASE
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(
        (
            RepositoriesExhaustedError,
            RepositoriesUnavailableError,
        )
    ),
    reraise=True,
)
class CreatePaymentUseCase:
    """
    Creates a new payment aggregate with idempotency guarantees.

    Flow:
        1. Convert command DTO to value objects
        2. Create Payment aggregate (idempotency check via key)
        3. Extract events, add to outbox, commit transaction
        4. Publish events to event bus (outside transaction)
        5. Return response DTO

    If event publishing fails, events remain in outbox for async retry.
    """

    async def __call__(
        self,
        command: CreatePaymentCommand,
        uow: PaymentUoW,
        event_bus: PaymentEventBus,
    ) -> "CreatePaymentResponse":
        """
        Execute payment creation.
        Args:
            command: CreatePaymentCommand
            uow: PaymentUoW (caller opens transaction)
            event_bus: PaymentEventBus for external notifications
        Returns:
            CreatePaymentResponse
        Raises:
            PublisherUnavailableError, EventRoutingError, EventSerializationError
        """

        # Building value objects from command DTO
        amount = Amount(command.amount)
        currency = command.currency
        key = IdempotencyKey(command.key)
        descr = Description(command.description)
        metadata = Metadata(command.metadata)
        webhook = WebhookUrl(command.webhook_url)

        async with uow:
            # Creating new payment with idempotency-check
            service = PaymentService(repo=uow.payments)
            payment = await service.create(
                amount=amount,
                key=key,
                currency=currency,
                metadata=metadata,
                webhook_url=webhook,
                description=descr,
            )

            # events
            events = payment.pull_events()
            await uow.outbox.add(events)
            await uow.commit()

        try:
            await event_bus.publish_payment_events(events)
        except PublisherUnavailableError:
            logger.warning("publisher_unavailable_events_in_outbox")
            raise
        except EventRoutingError:
            logger.error("Routing misconfigured")
            raise
        except EventSerializationError:
            logger.error("event_serialization_failed")
            raise

        return CreatePaymentResponse.from_domain(payment)


@dataclass(frozen=True, slots=True, kw_only=True)
class CreatePaymentResponse:
    """
    Response DTO on successful payment creation.

    Attributes:
        payment_id: Unique payment identifier (str)
        status: Current payment status (PaymentStatus)
        created_at: Server timestamp (datetime)
    """

    payment_id: str
    status: PaymentStatus
    created_at: datetime

    @classmethod
    def from_domain(cls, payment: Payment):
        return cls(
            payment_id=str(payment.id.value),
            status=payment.status,
            created_at=payment.created_at.value,
        )
