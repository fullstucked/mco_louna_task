from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from payments.application.handlers.queries.get import (
    GetPayment,
    GetPaymentQuery,
    GetPaymentQueryResponse,
)
from payments.application.interfaces.uow import PaymentUoW
from payments.domain.enums.currency import Currency
from payments.domain.payment import Payment
from payments.domain.value_objects.amount import Amount
from payments.domain.value_objects.description import Description
from payments.domain.value_objects.key import IdempotencyKey
from payments.domain.value_objects.metadata import Metadata
from payments.domain.value_objects.webhook import WebhookUrl
from shared.domain.errors import DomainResourceNotFoundError, DomainTypeError


class TestGetPayment:
    """Tests for GetPayment query handler."""

    @pytest.mark.asyncio
    async def test_get_payment_success(self):
        """GetPayment should retrieve payment by id and return response DTO."""
        payment_id = uuid4()

        query = GetPaymentQuery(id=payment_id)

        # Create a real payment aggregate
        payment = Payment(
            amount=Amount(Decimal(100.00)),
            currency=Currency.USD,
            description=Description("Test payment"),
            metadata=Metadata({"key": "value"}),
            key=IdempotencyKey(uuid4()),
            webhook_url=WebhookUrl("https://example.com/webhook"),
        )

        # Mock repositories
        mock_payments_repo = AsyncMock()
        mock_payments_repo.get_by_id = AsyncMock(return_value=payment)

        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.payments = mock_payments_repo

        query_handler = GetPayment()
        result = await query_handler(query=query, uow=mock_uow)

        # Assert repository was called with correct PaymentID
        mock_payments_repo.get_by_id.assert_awaited_once()
        call_args = mock_payments_repo.get_by_id.call_args[0][0]
        assert call_args.value == payment_id

        # Assert response DTO
        assert isinstance(result, GetPaymentQueryResponse)
        assert result.payment_id == payment.id.value
        assert result.status == payment.status
        assert result.created_at == payment.created_at.timestamp

    @pytest.mark.asyncio
    async def test_get_payment_uses_context_manager(self):
        """GetPayment should properly use UoW context manager."""
        query = GetPaymentQuery(id=uuid4())

        payment = Payment(
            amount=Amount(Decimal(50.00)),
            currency=Currency.EUR,
            description=Description("Test"),
            metadata=Metadata({}),
            key=IdempotencyKey(uuid4()),
            webhook_url=WebhookUrl("https://example.com/webhook"),
        )

        mock_payments_repo = AsyncMock()
        mock_payments_repo.get_by_id = AsyncMock(return_value=payment)

        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.payments = mock_payments_repo

        query_handler = GetPayment()
        await query_handler(query=query, uow=mock_uow)

        # Verify context manager was used
        mock_uow.__aenter__.assert_awaited_once()
        mock_uow.__aexit__.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_payment_not_found(self):
        """GetPayment should raise exception when payment not found."""
        query = GetPaymentQuery(id=uuid4())

        mock_payments_repo = AsyncMock()
        # Repository raises when payment not found
        mock_payments_repo.get_by_id = AsyncMock(
            side_effect=DomainResourceNotFoundError(message="Payment not found")
        )

        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.payments = mock_payments_repo

        query_handler = GetPayment()

        with pytest.raises(DomainResourceNotFoundError):
            await query_handler(query=query, uow=mock_uow)

    @pytest.mark.asyncio
    async def test_get_payment_response_mapping(self):
        """GetPayment should correctly map domain payment to response DTO."""
        payment_id = uuid4()
        query = GetPaymentQuery(id=payment_id)

        # Create payment with specific data
        payment = Payment(
            amount=Amount(Decimal("75.50")),
            currency=Currency.RUB,
            description=Description("Detailed test payment"),
            metadata=Metadata({"order_id": "12345", "user": "test_user"}),
            key=IdempotencyKey(uuid4()),
            webhook_url=WebhookUrl("https://api.example.com/payment/webhook"),
        )

        mock_payments_repo = AsyncMock()
        mock_payments_repo.get_by_id = AsyncMock(return_value=payment)

        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.payments = mock_payments_repo

        query_handler = GetPayment()
        result = await query_handler(query=query, uow=mock_uow)

        # Verify all fields are correctly mapped
        assert result.payment_id == payment.id.value
        assert result.status == payment.status
        assert result.created_at == payment.created_at.timestamp
        assert result.amount == payment.amount.value
        assert result.currency == payment.currency.value
        assert result.description == payment.description.text
        assert result.metadata == payment.metadata.value

    @pytest.mark.asyncio
    async def test_get_payment_invalid_uuid(self):
        """GetPayment should raise exception for invalid UUID format."""
        query = GetPaymentQuery(id="not-a-uuid")  # Invalid UUID

        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None

        query_handler = GetPayment()

        with pytest.raises(DomainTypeError):
            await query_handler(query=query, uow=mock_uow)
