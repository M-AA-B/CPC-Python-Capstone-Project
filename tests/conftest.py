import pytest
from app import create_app

@pytest.fixture()
def client():
    app = create_app({"TESTING": True, "SECRET_KEY": "test-only", "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    return app.test_client()
