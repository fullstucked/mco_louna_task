from abc import ABC, abstractmethod


class WebhookUrlInvalidError(Exception):
    """
    Raised when the webhook URL is invalid or malformed.

    This occurs when:
    - URL protocol is not supported (not http/https)

    Application layer response: Configuration error, should not send.
    """

    pass


class WebhookPayloadError(Exception):
    """
    Raised when the webhook payload is invalid or cannot be serialized.

    This occurs when:
    - Payload contains non-serializable objects
    - JSON encoding fails
    - Payload is too large

    Application layer response: Data validation error, retry may not help.
    """

    pass


class WebhookSenderUnavailableError(Exception):
    """
    Raised when the webhook sender is unavailable.

    This occurs when:
    - HTTP connection timeout
    - Webhook endpoint is down (5xx errors)
    - Network error or connection refused
    - Circuit breaker is open (too many failures)
    - Rate limited (429) and retries exhausted

    Application layer response: Retry later, store in outbox if critical.
    """

    pass


class WebhookSender(ABC):
    """
    Port: Interface for sending webhooks to external URLs.
    """

    @abstractmethod
    async def send(
        self,
        url: str,
        payload: dict[str, str],
        timeout: int = 5,
    ) -> None:
        """
        Send a webhook to the specified URL with the given payload.

        Args:
            url: Webhook endpoint URL (must be valid http/https)
            payload: JSON-serializable payload dictionary
            timeout: Request timeout in seconds (default 5)

        Raises:
            WebhookUrlInvalidError: URL is malformed or invalid.
            WebhookPayloadError: Payload cannot be serialized.
            WebhookSenderUnavailableError: Webhook endpoint unreachable or down.
        """
        raise NotImplementedError
