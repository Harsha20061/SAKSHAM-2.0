import pytest
from app.services.auth_service import hash_password, verify_password, create_access_token
from jose import jwt
from app.core.config import settings

def test_password_hashing():
    password = "secure_password"
    hashed = hash_password(password)

    # Password is not stored as plaintext
    assert password != hashed

    # Correct password verifies
    assert verify_password(password, hashed) is True

    # Incorrect password fails
    assert verify_password("wrong_password", hashed) is False

def test_jwt_creation():
    data = {"sub": "12345"}
    token = create_access_token(data)

    # Token contains user ID
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload.get("sub") == "12345"
    assert "exp" in payload
