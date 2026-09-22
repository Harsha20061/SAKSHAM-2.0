"""
Integration-style tests for Calls API routes.
All service/DB calls are mocked — no PostgreSQL required.
"""
import uuid
import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException, status as http_status

from app.main import app
from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.db.models.user import User

client = TestClient(app)

# ── shared fixtures ───────────────────────────────────────────────────────────

CALLER_ID   = uuid.uuid4()
RECEIVER_ID = uuid.uuid4()
CALL_ID     = uuid.uuid4()
_TS = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)

SAMPLE_CALL = {
    "id": str(CALL_ID),
    "caller_id": str(CALLER_ID),
    "receiver_id": str(RECEIVER_ID),
    "status": "RINGING",
    "started_at": None,
    "ended_at": None,
    "created_at": _TS,
}


def _mock_user(user_id: uuid.UUID = CALLER_ID):
    u = MagicMock(spec=User)
    u.id = user_id
    u.username = "caller"
    u.display_name = "Caller"
    u.created_at = _TS
    return u


def _override_auth(user=None):
    u = user or _mock_user()
    app.dependency_overrides[get_current_user] = lambda: u


def _clear():
    app.dependency_overrides = {}


# ── AUTH guard ────────────────────────────────────────────────────────────────

def test_calls_require_auth():
    _clear()
    for method, url in [
        ("GET",   "/api/calls"),
        ("POST",  "/api/calls"),
        ("GET",   f"/api/calls/{CALL_ID}"),
        ("PATCH", f"/api/calls/{CALL_ID}/status"),
        ("POST",  f"/api/calls/{CALL_ID}/end"),
    ]:
        r = client.request(method, url)
        assert r.status_code == 401, f"{method} {url} should be 401"


# ── POST /api/calls ───────────────────────────────────────────────────────────

def test_create_call_success():
    _override_auth()
    with patch("app.api.routes.calls.CallService") as MockSvc:
        MockSvc.return_value.create_call = AsyncMock(return_value=SAMPLE_CALL)
        r = client.post("/api/calls", json={"receiver_id": str(RECEIVER_ID)})
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "RINGING"
    assert "password_hash" not in data
    _clear()


def test_create_call_caller_id_comes_from_jwt():
    """Sending a caller_id in the body must have no effect on the actual caller."""
    _override_auth()
    with patch("app.api.routes.calls.CallService") as MockSvc:
        MockSvc.return_value.create_call = AsyncMock(return_value=SAMPLE_CALL)
        r = client.post("/api/calls", json={
            "receiver_id": str(RECEIVER_ID),
            "caller_id": str(uuid.uuid4()),   # attacker-supplied; should be ignored
        })
    assert r.status_code == 201
    # The route must call create_call with caller_id=CALLER_ID (from JWT)
    call_kwargs = MockSvc.return_value.create_call.call_args
    assert call_kwargs.kwargs["caller_id"] == CALLER_ID
    _clear()


def test_create_call_receiver_not_found_returns_404():
    _override_auth()
    with patch("app.api.routes.calls.CallService") as MockSvc:
        MockSvc.return_value.create_call = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Receiver not found")
        )
        r = client.post("/api/calls", json={"receiver_id": str(uuid.uuid4())})
    assert r.status_code == 404
    _clear()


def test_create_call_self_returns_400():
    _override_auth()
    with patch("app.api.routes.calls.CallService") as MockSvc:
        MockSvc.return_value.create_call = AsyncMock(
            side_effect=HTTPException(status_code=400, detail="Cannot call yourself")
        )
        r = client.post("/api/calls", json={"receiver_id": str(CALLER_ID)})
    assert r.status_code == 400
    _clear()


def test_create_call_invalid_body_returns_422():
    _override_auth()
    r = client.post("/api/calls", json={})
    assert r.status_code == 422
    _clear()


# ── GET /api/calls ────────────────────────────────────────────────────────────

def test_list_calls_success():
    _override_auth()
    with patch("app.api.routes.calls.CallService") as MockSvc:
        MockSvc.return_value.list_calls = AsyncMock(return_value=[SAMPLE_CALL])
        r = client.get("/api/calls")
    assert r.status_code == 200
    assert len(r.json()) == 1
    _clear()


def test_list_calls_status_filter():
    _override_auth()
    active_call = {**SAMPLE_CALL, "status": "ACTIVE"}
    with patch("app.api.routes.calls.CallService") as MockSvc:
        MockSvc.return_value.list_calls = AsyncMock(return_value=[active_call])
        r = client.get("/api/calls?status=ACTIVE")
    assert r.status_code == 200
    assert r.json()[0]["status"] == "ACTIVE"
    # Confirm status_filter was passed through
    call_kwargs = MockSvc.return_value.list_calls.call_args
    assert call_kwargs.kwargs.get("status_filter") == "ACTIVE"
    _clear()


# ── GET /api/calls/{call_id} ──────────────────────────────────────────────────

def test_get_call_success():
    _override_auth()
    with patch("app.api.routes.calls.CallService") as MockSvc:
        MockSvc.return_value.get_call = AsyncMock(return_value=SAMPLE_CALL)
        r = client.get(f"/api/calls/{CALL_ID}")
    assert r.status_code == 200
    assert r.json()["id"] == str(CALL_ID)
    _clear()


def test_get_call_not_participant_returns_404():
    _override_auth()
    with patch("app.api.routes.calls.CallService") as MockSvc:
        MockSvc.return_value.get_call = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Call not found")
        )
        r = client.get(f"/api/calls/{uuid.uuid4()}")
    assert r.status_code == 404
    _clear()


# ── PATCH /api/calls/{call_id}/status ────────────────────────────────────────

def test_update_status_to_active():
    _override_auth()
    active_call = {**SAMPLE_CALL, "status": "ACTIVE"}
    with patch("app.api.routes.calls.CallService") as MockSvc:
        MockSvc.return_value.update_status = AsyncMock(return_value=active_call)
        r = client.patch(f"/api/calls/{CALL_ID}/status", json={"status": "ACTIVE"})
    assert r.status_code == 200
    assert r.json()["status"] == "ACTIVE"
    _clear()


def test_update_status_invalid_transition_returns_400():
    _override_auth()
    with patch("app.api.routes.calls.CallService") as MockSvc:
        MockSvc.return_value.update_status = AsyncMock(
            side_effect=HTTPException(status_code=400, detail="Invalid transition")
        )
        r = client.patch(f"/api/calls/{CALL_ID}/status", json={"status": "ENDED"})
    assert r.status_code == 400
    _clear()


def test_update_status_non_participant_returns_404():
    _override_auth()
    with patch("app.api.routes.calls.CallService") as MockSvc:
        MockSvc.return_value.update_status = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Not found")
        )
        r = client.patch(f"/api/calls/{CALL_ID}/status", json={"status": "ACTIVE"})
    assert r.status_code == 404
    _clear()


def test_update_status_invalid_body_returns_422():
    _override_auth()
    # "RINGING" is not allowed in UpdateCallStatusRequest (only ACTIVE/ENDED/FAILED)
    r = client.patch(f"/api/calls/{CALL_ID}/status", json={"status": "RINGING"})
    assert r.status_code == 422
    _clear()


# ── POST /api/calls/{call_id}/end ─────────────────────────────────────────────

def test_end_call_success():
    _override_auth()
    ended_call = {**SAMPLE_CALL, "status": "ENDED", "ended_at": _TS}
    with patch("app.api.routes.calls.CallService") as MockSvc:
        MockSvc.return_value.end_call = AsyncMock(return_value=ended_call)
        r = client.post(f"/api/calls/{CALL_ID}/end")
    assert r.status_code == 200
    assert r.json()["status"] == "ENDED"
    _clear()


def test_end_call_already_ended_returns_200():
    _override_auth()
    ended_call = {**SAMPLE_CALL, "status": "ENDED", "ended_at": _TS}
    with patch("app.api.routes.calls.CallService") as MockSvc:
        MockSvc.return_value.end_call = AsyncMock(return_value=ended_call)
        r = client.post(f"/api/calls/{CALL_ID}/end")
    assert r.status_code == 200
    assert r.json()["status"] == "ENDED"
    _clear()


def test_end_call_non_participant_returns_404():
    _override_auth()
    with patch("app.api.routes.calls.CallService") as MockSvc:
        MockSvc.return_value.end_call = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Not found")
        )
        r = client.post(f"/api/calls/{CALL_ID}/end")
    assert r.status_code == 404


def test_security_report_returns_final_and_peak_risk():
    report = {
        "call_id": str(CALL_ID),
        "duration_seconds": 42.0,
        "status": "ENDED",
        "started_at": _TS,
        "ended_at": _TS + datetime.timedelta(seconds=42),
        "final_risk_score": 0.72,
        "final_risk_level": "HIGH",
        "peak_risk_score": 0.91,
        "voice_authenticity_risk": 0.8,
        "speaker_verification_status": "NOT ENROLLED",
        "speaker_similarity": None,
        "scam_probability": 0.75,
        "indicators": ["otp_request"],
        "recommended_action": "Do not share OTPs.",
    }
    with patch("app.api.routes.risk_events.RiskEventService") as MockSvc:
        MockSvc.get_call_security_report = AsyncMock(return_value=report)
        r = client.get(f"/api/calls/{CALL_ID}/security-report")

    assert r.status_code == 200
    assert r.json()["status"] == "ENDED"
    assert r.json()["peak_risk_score"] == 0.91
    assert r.json()["speaker_verification_status"] == "NOT ENROLLED"
    _clear()
