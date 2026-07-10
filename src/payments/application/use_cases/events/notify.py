from payments.application.interfaces.notifier import WebhookSender
from payments.domain.enums.status import PaymentStatus
from payments.domain.events import PaymentProcessedEvent


class SendNotificationUseCase:

    async def __call__(
        self,
        notifier: WebhookSender,
        event: PaymentProcessedEvent,
        timeout=5,
    ) -> None:

        if event.status != PaymentStatus.CONFIRMED:
            payload = {
                "payment_id": str(event.payment_id),
                "status": event.status.value,
                "reason": event.reason if event.reason else "Internal error",
            }
        else:
            payload = {
                "payment_id": str(event.payment_id),
                "status": event.status.value,
                "amount": str(event.amount),
                "currency": event.currency.value,
            }

        await notifier.send(
            url=event.webhook_url,
            payload=payload,
            timeout=timeout,
        )
