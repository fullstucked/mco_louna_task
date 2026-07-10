from payments.domain.value_objects.id import PaymentID
from payments.domain.value_objects.metadata import Metadata
from payments.domain.value_objects.webhook import WebhookUrl
from uuid import uuid4
from payments.domain.value_objects.key import IdempotencyKey
from payments.domain.value_objects.description import Description
from payments.domain.value_objects.timestamp import Timestamp
from payments.application.dto.commands.create import CreatePaymentCommand
from payments.domain.enums.status import PaymentStatus
from payments.domain.payment import Payment
from payments.presentation.http.factory import create_app
import pytest
from decimal import Decimal
from uuid import UUID
from unittest.mock import AsyncMock, Mock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_use_case():
    return AsyncMock()


@pytest.fixture
def mock_uow():
    return Mock()


@pytest.fixture
def mock_event_publisher():
    return Mock()


def test_create_payment_success(
    client, monkeypatch, mock_use_case, mock_uow, mock_event_publisher
):
    """Test successful payment creation"""

    # Setup mocks
    payment_id = UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479")
    mock_payment = Payment(
        id=PaymentID(payment_id),
        amount=Decimal("123.45"),
        currency="USD",
        status=PaymentStatus.PENDING,
        created_at=Timestamp.now(),
        description=Description("ewlknfwlkw"),
        key=IdempotencyKey(uuid4()),
        webhook_url=WebhookUrl("https://test.com"),
        metadata=Metadata(meta=dict()),
    )
    mock_use_case.return_value = mock_payment

    # Mock dependencies in FastAPI
    app = create_app()
    app.dependency_overrides = {
        "create_payment_command": lambda: mock_use_case,
        "get_uow": lambda: mock_uow,
        "get_publisher": lambda: mock_event_publisher,
    }

    client = TestClient(app)

    response = client.post(
        "/v1/payments/",
        json={
            "amount": 123.45,
            "currency": "USD",
            "description": "Invoice 123",
            "metadata": {"order_id": "ABC123"},
            "webhook_url": "https://example.com/webhook",
        },
        headers={
            "Idempotency-Key": "unique-key-123",
            "X-API-Key": "dev-key",  # From env
        },
    )

    # Assert HTTP response
    assert response.status_code == 200
    assert response.json()["payment_id"] == str(payment_id)
    assert response.json()["status"] == "PENDING"

    # Assert use case was called correctly
    mock_use_case.assert_called_once()
    call_args = mock_use_case.call_args
    assert isinstance(call_args.kwargs["command"], CreatePaymentCommand)
    assert call_args.kwargs["uow"] == mock_uow


def test_create_payment_invalid_amount(client):
    """Test validation: amount must be greater than 0"""
    response = client.post(
        "/v1/payments/",
        json={
            "amount": 0,  # ❌ Invalid
            "currency": "USD",
            "description": "Invoice 123",
            "webhook_url": "https://example.com/webhook",
        },
        headers={"Idempotency-Key": "key", "X-API-Key": "dev-key"},
    )

    assert response.status_code == 422  # Validation error
    assert "amount" in response.json()["detail"][0]["loc"]


def test_create_payment_missing_idempotency_key(client):
    """Test missing required header"""
    response = client.post(
        "/v1/payments/",
        json={
            "amount": 123.45,
            "currency": "USD",
            "description": "Invoice 123",
            "webhook_url": "https://example.com/webhook",
        },
        headers={"X-API-Key": "dev-key"},  # Missing Idempotency-Key
    )

    assert response.status_code == 422


def test_api_key_validation_unauthorized(client):
    """Test API key validation"""
    response = client.post(
        "/v1/payments/",
        json={
            "amount": 123.45,
            "currency": "USD",
            "description": "Invoice 123",
            "webhook_url": "https://example.com/webhook",
        },
        headers={
            "Idempotency-Key": "key",
            "X-API-Key": "wrong-key",  # ❌ Invalid
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"
