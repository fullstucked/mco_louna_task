from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from payments.infrastructure.notifications.httpx_sender import HttpxWebhookSender


@pytest.fixture
def sender():
    return HttpxWebhookSender()


def create_mock_httpx_client(status_code=200, side_effect=None):
    """Factory function that creates fresh mocks with custom config."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = status_code

    if side_effect:
        mock_client.post = AsyncMock(side_effect=side_effect)
    else:
        mock_client.post = AsyncMock(return_value=mock_response)

    context_manager = AsyncMock()
    context_manager.__aenter__ = AsyncMock(return_value=mock_client)
    context_manager.__aexit__ = AsyncMock(return_value=None)

    return context_manager, mock_client, mock_response


class TestHttpxWebhookSender:

    @pytest.mark.asyncio
    async def test_send_posts_payload_as_json(self, sender):
        """Verify send() POSTs payload to URL with JSON content-type."""
        context_manager, mock_client, _ = create_mock_httpx_client()
        url = "https://webhook.example.com/payments"
        payload = {"payment_id": "uuid-123", "amount": "99.99"}

        with patch(
            "payments.infrastructure.notifications.httpx_sender.httpx.AsyncClient",
            return_value=context_manager,
        ):
            await sender.send(url, payload)

        mock_client.post.assert_called_once_with(url, json=payload)

    @pytest.mark.asyncio
    async def test_send_applies_timeout(self, sender):
        """Verify send() creates client with specified timeout."""
        context_manager, _, _ = create_mock_httpx_client()

        with patch(
            "payments.infrastructure.notifications.httpx_sender.httpx.AsyncClient",
        ) as mock_async_client:
            mock_async_client.return_value = context_manager
            await sender.send("https://example.com", {}, timeout=10)

        mock_async_client.assert_called_once_with(timeout=10)

    @pytest.mark.asyncio
    async def test_send_succeeds_on_200_response(self, sender):
        """Verify send() completes without error on 2xx status."""
        context_manager, _, _ = create_mock_httpx_client(status_code=200)

        with patch(
            "payments.infrastructure.notifications.httpx_sender.httpx.AsyncClient",
            return_value=context_manager,
        ):
            await sender.send("https://example.com", {"key": "value"})

    @pytest.mark.asyncio
    async def test_send_succeeds_on_201_response(self, sender):
        """Verify send() handles 201 Created response."""
        context_manager, _, _ = create_mock_httpx_client(status_code=201)

        with patch(
            "payments.infrastructure.notifications.httpx_sender.httpx.AsyncClient",
            return_value=context_manager,
        ):
            await sender.send("https://example.com", {})

    @pytest.mark.asyncio
    async def test_send_raises_on_400_client_error(self, sender):
        """Verify send() raises on 4xx status codes."""
        context_manager, _, _ = create_mock_httpx_client(status_code=400)

        with patch(
            "payments.infrastructure.notifications.httpx_sender.httpx.AsyncClient",
            return_value=context_manager,
        ):
            with pytest.raises(NotImplementedError) as exc_info:
                await sender.send("https://example.com", {})

            assert "Client error: 400" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_raises_on_404_not_found(self, sender):
        """Verify send() raises on 404."""
        context_manager, _, _ = create_mock_httpx_client(status_code=404)

        with patch(
            "payments.infrastructure.notifications.httpx_sender.httpx.AsyncClient",
            return_value=context_manager,
        ):
            with pytest.raises(NotImplementedError) as exc_info:
                await sender.send("https://example.com", {})

            assert "Client error: 404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_raises_on_500_server_error(self, sender):
        """Verify send() raises on 5xx status codes."""
        context_manager, _, _ = create_mock_httpx_client(status_code=500)

        with patch(
            "payments.infrastructure.notifications.httpx_sender.httpx.AsyncClient",
            return_value=context_manager,
        ):
            with pytest.raises(NotImplementedError) as exc_info:
                await sender.send("https://example.com", {})

            assert "Server error: 500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_raises_on_502_bad_gateway(self, sender):
        """Verify send() raises on 502."""
        context_manager, _, _ = create_mock_httpx_client(status_code=502)

        with patch(
            "payments.infrastructure.notifications.httpx_sender.httpx.AsyncClient",
            return_value=context_manager,
        ):
            with pytest.raises(NotImplementedError) as exc_info:
                await sender.send("https://example.com", {})

            assert "Server error: 502" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_raises_on_timeout(self, sender):
        """Verify send() raises on httpx.TimeoutException and chains it."""
        context_manager, _, _ = create_mock_httpx_client(
            side_effect=httpx.TimeoutException("Connection timed out")
        )

        with patch(
            "payments.infrastructure.notifications.httpx_sender.httpx.AsyncClient",
            return_value=context_manager,
        ):
            with pytest.raises(NotImplementedError) as exc_info:
                await sender.send("https://example.com", {})

            assert "Timeout" in str(exc_info.value)
            assert exc_info.value.__cause__ is not None
            assert isinstance(exc_info.value.__cause__, httpx.TimeoutException)

    @pytest.mark.asyncio
    async def test_send_raises_on_network_error(self, sender):
        """Verify send() raises on httpx.RequestError."""
        context_manager, _, _ = create_mock_httpx_client(
            side_effect=httpx.RequestError("Connection refused")
        )

        with patch(
            "payments.infrastructure.notifications.httpx_sender.httpx.AsyncClient",
            return_value=context_manager,
        ):
            with pytest.raises(NotImplementedError) as exc_info:
                await sender.send("https://example.com", {})

            assert "Network error" in str(exc_info.value)
            assert isinstance(exc_info.value.__cause__, httpx.RequestError)

    @pytest.mark.asyncio
    async def test_send_closes_client_context(self, sender):
        """Verify send() properly exits AsyncClient context manager."""
        context_manager, _, _ = create_mock_httpx_client()

        with patch(
            "payments.infrastructure.notifications.httpx_sender.httpx.AsyncClient",
            return_value=context_manager,
        ):
            await sender.send("https://example.com", {})

        assert context_manager.__aexit__.called

    @pytest.mark.asyncio
    async def test_send_uses_default_timeout_of_5_seconds(self, sender):
        """Verify send() defaults to 5 second timeout."""
        context_manager, _, _ = create_mock_httpx_client()

        with patch(
            "payments.infrastructure.notifications.httpx_sender.httpx.AsyncClient",
        ) as mock_async_client:
            mock_async_client.return_value = context_manager
            await sender.send("https://example.com", {})

        mock_async_client.assert_called_once_with(timeout=5)
