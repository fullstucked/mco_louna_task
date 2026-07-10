import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Set test environment variables"""
    os.environ["API_KEY"] = "secret"
    os.environ["BROKER_URL"] = "amqp://test"


@pytest.fixture
def client():

    from payments.presentation.http.factory import create_app

    app = create_app()
    return TestClient(app)
