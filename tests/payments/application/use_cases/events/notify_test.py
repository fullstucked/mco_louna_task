from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from payments.application.interfaces.notifier import WebhookSender
from payments.application.use_cases.events.notify import SendNotificationUseCase
from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus
from payments.domain.events import PaymentProcessedEvent


class TestSendNotificationUseCase:
    """Tests for SendNotificationUseCase."""

    @pytest.mark.asyncio
    async def test_send_notification_confirmed_status(self):
        """Should send notification with amount and currency when status is CONFIRMED."""
        payment_id = uuid4()
        event = PaymentProcessedEvent(
            payment_id=payment_id,
            status=PaymentStatus.CONFIRMED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason=None,
        )

        mock_notifier = AsyncMock(spec=WebhookSender)
        mock_notifier.send = AsyncMock()

        use_case = SendNotificationUseCase()
        await use_case(notifier=mock_notifier, event=event)

        # Verify send was called with correct payload for CONFIRMED status
        mock_notifier.send.assert_awaited_once()
        call_args = mock_notifier.send.call_args

        assert call_args.kwargs["url"] == "https://example.com/webhook"
        assert call_args.kwargs["payload"] == {
            "payment_id": str(payment_id),
            "status": "CONFIRMED",
            "amount": "100.0",
            "currency": "USD",
        }
        assert call_args.kwargs["timeout"] == 5

    @pytest.mark.asyncio
    async def test_send_notification_failed_status(self):
        """Should send notification with reason when status is FAILED."""
        payment_id = uuid4()
        event = PaymentProcessedEvent(
            payment_id=payment_id,
            status=PaymentStatus.FAILED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason="Insufficient funds",
        )

        mock_notifier = AsyncMock(spec=WebhookSender)
        mock_notifier.send = AsyncMock()

        use_case = SendNotificationUseCase()
        await use_case(notifier=mock_notifier, event=event)

        # Verify send was called with correct payload for FAILED status
        mock_notifier.send.assert_awaited_once()
        call_args = mock_notifier.send.call_args

        assert call_args.kwargs["url"] == "https://example.com/webhook"
        assert call_args.kwargs["payload"] == {
            "payment_id": str(payment_id),
            "status": "FAILED",
            "reason": "Insufficient funds",
        }
        assert call_args.kwargs["timeout"] == 5

    @pytest.mark.asyncio
    async def test_send_notification_failed_status_with_none_reason(self):
        """Should use default reason when status is not CONFIRMED and reason is None."""
        payment_id = uuid4()
        event = PaymentProcessedEvent(
            payment_id=payment_id,
            status=PaymentStatus.FAILED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason=None,
        )

        mock_notifier = AsyncMock(spec=WebhookSender)
        mock_notifier.send = AsyncMock()

        use_case = SendNotificationUseCase()
        await use_case(notifier=mock_notifier, event=event)

        # Verify default reason is used
        call_args = mock_notifier.send.call_args
        assert call_args.kwargs["payload"]["reason"] == "Internal error"

    @pytest.mark.asyncio
    async def test_send_notification_pending_status(self):
        """Should send notification with reason when status is PENDING."""
        payment_id = uuid4()
        event = PaymentProcessedEvent(
            payment_id=payment_id,
            status=PaymentStatus.PENDING,
            webhook_url="https://api.example.com/payment-webhook",
            amount=250.00,
            currency=Currency.EUR,
            reason="Payment processing",
        )

        mock_notifier = AsyncMock(spec=WebhookSender)
        mock_notifier.send = AsyncMock()

        use_case = SendNotificationUseCase()
        await use_case(notifier=mock_notifier, event=event)

        call_args = mock_notifier.send.call_args
        assert call_args.kwargs["payload"] == {
            "payment_id": str(payment_id),
            "status": "PENDING",
            "reason": "Payment processing",
        }

    @pytest.mark.asyncio
    async def test_send_notification_custom_timeout(self):
        """Should use custom timeout when provided."""
        event = PaymentProcessedEvent(
            payment_id=uuid4(),
            status=PaymentStatus.CONFIRMED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason=None,
        )

        mock_notifier = AsyncMock(spec=WebhookSender)
        mock_notifier.send = AsyncMock()

        use_case = SendNotificationUseCase()
        await use_case(notifier=mock_notifier, event=event, timeout=10)

        call_args = mock_notifier.send.call_args
        assert call_args.kwargs["timeout"] == 10

    @pytest.mark.asyncio
    async def test_send_notification_default_timeout(self):
        """Should use default timeout of 5 seconds when not specified."""
        event = PaymentProcessedEvent(
            payment_id=uuid4(),
            status=PaymentStatus.CONFIRMED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason=None,
        )

        mock_notifier = AsyncMock(spec=WebhookSender)
        mock_notifier.send = AsyncMock()

        use_case = SendNotificationUseCase()
        await use_case(notifier=mock_notifier, event=event)

        call_args = mock_notifier.send.call_args
        assert call_args.kwargs["timeout"] == 5

    @pytest.mark.asyncio
    async def test_send_notification_notifier_fails(self):
        """Should propagate notifier exceptions."""
        event = PaymentProcessedEvent(
            payment_id=uuid4(),
            status=PaymentStatus.CONFIRMED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason=None,
        )

        mock_notifier = AsyncMock(spec=WebhookSender)
        mock_notifier.send = AsyncMock(side_effect=Exception("Webhook delivery failed"))

        use_case = SendNotificationUseCase()

        with pytest.raises(Exception, match="Webhook delivery failed"):
            await use_case(notifier=mock_notifier, event=event)

    @pytest.mark.asyncio
    async def test_send_notification_confirmed_with_different_currencies(self):
        """Should handle different currency values in CONFIRMED payload."""
        currencies_to_test = [
            (Currency.USD, "USD"),
            (Currency.EUR, "EUR"),
            (Currency.RUB, "RUB"),
        ]

        for currency, currency_value in currencies_to_test:
            payment_id = uuid4()
            event = PaymentProcessedEvent(
                payment_id=payment_id,
                status=PaymentStatus.CONFIRMED,
                webhook_url="https://example.com/webhook",
                amount=100.00,
                currency=currency,
                reason=None,
            )

            mock_notifier = AsyncMock(spec=WebhookSender)
            mock_notifier.send = AsyncMock()

            use_case = SendNotificationUseCase()
            await use_case(notifier=mock_notifier, event=event)

            call_args = mock_notifier.send.call_args
            assert call_args.kwargs["payload"]["currency"] == currency_value

    @pytest.mark.asyncio
    async def test_send_notification_confirmed_converts_amount_to_string(self):
        """Should convert amount to string in CONFIRMED payload."""
        amounts_to_test = [100.00, 0.01, 1000000.99, 50.5]

        for amount in amounts_to_test:
            event = PaymentProcessedEvent(
                payment_id=uuid4(),
                status=PaymentStatus.CONFIRMED,
                webhook_url="https://example.com/webhook",
                amount=amount,
                currency=Currency.USD,
                reason=None,
            )

            mock_notifier = AsyncMock(spec=WebhookSender)
            mock_notifier.send = AsyncMock()

            use_case = SendNotificationUseCase()
            await use_case(notifier=mock_notifier, event=event)

            call_args = mock_notifier.send.call_args
            assert call_args.kwargs["payload"]["amount"] == str(amount)
            assert isinstance(call_args.kwargs["payload"]["amount"], str)

    @pytest.mark.asyncio
    async def test_send_notification_converts_payment_id_to_string(self):
        """Should convert payment_id UUID to string in payload."""
        payment_id = uuid4()
        event = PaymentProcessedEvent(
            payment_id=payment_id,
            status=PaymentStatus.CONFIRMED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason=None,
        )

        mock_notifier = AsyncMock(spec=WebhookSender)
        mock_notifier.send = AsyncMock()

        use_case = SendNotificationUseCase()
        await use_case(notifier=mock_notifier, event=event)

        call_args = mock_notifier.send.call_args
        assert call_args.kwargs["payload"]["payment_id"] == str(payment_id)
        assert isinstance(call_args.kwargs["payload"]["payment_id"], str)

    @pytest.mark.asyncio
    async def test_send_notification_cancelled_status_with_reason(self):
        """Should send notification with reason for FAILED status."""
        payment_id = uuid4()
        event = PaymentProcessedEvent(
            payment_id=payment_id,
            status=PaymentStatus.FAILED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason="User cancelled payment",
        )

        mock_notifier = AsyncMock(spec=WebhookSender)
        mock_notifier.send = AsyncMock()

        use_case = SendNotificationUseCase()
        await use_case(notifier=mock_notifier, event=event)

        call_args = mock_notifier.send.call_args
        assert call_args.kwargs["payload"]["status"] == "FAILED"
        assert call_args.kwargs["payload"]["reason"] == "User cancelled payment"
        assert "amount" not in call_args.kwargs["payload"]
        assert "currency" not in call_args.kwargs["payload"]

    @pytest.mark.asyncio
    async def test_send_notification_zero_timeout(self):
        """Should handle zero timeout when explicitly provided."""
        event = PaymentProcessedEvent(
            payment_id=uuid4(),
            status=PaymentStatus.CONFIRMED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason=None,
        )

        mock_notifier = AsyncMock(spec=WebhookSender)
        mock_notifier.send = AsyncMock()

        use_case = SendNotificationUseCase()
        await use_case(notifier=mock_notifier, event=event, timeout=0)

        call_args = mock_notifier.send.call_args
        assert call_args.kwargs["timeout"] == 0

    @pytest.mark.asyncio
    async def test_send_notification_status_enum_serialization(self):
        """Should serialize status enum correctly using .value."""
        event = PaymentProcessedEvent(
            payment_id=uuid4(),
            status=PaymentStatus.FAILED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason="Test reason",
        )

        mock_notifier = AsyncMock(spec=WebhookSender)
        mock_notifier.send = AsyncMock()

        use_case = SendNotificationUseCase()
        await use_case(notifier=mock_notifier, event=event)

        call_args = mock_notifier.send.call_args
        # Verify status is serialized as enum value, not enum object
        assert isinstance(call_args.kwargs["payload"]["status"], str)
        assert call_args.kwargs["payload"]["status"] == PaymentStatus.FAILED.value
