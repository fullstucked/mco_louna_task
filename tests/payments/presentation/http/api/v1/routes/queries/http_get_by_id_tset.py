from payments.domain.enums.currency import Currency
from payments.domain.value_objects.amount import Amount
from payments.domain.value_objects.id import PaymentID
from payments.presentation.http.factory import create_app
from payments.domain.enums.status import PaymentStatus
from payments.domain.payment import Payment
from decimal import Decimal
from uuid import UUID
from unittest.mock import Mock
from fastapi.testclient import TestClient


def test_get_payment_success(client):
    """Test successful payment retrieval"""
    payment_id = "f47ac10b-58cc-4372-a567-0e02b2c3d479"

    mock_use_case = Mock()
    mock_payment = Payment(
        amount=Amount(Decimal("123.45")),
        currency=Currency.USD,
        status=PaymentStatus.PENDING,
        # ... other fields
    )
    mock_use_case.return_value = mock_payment

    app = create_app()
    app.dependency_overrides = {
        "get_payment_query": lambda: mock_use_case,
    }

    client = TestClient(app)
    response = client.get(
        f"/v1/payments/{payment_id}",
        headers={"X-API-Key": "dev-key"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == payment_id


def test_get_payment_invalid_id_format(client):
    """Test invalid UUID format"""
    response = client.get(
        "/v1/payments/not-a-uuid",
        headers={"X-API-Key": "dev-key"},
    )

    assert response.status_code == 400
    assert "Invalid payment ID format" in response.json()["detail"]
