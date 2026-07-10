from uuid import uuid4
from decimal import Decimal

import pytest

from payments.domain.enums.currency import Currency
from payments.domain.enums.status import PaymentStatus
from payments.domain.events import PaymentCreatedEvent
from payments.domain.payment import Payment
from payments.domain.value_objects.amount import Amount
from payments.domain.value_objects.description import Description
from payments.domain.value_objects.key import IdempotencyKey
from payments.domain.value_objects.metadata import Metadata
from payments.domain.value_objects.webhook import WebhookUrl
from shared.domain.errors import DomainBusinessRuleError


class TestPaymentConstruction:
    """Tests for Payment instantiation."""

    def test_create_new_payment(self):
        """New payment should have PENDING status and creation event."""
        payment = Payment(
            amount=Amount(amount=Decimal("100.00")),
            currency=Currency.USD,
            description=Description(text="Order #123"),
            metadata=Metadata(meta={"order_id": "123"}),
            key=IdempotencyKey(key=uuid4()),
            webhook_url=WebhookUrl(url="https://example.com/webhook"),
        )

        assert payment.status == PaymentStatus.PENDING
        assert payment.processed_at is None
        assert len(payment._events) == 1
        assert isinstance(payment._events[0], PaymentCreatedEvent)

    def test_processed_payment_without_timestamp_raises_error(self):
        """Payment with non-PENDING status but no processed_at should raise."""
        with pytest.raises(DomainBusinessRuleError):
            Payment(
                amount=Amount(amount=Decimal("100.00")),
                currency=Currency.USD,
                description=Description(text="Order #123"),
                metadata=Metadata(meta={}),
                key=IdempotencyKey(key=uuid4()),
                webhook_url=WebhookUrl(url="https://example.com/webhook"),
                status=PaymentStatus.CONFIRMED,  # Invalid: no timestamp
            )


class TestPaymentStateTransitions:
    """Tests for Payment state changes."""

    def test_mark_as_succeeded(self):
        """Mark PENDING payment as CONFIRMED."""
        payment = Payment(
            amount=Amount(amount=Decimal("100.00")),
            currency=Currency.USD,
            description=Description(text="Order #123"),
            metadata=Metadata(meta={}),
            key=IdempotencyKey(key=uuid4()),
            webhook_url=WebhookUrl(url="https://example.com/webhook"),
        )

        payment.mark_as_succeeded()

        assert payment.status == PaymentStatus.CONFIRMED
        assert payment.processed_at is not None
        assert len(payment._events) == 2  # Creation + ProcessedEvent

    def test_mark_as_succeeded_when_already_processed_raises_error(self):
        """Cannot mark already-processed payment as succeeded."""
        payment = Payment(
            amount=Amount(amount=Decimal("100.00")),
            currency=Currency.USD,
            description=Description(text="Order #123"),
            metadata=Metadata(meta={}),
            key=IdempotencyKey(key=uuid4()),
            webhook_url=WebhookUrl(url="https://example.com/webhook"),
        )
        payment.mark_as_succeeded()

        with pytest.raises(DomainBusinessRuleError) as exc_info:
            payment.mark_as_succeeded()
        assert "Already processed" in str(exc_info.value.message)
