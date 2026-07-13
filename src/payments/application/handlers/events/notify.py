from payments.application.interfaces.notifier import WebhookSenderUnavailableError
from payments.application.interfaces.notifier import WebhookPayloadError
from payments.application.interfaces.notifier import WebhookUrlInvalidError
from structlog import get_logger
from payments.application.interfaces.notifier import WebhookSender
from payments.application.strategies.notification_payload import PayloadStrategyFactory
from payments.domain.events import PaymentProcessedEvent

logger = get_logger()


class SendNotificationUseCase:
    """
    Send webhook notifications for payment status updates.

    Consumes PaymentProcessedEvent, builds status-specific payload via
    strategy pattern, and delivers via WebhookSender interface.
    """

    DEFAULT_TIMEOUT = 5

    def __init__(self, strategy_factory: PayloadStrategyFactory | None = None):
        self.strategy_factory = strategy_factory or PayloadStrategyFactory()

    async def __call__(
        self,
        notifier: WebhookSender,
        event: PaymentProcessedEvent,
        timeout: int | None = None,
    ) -> None:
        """
        Send notification to webhook URL.
        Flow:
            1. Resolve timeout (provided or DEFAULT_TIMEOUT)
            2. Fetch strategy based on event.status
            3. Build payload via strategy.build(event)
            4. Send via notifier.send(url, payload, timeout)
        Args:
            notifier: WebhookSender implementation
            event: PaymentProcessedEvent with status, payment_id, webhook_url
            timeout: Request timeout in seconds (default: 5)
        Raises:
            WebhookUrlInvalidError: Protocol unsupported by notifier
            WebhookPayloadError: Payload structure incompatible with notifier
            WebhookSenderUnavailableError: Network/service unavailable
        """
        timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT

        # Build payload based on payment status
        strategy = self.strategy_factory.get_strategy(event.status)
        payload = strategy.build(event)

        # Send notification
        try:
            await notifier.send(
                url=event.webhook_url,
                payload=payload,
                timeout=timeout,
            )
            #logger.info("payment_confirmation_notified", payment_id=event.payment_id)

        except WebhookUrlInvalidError:
            # Unsupported protocol by implementation for example (Not domain boundary)
            #logger.error("webhook_url_invalid", webhook_url=event.webhook_url)
            raise

        except WebhookPayloadError:
            # Implementation do not supports serialized event
            #logger.error("webhook_payload_invalid", payment_id=event.payment_id)
            raise

        except WebhookSenderUnavailableError:
            #logger.warning(
            #     "webhook_sender_unavailable",
            #     payment_id=event.payment_id,
            #     webhook_url=event.webhook_url,
            # )
            raise
