import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.api.dependencies import get_current_user
from app.db.models.user import User

def test_get_current_user_valid_token():
    user_id = uuid.uuid4()
    mock_db = AsyncMock()
    mock_user = MagicMock(id=user_id, username="test_user")

    with patch('app.api.dependencies.jwt.decode') as mock_decode, \
         patch('app.api.dependencies.UserRepository') as MockRepo:

        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.get_by_id = AsyncMock(return_value=mock_user)
        mock_decode.return_value = {"sub": str(user_id)}

        user = asyncio.run(get_current_user(token="valid_token", db=mock_db))
        assert user.id == user_id
        assert user.username == "test_user"

def test_get_current_user_invalid_token():
    mock_db = AsyncMock()

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(get_current_user(token="invalid_token", db=mock_db))

    assert excinfo.value.status_code == 401
