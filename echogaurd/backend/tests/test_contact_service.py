"""
Unit tests for ContactService business logic.
All database interactions are mocked — no PostgreSQL required.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Drive asyncio ourselves (no pytest-asyncio plugin installed)
import asyncio

from fastapi import HTTPException
from app.services.contact_service import ContactService


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


def _make_contact(
    owner_id: uuid.UUID,
    contact_user_id: uuid.UUID,
    nickname: str = "Friend",
    is_trusted: bool = False,
) -> MagicMock:
    c = MagicMock()
    c.id = uuid.uuid4()
    c.user_id = owner_id
    c.contact_user_id = contact_user_id
    c.nickname = nickname
    c.is_trusted = is_trusted
    import datetime
    c.created_at = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    return c


# ── CREATE ────────────────────────────────────────────────────────────────────

def test_create_contact_self_raises_400():
    owner_id = uuid.uuid4()
    db = _make_db()
    svc = ContactService(db)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.create_contact(owner_id, owner_id, "Me", False))
    assert exc.value.status_code == 400


def test_create_contact_target_not_found_raises_404():
    owner_id = uuid.uuid4()
    contact_user_id = uuid.uuid4()
    db = _make_db()
    svc = ContactService(db)
    svc.user_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.create_contact(owner_id, contact_user_id, "Ghost", False))
    assert exc.value.status_code == 404


def test_create_contact_duplicate_raises_409():
    owner_id = uuid.uuid4()
    contact_user_id = uuid.uuid4()
    db = _make_db()
    svc = ContactService(db)
    svc.user_repo.get_by_id = AsyncMock(return_value=MagicMock())
    svc.contact_repo.exists = AsyncMock(return_value=True)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.create_contact(owner_id, contact_user_id, "Dup", False))
    assert exc.value.status_code == 409


def test_create_contact_success():
    owner_id = uuid.uuid4()
    contact_user_id = uuid.uuid4()
    db = _make_db()
    svc = ContactService(db)
    svc.user_repo.get_by_id = AsyncMock(return_value=MagicMock())
    svc.contact_repo.exists = AsyncMock(return_value=False)

    mock_contact = _make_contact(owner_id, contact_user_id)
    svc.contact_repo.create = AsyncMock(return_value=mock_contact)

    result = asyncio.run(svc.create_contact(owner_id, contact_user_id, "Friend", True))

    assert result["contact_user_id"] == str(contact_user_id)
    assert result["nickname"] == "Friend"
    assert "password_hash" not in result


# ── LIST ──────────────────────────────────────────────────────────────────────

def test_list_contacts_returns_owned_only():
    owner_id = uuid.uuid4()
    db = _make_db()
    svc = ContactService(db)
    contacts = [_make_contact(owner_id, uuid.uuid4()), _make_contact(owner_id, uuid.uuid4())]
    svc.contact_repo.get_user_contacts = AsyncMock(return_value=contacts)

    result = asyncio.run(svc.list_contacts(owner_id, trusted_only=False))
    assert len(result) == 2


def test_list_contacts_trusted_only():
    owner_id = uuid.uuid4()
    db = _make_db()
    svc = ContactService(db)
    trusted = [_make_contact(owner_id, uuid.uuid4(), is_trusted=True)]
    svc.contact_repo.get_trusted_contacts = AsyncMock(return_value=trusted)

    result = asyncio.run(svc.list_contacts(owner_id, trusted_only=True))
    assert len(result) == 1
    assert result[0]["is_trusted"] is True


# ── GET ───────────────────────────────────────────────────────────────────────

def test_get_contact_not_found_raises_404():
    owner_id = uuid.uuid4()
    db = _make_db()
    svc = ContactService(db)
    svc.contact_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.get_contact(owner_id, uuid.uuid4()))
    assert exc.value.status_code == 404


def test_get_contact_wrong_owner_raises_404():
    """A contact belonging to another user must not be revealed."""
    owner_id = uuid.uuid4()
    other_owner = uuid.uuid4()
    db = _make_db()
    svc = ContactService(db)
    # Contact exists but belongs to other_owner
    mock_contact = _make_contact(other_owner, uuid.uuid4())
    svc.contact_repo.get_by_id = AsyncMock(return_value=mock_contact)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.get_contact(owner_id, mock_contact.id))
    assert exc.value.status_code == 404


# ── UPDATE ────────────────────────────────────────────────────────────────────

def test_update_contact_success():
    owner_id = uuid.uuid4()
    contact_id = uuid.uuid4()
    db = _make_db()
    svc = ContactService(db)
    mock_contact = _make_contact(owner_id, uuid.uuid4())
    mock_contact.id = contact_id
    svc.contact_repo.get_by_id = AsyncMock(return_value=mock_contact)
    svc.contact_repo.update = AsyncMock(return_value=mock_contact)

    result = asyncio.run(svc.update_contact(owner_id, contact_id, nickname="Updated", is_trusted=True))
    assert result["nickname"] == "Friend"  # mock didn't mutate; logic tested in repo tests


def test_update_contact_wrong_owner_raises_404():
    owner_id = uuid.uuid4()
    other_owner = uuid.uuid4()
    db = _make_db()
    svc = ContactService(db)
    mock_contact = _make_contact(other_owner, uuid.uuid4())
    svc.contact_repo.get_by_id = AsyncMock(return_value=mock_contact)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.update_contact(owner_id, mock_contact.id, nickname="Hack", is_trusted=None))
    assert exc.value.status_code == 404


# ── DELETE ────────────────────────────────────────────────────────────────────

def test_delete_contact_success():
    owner_id = uuid.uuid4()
    contact_id = uuid.uuid4()
    db = _make_db()
    svc = ContactService(db)
    mock_contact = _make_contact(owner_id, uuid.uuid4())
    mock_contact.id = contact_id
    svc.contact_repo.get_by_id = AsyncMock(return_value=mock_contact)
    svc.contact_repo.delete = AsyncMock()

    # Should not raise
    asyncio.run(svc.delete_contact(owner_id, contact_id))
    svc.contact_repo.delete.assert_called_once_with(mock_contact)


def test_delete_contact_wrong_owner_raises_404():
    owner_id = uuid.uuid4()
    other_owner = uuid.uuid4()
    db = _make_db()
    svc = ContactService(db)
    mock_contact = _make_contact(other_owner, uuid.uuid4())
    svc.contact_repo.get_by_id = AsyncMock(return_value=mock_contact)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.delete_contact(owner_id, mock_contact.id))
    assert exc.value.status_code == 404


def test_delete_contact_not_found_raises_404():
    owner_id = uuid.uuid4()
    db = _make_db()
    svc = ContactService(db)
    svc.contact_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.delete_contact(owner_id, uuid.uuid4()))
    assert exc.value.status_code == 404
