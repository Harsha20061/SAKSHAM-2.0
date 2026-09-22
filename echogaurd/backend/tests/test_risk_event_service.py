import uuid
import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from app.services.risk_event_service import RiskEventService
from app.models.schemas import RiskEventRequest
from app.db.models.user import User
from app.db.models.call_session import CallSession, CallStatus
from app.db.models.risk_event import RiskEvent, RiskLevel

_TS = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
USER_ID = uuid.uuid4()
CALL_ID = uuid.uuid4()
EVENT_ID = uuid.uuid4()

def mock_user(uid=USER_ID):
    u = MagicMock(spec=User)
    u.id = uid
    return u

def mock_call(status=CallStatus.ACTIVE, caller_id=USER_ID, receiver_id=uuid.uuid4()):
    c = MagicMock(spec=CallSession)
    c.id = CALL_ID
    c.caller_id = caller_id
    c.receiver_id = receiver_id
    c.status = status
    return c

def mock_risk_event():
    e = MagicMock(spec=RiskEvent)
    e.id = EVENT_ID
    e.call_id = CALL_ID
    e.spoof_probability = 0.92
    e.speaker_similarity = 0.21
    e.scam_score = 0.88
    e.risk_score = 0.87
    e.risk_level = RiskLevel.HIGH
    e.indicators = ["money_request", "urgency"]
    e.latency_ms = 640
    e.timestamp = _TS
    return e

@pytest.mark.anyio
async def test_create_risk_event():
    db = AsyncMock()
    user = mock_user()
    call = mock_call()
    event = mock_risk_event()

    request = RiskEventRequest(
        spoof_probability=0.92,
        speaker_similarity=0.21,
        scam_score=0.88,
        risk_score=0.87,
        risk_level="HIGH",
        indicators=["money_request", "urgency"],
        latency_ms=640
    )

    with patch('app.services.risk_event_service.CallSessionRepository') as mock_call_repo_cls, \
         patch('app.services.risk_event_service.RiskEventRepository') as mock_risk_repo_cls:

        mock_call_repo = mock_call_repo_cls.return_value
        mock_call_repo.get_by_id = AsyncMock(return_value=call)

        mock_risk_repo = mock_risk_repo_cls.return_value
        mock_risk_repo.create = AsyncMock(return_value=event)

        response = await RiskEventService.create_risk_event(db, user, str(CALL_ID), request)

        assert response.id == str(EVENT_ID)
        assert response.risk_level == "HIGH"
        mock_risk_repo.create.assert_called_once()
        db.commit.assert_called_once()

@pytest.mark.anyio
async def test_create_risk_event_terminal_call():
    db = AsyncMock()
    user = mock_user()
    call = mock_call(status=CallStatus.ENDED)

    request = RiskEventRequest(
        spoof_probability=0.92,
        speaker_similarity=0.21,
        scam_score=0.88,
        risk_score=0.87,
        risk_level="HIGH",
        indicators=["money_request", "urgency"],
        latency_ms=640
    )

    with patch('app.services.risk_event_service.CallSessionRepository') as mock_call_repo_cls:
        mock_call_repo = mock_call_repo_cls.return_value
        mock_call_repo.get_by_id = AsyncMock(return_value=call)

        with pytest.raises(HTTPException) as exc:
            await RiskEventService.create_risk_event(db, user, str(CALL_ID), request)

        assert exc.value.status_code == 400

@pytest.mark.anyio
async def test_create_risk_event_non_participant():
    db = AsyncMock()
    user = mock_user(uid=uuid.uuid4()) # different user
    call = mock_call()

    request = RiskEventRequest(
        spoof_probability=0.92,
        speaker_similarity=0.21,
        scam_score=0.88,
        risk_score=0.87,
        risk_level="HIGH",
        indicators=[],
        latency_ms=640
    )

    with patch('app.services.risk_event_service.CallSessionRepository') as mock_call_repo_cls:
        mock_call_repo = mock_call_repo_cls.return_value
        mock_call_repo.get_by_id = AsyncMock(return_value=call)

        with pytest.raises(HTTPException) as exc:
            await RiskEventService.create_risk_event(db, user, str(CALL_ID), request)

        assert exc.value.status_code == 404

@pytest.mark.anyio
async def test_get_call_events():
    db = AsyncMock()
    user = mock_user()
    call = mock_call()
    event = mock_risk_event()

    with patch('app.services.risk_event_service.CallSessionRepository') as mock_call_repo_cls, \
         patch('app.services.risk_event_service.RiskEventRepository') as mock_risk_repo_cls:

        mock_call_repo = mock_call_repo_cls.return_value
        mock_call_repo.get_by_id = AsyncMock(return_value=call)

        mock_risk_repo = mock_risk_repo_cls.return_value
        mock_risk_repo.get_call_events = AsyncMock(return_value=[event])

        events = await RiskEventService.get_call_events(db, user, str(CALL_ID))
        assert len(events) == 1
        assert events[0].id == str(EVENT_ID)

@pytest.mark.anyio
async def test_get_latest_event():
    db = AsyncMock()
    user = mock_user()
    call = mock_call()
    event = mock_risk_event()

    with patch('app.services.risk_event_service.CallSessionRepository') as mock_call_repo_cls, \
         patch('app.services.risk_event_service.RiskEventRepository') as mock_risk_repo_cls:

        mock_call_repo = mock_call_repo_cls.return_value
        mock_call_repo.get_by_id = AsyncMock(return_value=call)

        mock_risk_repo = mock_risk_repo_cls.return_value
        mock_risk_repo.get_latest_event = AsyncMock(return_value=event)

        latest = await RiskEventService.get_latest_event(db, user, str(CALL_ID))
        assert latest is not None
        assert latest.id == str(EVENT_ID)
