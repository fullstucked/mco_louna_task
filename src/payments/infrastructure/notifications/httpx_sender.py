from payments.application.interfaces.notifier import WebhookSender
import httpx


class HttpxWebhookSender(WebhookSender):
    async def send(self, url: str, payload: dict, timeout: int = 5) -> None:
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(url, json=payload)

                if resp.status_code >= 500:
                    raise NotImplementedError(f"Server error: {resp.status_code}")

                if resp.status_code >= 400:
                    raise NotImplementedError(f"Client error: {resp.status_code}")

            except httpx.TimeoutException as exc:
                raise NotImplementedError("Timeout") from exc

            except httpx.RequestError as exc:
                raise NotImplementedError("Network error") from exc
