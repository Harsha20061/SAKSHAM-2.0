"""
Integration-style tests for Contacts API routes.
All service/DB calls are mocked — no PostgreSQL required.
"""
import uuid
import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException, status

from app.main import app
from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.db.models.user import User

client = TestClient(app)

# ── shared fixtures ───────────────────────────────────────────────────────────

OWNER_ID = uuid.uuid4()
OTHER_ID = uuid.uuid4()
CONTACT_ID = uuid.uuid4()
TARGET_USER_ID = uuid.uuid4()

_CREATED_AT = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)

SAMPLE_CONTACT_DICT = {
    "id": str(CONTACT_ID),
    "contact_user_id": str(TARGET_USER_ID),
    "nickname": "Test Friend",
    "is_trusted": False,
    "created_at": _CREATED_AT,
}


def _mock_owner():
    u = MagicMock(spec=User)
    u.id = OWNER_ID
    u.username = "owner"
    u.display_name = "Owner"
    u.created_at = _CREATED_AT
    return u


def _override_auth(user: MagicMock):
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides():
    app.dependency_overrides = {}


# ── AUTH guard ────────────────────────────────────────────────────────────────

def test_contacts_requires_auth():
    _clear_overrides()
    for method, url in [
        ("GET",    "/api/contacts"),
        ("POST",   "/api/contacts"),
        ("GET",    f"/api/contacts/{CONTACT_ID}"),
        ("PATCH",  f"/api/contacts/{CONTACT_ID}"),
        ("DELETE", f"/api/contacts/{CONTACT_ID}"),
    ]:
        resp = client.request(method, url)
        assert resp.status_code == 401, f"{method} {url} should be 401 without auth"


# ── POST /api/contacts ────────────────────────────────────────────────────────

def test_create_contact_success():
    _override_auth(_mock_owner())
    with patch("app.api.routes.contacts.ContactService") as MockSvc:
        MockSvc.return_value.create_contact = AsyncMock(return_value=SAMPLE_CONTACT_DICT)
        resp = client.post("/api/contacts", json={
            "contact_user_id": str(TARGET_USER_ID),
            "nickname": "Test Friend",
            "is_trusted": False,
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["nickname"] == "Test Friend"
    assert "password_hash" not in data
    _clear_overrides()


def test_create_contact_self_returns_400():
    _override_auth(_mock_owner())
    with patch("app.api.routes.contacts.ContactService") as MockSvc:
        MockSvc.return_value.create_contact = AsyncMock(
            side_effect=HTTPException(status_code=400, detail="Cannot add yourself")
        )
        resp = client.post("/api/contacts", json={
            "contact_user_id": str(OWNER_ID),
            "nickname": "Me",
            "is_trusted": False,
        })
    assert resp.status_code == 400
    _clear_overrides()


def test_create_contact_target_not_found_returns_404():
    _override_auth(_mock_owner())
    with patch("app.api.routes.contacts.ContactService") as MockSvc:
        MockSvc.return_value.create_contact = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Target user not found")
        )
        resp = client.post("/api/contacts", json={
            "contact_user_id": str(uuid.uuid4()),
            "nickname": "Ghost",
            "is_trusted": False,
        })
    assert resp.status_code == 404
    _clear_overrides()


def test_create_contact_duplicate_returns_409():
    _override_auth(_mock_owner())
    with patch("app.api.routes.contacts.ContactService") as MockSvc:
        MockSvc.return_value.create_contact = AsyncMock(
            side_effect=HTTPException(status_code=409, detail="Already exists")
        )
        resp = client.post("/api/contacts", json={
            "contact_user_id": str(TARGET_USER_ID),
            "nickname": "Dup",
            "is_trusted": False,
        })
    assert resp.status_code == 409
    _clear_overrides()


def test_create_contact_invalid_body_returns_422():
    _override_auth(_mock_owner())
    resp = client.post("/api/contacts", json={"nickname": "NoUUID"})
    assert resp.status_code == 422
    _clear_overrides()


# ── GET /api/contacts ─────────────────────────────────────────────────────────

def test_list_contacts_success():
    _override_auth(_mock_owner())
    with patch("app.api.routes.contacts.ContactService") as MockSvc:
        MockSvc.return_value.list_contacts = AsyncMock(return_value=[SAMPLE_CONTACT_DICT])
        resp = client.get("/api/contacts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) == 1
    _clear_overrides()


def test_list_contacts_trusted_only():
    _override_auth(_mock_owner())
    trusted_dict = {**SAMPLE_CONTACT_DICT, "is_trusted": True}
    with patch("app.api.routes.contacts.ContactService") as MockSvc:
        MockSvc.return_value.list_contacts = AsyncMock(return_value=[trusted_dict])
        resp = client.get("/api/contacts?trusted_only=true")
    assert resp.status_code == 200
    assert resp.json()[0]["is_trusted"] is True
    _clear_overrides()


# ── GET /api/contacts/{id} ────────────────────────────────────────────────────

def test_get_contact_success():
    _override_auth(_mock_owner())
    with patch("app.api.routes.contacts.ContactService") as MockSvc:
        MockSvc.return_value.get_contact = AsyncMock(return_value=SAMPLE_CONTACT_DICT)
        resp = client.get(f"/api/contacts/{CONTACT_ID}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(CONTACT_ID)
    _clear_overrides()


def test_get_contact_not_found_returns_404():
    _override_auth(_mock_owner())
    with patch("app.api.routes.contacts.ContactService") as MockSvc:
        MockSvc.return_value.get_contact = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Not found")
        )
        resp = client.get(f"/api/contacts/{uuid.uuid4()}")
    assert resp.status_code == 404
    _clear_overrides()


def test_get_contact_other_user_returns_404():
    """Another user's contact must return 404, not the contact data."""
    _override_auth(_mock_owner())
    with patch("app.api.routes.contacts.ContactService") as MockSvc:
        MockSvc.return_value.get_contact = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Not found")
        )
        resp = client.get(f"/api/contacts/{CONTACT_ID}")
    assert resp.status_code == 404
    _clear_overrides()


# ── PATCH /api/contacts/{id} ──────────────────────────────────────────────────

def test_update_contact_success():
    _override_auth(_mock_owner())
    updated = {**SAMPLE_CONTACT_DICT, "nickname": "New Name", "is_trusted": True}
    with patch("app.api.routes.contacts.ContactService") as MockSvc:
        MockSvc.return_value.update_contact = AsyncMock(return_value=updated)
        resp = client.patch(f"/api/contacts/{CONTACT_ID}", json={"nickname": "New Name", "is_trusted": True})
    assert resp.status_code == 200
    assert resp.json()["nickname"] == "New Name"
    _clear_overrides()


def test_update_contact_other_user_returns_404():
    _override_auth(_mock_owner())
    with patch("app.api.routes.contacts.ContactService") as MockSvc:
        MockSvc.return_value.update_contact = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Not found")
        )
        resp = client.patch(f"/api/contacts/{CONTACT_ID}", json={"nickname": "Hacker"})
    assert resp.status_code == 404
    _clear_overrides()


# ── DELETE /api/contacts/{id} ─────────────────────────────────────────────────

def test_delete_contact_success():
    _override_auth(_mock_owner())
    with patch("app.api.routes.contacts.ContactService") as MockSvc:
        MockSvc.return_value.delete_contact = AsyncMock(return_value=None)
        resp = client.delete(f"/api/contacts/{CONTACT_ID}")
    assert resp.status_code == 204
    _clear_overrides()


def test_delete_contact_other_user_returns_404():
    _override_auth(_mock_owner())
    with patch("app.api.routes.contacts.ContactService") as MockSvc:
        MockSvc.return_value.delete_contact = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Not found")
        )
        resp = client.delete(f"/api/contacts/{CONTACT_ID}")
    assert resp.status_code == 404
    _clear_overrides()


def test_delete_contact_not_found_returns_404():
    _override_auth(_mock_owner())
    with patch("app.api.routes.contacts.ContactService") as MockSvc:
        MockSvc.return_value.delete_contact = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Not found")
        )
        resp = client.delete(f"/api/contacts/{uuid.uuid4()}")
    assert resp.status_code == 404
    _clear_overrides()


# ── SECURITY: user_id never from client body ──────────────────────────────────

def test_user_id_not_accepted_in_body():
    """
    The API must not accept user_id from the request body.
    CreateContactRequest has no user_id field — Pydantic will ignore/reject it.
    """
    _override_auth(_mock_owner())
    with patch("app.api.routes.contacts.ContactService") as MockSvc:
        MockSvc.return_value.create_contact = AsyncMock(return_value=SAMPLE_CONTACT_DICT)
        resp = client.post("/api/contacts", json={
            "user_id": str(OTHER_ID),          # should be ignored
            "contact_user_id": str(TARGET_USER_ID),
            "nickname": "Injected",
            "is_trusted": False,
        })
    # Route still calls create_contact; user_id was NOT passed from body
    assert resp.status_code == 201
    # Confirm service was called — user_id ownership comes from JWT, not body
    MockSvc.return_value.create_contact.assert_called_once()
    call_kwargs = MockSvc.return_value.create_contact.call_args
    assert call_kwargs.kwargs["owner_id"] == OWNER_ID   # from JWT, not body
    _clear_overrides()
