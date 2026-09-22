"""
Unit tests for CallService business logic.
All DB interactions are mocked — no PostgreSQL required.
"""
import uuid
import asyncio
import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.services.call_service import CallService
from app.db.models.call_session import CallSession, CallStatus


# ── factories ─────────────────────────────────────────────────────────────────

def _make_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


_TS = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)


def _make_call(
    caller_id: uuid.UUID,
    receiver_id: uuid.UUID,
    status: CallStatus = CallStatus.RINGING,
    started_at=None,
    ended_at=None,
) -> MagicMock:
    c = MagicMock(spec=CallSession)
    c.id = uuid.uuid4()
    c.caller_id = caller_id
    c.receiver_id = receiver_id
    c.status = status
    c.started_at = started_at
    c.ended_at = ended_at
    c.created_at = _TS
    return c


# ── CREATE ────────────────────────────────────────────────────────────────────

def test_create_call_self_raises_400():
    uid = uuid.uuid4()
    svc = CallService(_make_db())
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.create_call(uid, uid))
    assert exc.value.status_code == 400


def test_create_call_receiver_not_found_raises_404():
    caller = uuid.uuid4()
    receiver = uuid.uuid4()
    svc = CallService(_make_db())
    svc.user_repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.create_call(caller, receiver))
    assert exc.value.status_code == 404


def test_create_call_success():
    caller = uuid.uuid4()
    receiver = uuid.uuid4()
    db = _make_db()
    svc = CallService(db)
    svc.user_repo.get_by_id = AsyncMock(return_value=MagicMock())
    mock_call = _make_call(caller, receiver)
    svc.call_repo.create = AsyncMock(return_value=mock_call)

    result = asyncio.run(svc.create_call(caller, receiver))

    assert result["caller_id"] == str(caller)
    assert result["receiver_id"] == str(receiver)
    assert result["status"] == "RINGING"
    assert "password_hash" not in result
    # caller_id must NOT be accepted from body — test that it equals the injected ID
    assert result["caller_id"] == str(caller)


# ── LIST ──────────────────────────────────────────────────────────────────────

def test_list_calls_returns_participant_calls():
    uid = uuid.uuid4()
    db = _make_db()
    svc = CallService(db)
    calls = [_make_call(uid, uuid.uuid4()), _make_call(uuid.uuid4(), uid)]
    svc.call_repo.get_user_calls = AsyncMock(return_value=calls)

    result = asyncio.run(svc.list_calls(uid))
    assert len(result) == 2


def test_list_calls_status_filter_valid():
    uid = uuid.uuid4()
    db = _make_db()
    svc = CallService(db)
    active_call = _make_call(uid, uuid.uuid4(), status=CallStatus.ACTIVE)
    svc.call_repo.get_user_calls_by_status = AsyncMock(return_value=[active_call])

    result = asyncio.run(svc.list_calls(uid, status_filter="ACTIVE"))
    assert len(result) == 1
    assert result[0]["status"] == "ACTIVE"


def test_list_calls_status_filter_invalid_raises_400():
    svc = CallService(_make_db())
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.list_calls(uuid.uuid4(), status_filter="UNKNOWN"))
    assert exc.value.status_code == 400


# ── GET ───────────────────────────────────────────────────────────────────────

def test_get_call_participant_access():
    caller = uuid.uuid4()
    receiver = uuid.uuid4()
    db = _make_db()
    svc = CallService(db)
    call = _make_call(caller, receiver)
    svc.call_repo.get_by_id = AsyncMock(return_value=call)

    # caller can access
    result = asyncio.run(svc.get_call(caller, call.id))
    assert result["id"] == str(call.id)

    # receiver can access
    result = asyncio.run(svc.get_call(receiver, call.id))
    assert result["id"] == str(call.id)


def test_get_call_non_participant_raises_404():
    caller = uuid.uuid4()
    receiver = uuid.uuid4()
    outsider = uuid.uuid4()
    db = _make_db()
    svc = CallService(db)
    call = _make_call(caller, receiver)
    svc.call_repo.get_by_id = AsyncMock(return_value=call)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.get_call(outsider, call.id))
    assert exc.value.status_code == 404


def test_get_call_not_found_raises_404():
    svc = CallService(_make_db())
    svc.call_repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.get_call(uuid.uuid4(), uuid.uuid4()))
    assert exc.value.status_code == 404


# ── UPDATE STATUS / STATE MACHINE ─────────────────────────────────────────────

def _patch_update(svc: CallService, call: MagicMock):
    svc.call_repo.get_by_id = AsyncMock(return_value=call)
    svc.call_repo.update_status = AsyncMock(return_value=call)
    svc.call_repo.set_started_at = AsyncMock()
    svc.call_repo.set_ended_at = AsyncMock()


def test_ringing_to_active():
    uid = uuid.uuid4()
    call = _make_call(uid, uuid.uuid4(), status=CallStatus.RINGING)
    svc = CallService(_make_db())
    _patch_update(svc, call)
    asyncio.run(svc.update_status(uid, call.id, "ACTIVE"))
    svc.call_repo.set_started_at.assert_called_once()
    svc.call_repo.set_ended_at.assert_not_called()


def test_ringing_to_failed():
    uid = uuid.uuid4()
    call = _make_call(uid, uuid.uuid4(), status=CallStatus.RINGING)
    svc = CallService(_make_db())
    _patch_update(svc, call)
    asyncio.run(svc.update_status(uid, call.id, "FAILED"))
    svc.call_repo.set_ended_at.assert_called_once()


def test_ringing_to_ended():
    uid = uuid.uuid4()
    call = _make_call(uid, uuid.uuid4(), status=CallStatus.RINGING)
    svc = CallService(_make_db())
    _patch_update(svc, call)
    asyncio.run(svc.update_status(uid, call.id, "ENDED"))
    svc.call_repo.set_ended_at.assert_called_once()


def test_active_to_ended():
    uid = uuid.uuid4()
    call = _make_call(uid, uuid.uuid4(), status=CallStatus.ACTIVE)
    svc = CallService(_make_db())
    _patch_update(svc, call)
    asyncio.run(svc.update_status(uid, call.id, "ENDED"))
    svc.call_repo.set_ended_at.assert_called_once()


def test_active_to_failed():
    uid = uuid.uuid4()
    call = _make_call(uid, uuid.uuid4(), status=CallStatus.ACTIVE)
    svc = CallService(_make_db())
    _patch_update(svc, call)
    asyncio.run(svc.update_status(uid, call.id, "FAILED"))
    svc.call_repo.set_ended_at.assert_called_once()


def test_ended_to_active_raises_400():
    uid = uuid.uuid4()
    call = _make_call(uid, uuid.uuid4(), status=CallStatus.ENDED)
    svc = CallService(_make_db())
    svc.call_repo.get_by_id = AsyncMock(return_value=call)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.update_status(uid, call.id, "ACTIVE"))
    assert exc.value.status_code == 400


def test_failed_to_active_raises_400():
    uid = uuid.uuid4()
    call = _make_call(uid, uuid.uuid4(), status=CallStatus.FAILED)
    svc = CallService(_make_db())
    svc.call_repo.get_by_id = AsyncMock(return_value=call)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.update_status(uid, call.id, "ACTIVE"))
    assert exc.value.status_code == 400


def test_ended_to_ringing_raises_400():
    uid = uuid.uuid4()
    call = _make_call(uid, uuid.uuid4(), status=CallStatus.ENDED)
    svc = CallService(_make_db())
    svc.call_repo.get_by_id = AsyncMock(return_value=call)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.update_status(uid, call.id, "RINGING"))
    assert exc.value.status_code == 400


def test_started_at_not_overwritten():
    """set_started_at in the repo is guarded; the service should still call it."""
    uid = uuid.uuid4()
    existing_ts = datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)
    call = _make_call(uid, uuid.uuid4(), status=CallStatus.RINGING, started_at=existing_ts)
    svc = CallService(_make_db())
    _patch_update(svc, call)
    asyncio.run(svc.update_status(uid, call.id, "ACTIVE"))
    # The repo's set_started_at guards against overwriting — service still calls it once
    svc.call_repo.set_started_at.assert_called_once()


# ── END CALL ──────────────────────────────────────────────────────────────────

def test_end_call_success():
    uid = uuid.uuid4()
    call = _make_call(uid, uuid.uuid4(), status=CallStatus.ACTIVE)
    svc = CallService(_make_db())
    _patch_update(svc, call)
    asyncio.run(svc.end_call(uid, call.id))
    svc.call_repo.set_ended_at.assert_called_once()


def test_end_call_already_ended_returns_safely():
    uid = uuid.uuid4()
    call = _make_call(uid, uuid.uuid4(), status=CallStatus.ENDED,
                      ended_at=datetime.datetime(2023, 6, 1, tzinfo=datetime.timezone.utc))
    svc = CallService(_make_db())
    svc.call_repo.get_by_id = AsyncMock(return_value=call)
    svc.call_repo.set_ended_at = AsyncMock()
    # Should not raise and should not mutate ended_at
    result = asyncio.run(svc.end_call(uid, call.id))
    svc.call_repo.set_ended_at.assert_not_called()
    assert result["status"] == "ENDED"


def test_end_call_non_participant_raises_404():
    caller = uuid.uuid4()
    receiver = uuid.uuid4()
    outsider = uuid.uuid4()
    call = _make_call(caller, receiver, status=CallStatus.ACTIVE)
    svc = CallService(_make_db())
    svc.call_repo.get_by_id = AsyncMock(return_value=call)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.end_call(outsider, call.id))
    assert exc.value.status_code == 404
