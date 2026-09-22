import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import MagicMock

from app.db.repositories import (
    UserRepository,
    ContactRepository,
    CallSessionRepository,
    RiskEventRepository,
)

def test_user_repository_methods():
    mock_db = MagicMock(spec=AsyncSession)
    repo = UserRepository(mock_db)

    # Verify methods exist
    assert hasattr(repo, "create")
    assert hasattr(repo, "get_by_id")
    assert hasattr(repo, "get_by_username")
    assert hasattr(repo, "exists_by_username")

def test_contact_repository_methods():
    mock_db = MagicMock(spec=AsyncSession)
    repo = ContactRepository(mock_db)

    # Verify methods exist
    assert hasattr(repo, "create")
    assert hasattr(repo, "get_by_id")
    assert hasattr(repo, "get_user_contacts")
    assert hasattr(repo, "get_trusted_contacts")
    assert hasattr(repo, "exists")

def test_call_session_repository_methods():
    mock_db = MagicMock(spec=AsyncSession)
    repo = CallSessionRepository(mock_db)

    # Verify methods exist
    assert hasattr(repo, "create")
    assert hasattr(repo, "get_by_id")
    assert hasattr(repo, "get_user_calls")
    assert hasattr(repo, "update_status")
    assert hasattr(repo, "end_call")

def test_risk_event_repository_methods():
    mock_db = MagicMock(spec=AsyncSession)
    repo = RiskEventRepository(mock_db)

    # Verify methods exist
    assert hasattr(repo, "create")
    assert hasattr(repo, "get_by_id")
    assert hasattr(repo, "get_call_events")
    assert hasattr(repo, "get_latest_event")
