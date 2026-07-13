import httpx2 as httpx
import structlog
from pybreaker import CircuitBreaker, CircuitBreakerError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from payments.application.interfaces.notifier import (
    WebhookPayloadError,
    WebhookSender,
    WebhookSenderUnavailableError,
    WebhookUrlInvalidError,
)

logger = structlog.get_logger()


class HttpxWebhookSender(WebhookSender):
    """Webhook sender using httpx with circuit breaker + retries."""

    def __init__(self) -> None:
        self.breaker = CircuitBreaker(
            fail_max=5,
            reset_timeout=60,
            exclude=[WebhookUrlInvalidError, WebhookPayloadError],
            name="httpx_webhook_sender",
        )

    async def send(self, url: str, payload: dict, timeout: int = 5) -> None:
        """
        Send webhook with retries and circuit breaker protection.
        Raises:
            WebhookUrlInvalidError: Malformed or unsupported URL.
            WebhookPayloadError: Serialization failure or 4xx (except 429).
            WebhookSenderUnavailableError: Timeout, 5xx, 429, or circuit open.
        """
        # Validate URL early
        if not url.startswith(("http://", "https://")):
            logger.error("webhook_url_invalid", url=url)
            raise WebhookUrlInvalidError(f"Unsupported URL protocol: {url}")

        # Send with circuit breaker + retries
        try:
            await self.breaker.call(
                self._send_with_retries,
                url=url,
                payload=payload,
                timeout=timeout,
            )
            logger.info("webhook_sent", url=url)
        except CircuitBreakerError:
            logger.error("webhook_sender_circuit_open", url=url)
            raise WebhookSenderUnavailableError(
                "Webhook sender circuit is open"
            ) from None
        except WebhookPayloadError:
            # Pass through application exceptions
            raise
        except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPError) as e:
            logger.error("webhook_send_failed", url=url, error=str(e))
            raise WebhookSenderUnavailableError(f"Failed to send webhook: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.RequestError, httpx.HTTPError)
        ),
        reraise=True,
    )
    async def _send_with_retries(self, url: str, payload: dict, timeout: int) -> None:
        """Send webhook with automatic retries on transient failures."""
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(url, json=payload)

                # 5xx: retryable server error
                if resp.status_code >= 500:
                    raise httpx.HTTPError(f"Server error: {resp.status_code}")

                # 429: rate limited, retryable
                if resp.status_code == 429:
                    raise httpx.HTTPError(f"Rate limited: {resp.status_code}")

                # 4xx (except 429): client's fault, don't retry
                if resp.status_code >= 400:
                    logger.error(
                        "webhook_payload_error",
                        url=url,
                        status_code=resp.status_code,
                    )
                    raise WebhookPayloadError(f"Client error {resp.status_code}")

            except httpx.TimeoutException:
                logger.warning("webhook_timeout", url=url, timeout=timeout)
                raise  # to retry

            except httpx.RequestError as exc:
                logger.warning("webhook_request_error", url=url, error=str(exc))
                raise  # to retry
