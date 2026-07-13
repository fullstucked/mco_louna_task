from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from payments.application.handlers.events.notify import (
    PayloadStrategyFactory,
    SendNotificationUseCase,
)
from payments.application.interfaces.notifier import WebhookSender
from payments.application.strategies.notification_payload import (
    ConfirmedPayloadStrategy,
    FailurePayloadStrategy,
)
from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus
from payments.domain.events import PaymentProcessedEvent


class TestPayloadStrategies:
    """Tests for payload construction strategies."""

    def test_confirmed_payload_strategy(self):
        """Should build correct payload for CONFIRMED status."""
        payment_id = uuid4()
        event = PaymentProcessedEvent(
            payment_id=payment_id,
            status=PaymentStatus.CONFIRMED,
            webhook_url="https://example.com/webhook",
            amount=100.50,
            currency=Currency.USD,
            reason=None,
        )

        strategy = ConfirmedPayloadStrategy()
        payload = strategy.build(event)

        assert payload == {
            "payment_id": str(payment_id),
            "status": "CONFIRMED",
            "amount": "100.5",
            "currency": "USD",
        }

    def test_failure_payload_strategy_with_reason(self):
        """Should build correct payload for non-CONFIRMED with reason."""
        payment_id = uuid4()
        event = PaymentProcessedEvent(
            payment_id=payment_id,
            status=PaymentStatus.FAILED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason="Insufficient funds",
        )

        strategy = FailurePayloadStrategy()
        payload = strategy.build(event)

        assert payload == {
            "payment_id": str(payment_id),
            "status": "FAILED",
            "reason": "Insufficient funds",
        }
        assert "amount" not in payload
        assert "currency" not in payload

    def test_failure_payload_strategy_default_reason(self):
        """Should use default reason when not provided."""
        event = PaymentProcessedEvent(
            payment_id=uuid4(),
            status=PaymentStatus.PENDING,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason=None,
        )

        strategy = FailurePayloadStrategy(default_reason="Custom default")
        payload = strategy.build(event)

        assert payload["reason"] == "Custom default"


class TestPayloadStrategyFactory:
    """Tests for payload strategy factory."""

    def test_factory_returns_confirmed_strategy(self):
        """Should return ConfirmedPayloadStrategy for CONFIRMED status."""
        strategy = PayloadStrategyFactory.get_strategy(PaymentStatus.CONFIRMED)
        assert isinstance(strategy, ConfirmedPayloadStrategy)

    def test_factory_returns_failure_strategy_for_other_statuses(self):
        """Should return FailurePayloadStrategy for non-CONFIRMED statuses."""
        for status in [PaymentStatus.FAILED, PaymentStatus.PENDING]:
            strategy = PayloadStrategyFactory.get_strategy(status)
            assert isinstance(strategy, FailurePayloadStrategy)


class TestSendNotificationUseCase:
    """Tests for SendNotificationUseCase."""

    @pytest.fixture
    def mock_notifier(self):
        """Fixture for mocked WebhookSender."""
        return AsyncMock(spec=WebhookSender)

    @pytest.fixture
    def use_case(self):
        """Fixture for use case instance."""
        return SendNotificationUseCase()

    @pytest.mark.asyncio
    async def test_send_notification_confirmed(self, use_case, mock_notifier):
        """Should send CONFIRMED notification with amount and currency."""
        payment_id = uuid4()
        event = PaymentProcessedEvent(
            payment_id=payment_id,
            status=PaymentStatus.CONFIRMED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason=None,
        )

        await use_case(notifier=mock_notifier, event=event)

        mock_notifier.send.assert_awaited_once()
        call_args = mock_notifier.send.call_args.kwargs

        assert call_args["payload"]["status"] == "CONFIRMED"
        assert call_args["payload"]["amount"] == "100.0"
        assert call_args["payload"]["currency"] == "USD"

    @pytest.mark.asyncio
    async def test_send_notification_failed(self, use_case, mock_notifier):
        """Should send FAILED notification with reason."""
        event = PaymentProcessedEvent(
            payment_id=uuid4(),
            status=PaymentStatus.FAILED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason="Insufficient funds",
        )

        await use_case(notifier=mock_notifier, event=event)

        call_args = mock_notifier.send.call_args.kwargs
        assert call_args["payload"]["reason"] == "Insufficient funds"
        assert "amount" not in call_args["payload"]

    @pytest.mark.asyncio
    async def test_default_timeout(self, use_case, mock_notifier):
        """Should use DEFAULT_TIMEOUT when not specified."""
        event = PaymentProcessedEvent(
            payment_id=uuid4(),
            status=PaymentStatus.CONFIRMED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason=None,
        )

        await use_case(notifier=mock_notifier, event=event)

        assert (
            mock_notifier.send.call_args.kwargs["timeout"]
            == SendNotificationUseCase.DEFAULT_TIMEOUT
        )

    @pytest.mark.asyncio
    async def test_custom_timeout(self, use_case, mock_notifier):
        """Should use provided timeout."""
        event = PaymentProcessedEvent(
            payment_id=uuid4(),
            status=PaymentStatus.CONFIRMED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason=None,
        )

        await use_case(notifier=mock_notifier, event=event, timeout=10)

        assert mock_notifier.send.call_args.kwargs["timeout"] == 10

    @pytest.mark.asyncio
    async def test_notifier_failure(self, use_case, mock_notifier):
        """Should propagate notifier exceptions."""
        event = PaymentProcessedEvent(
            payment_id=uuid4(),
            status=PaymentStatus.CONFIRMED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason=None,
        )

        mock_notifier.send.side_effect = Exception("Webhook failed")

        with pytest.raises(Exception, match="Webhook failed"):
            await use_case(notifier=mock_notifier, event=event)

    @pytest.mark.asyncio
    async def test_custom_strategy_factory(self, mock_notifier):
        """Should accept custom strategy factory."""
        custom_factory = Mock(spec=PayloadStrategyFactory)
        custom_strategy = Mock()
        custom_strategy.build.return_value = {"custom": "payload"}
        custom_factory.get_strategy.return_value = custom_strategy

        use_case = SendNotificationUseCase(strategy_factory=custom_factory)
        event = PaymentProcessedEvent(
            payment_id=uuid4(),
            status=PaymentStatus.CONFIRMED,
            webhook_url="https://example.com/webhook",
            amount=100.00,
            currency=Currency.USD,
            reason=None,
        )

        await use_case(notifier=mock_notifier, event=event)

        assert mock_notifier.send.call_args.kwargs["payload"] == {"custom": "payload"}
