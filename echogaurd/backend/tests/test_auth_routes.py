import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db

client = TestClient(app)

@pytest.fixture
def mock_db_session():
    mock_session = AsyncMock()
    return mock_session

def test_signup_success(mock_db_session):
    with patch('app.api.routes.auth.UserRepository') as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.exists_by_username = AsyncMock(return_value=False)

        user_id = uuid.uuid4()
        mock_repo_instance.create = AsyncMock(return_value=MagicMock(id=user_id, username="test_user", display_name="Test User", created_at="2023-01-01T00:00:00Z"))

        app.dependency_overrides[get_db] = lambda: mock_db_session

        response = client.post("/api/auth/signup", json={
            "username": "test_user",
            "display_name": "Test User",
            "password": "password123"
        })

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "test_user"
        assert "password_hash" not in data

def test_signup_duplicate_username(mock_db_session):
    with patch('app.api.routes.auth.UserRepository') as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.exists_by_username = AsyncMock(return_value=True)

        app.dependency_overrides[get_db] = lambda: mock_db_session

        response = client.post("/api/auth/signup", json={
            "username": "existing_user",
            "display_name": "Existing User",
            "password": "password123"
        })

        assert response.status_code == 409

def test_login_success(mock_db_session):
    with patch('app.api.routes.auth.UserRepository') as MockRepo, \
         patch('app.api.routes.auth.verify_password') as mock_verify:

        mock_repo_instance = MockRepo.return_value
        user_id = uuid.uuid4()
        mock_user = MagicMock(id=user_id, username="test_user", password_hash="hashed")
        mock_repo_instance.get_by_username = AsyncMock(return_value=mock_user)
        mock_verify.return_value = True

        app.dependency_overrides[get_db] = lambda: mock_db_session

        response = client.post("/api/auth/login", json={
            "username": "test_user",
            "password": "password123"
        })

        assert response.status_code == 200
        assert "access_token" in response.json()

def test_login_invalid_credentials(mock_db_session):
    with patch('app.api.routes.auth.UserRepository') as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.get_by_username = AsyncMock(return_value=None)

        app.dependency_overrides[get_db] = lambda: mock_db_session

        response = client.post("/api/auth/login", json={
            "username": "wrong_user",
            "password": "password123"
        })

        assert response.status_code == 401

def test_me_requires_auth():
    response = client.get("/api/auth/me")
    assert response.status_code == 401
