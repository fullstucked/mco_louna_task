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
    Combine presistance with domain rules and events
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
        Pre-check existance by indempotency key - if not found
        new Payment created and saving
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
        Wrapper for payment status and process_time updates
        """
        await self.repo.update(payment=payment)
        return payment
