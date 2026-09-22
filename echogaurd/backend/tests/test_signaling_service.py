import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.signaling_service import SignalingService
from app.db.models.call_session import CallSession, CallStatus
from app.db.models.user import User

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def caller():
    return User(id=uuid.uuid4(), username="caller")

@pytest.fixture
def receiver():
    return User(id=uuid.uuid4(), username="receiver")

@pytest.fixture
def active_call(caller, receiver):
    return CallSession(
        id=uuid.uuid4(),
        caller_id=caller.id,
        receiver_id=receiver.id,
        status=CallStatus.ACTIVE
    )

@pytest.mark.anyio
async def test_validate_connection_success(mock_db, caller, active_call):
    with patch("app.services.signaling_service.CallSessionRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_by_id = AsyncMock(return_value=active_call)

        call = await SignalingService.validate_connection(mock_db, str(active_call.id), caller)
        assert call.id == active_call.id

@pytest.mark.anyio
async def test_validate_connection_not_participant(mock_db, active_call):
    other_user = User(id=uuid.uuid4(), username="other")
    with patch("app.services.signaling_service.CallSessionRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_by_id = AsyncMock(return_value=active_call)

        with pytest.raises(ValueError, match="Not a participant"):
            await SignalingService.validate_connection(mock_db, str(active_call.id), other_user)

@pytest.mark.anyio
async def test_validate_connection_ended_call(mock_db, caller, active_call):
    active_call.status = CallStatus.ENDED
    with patch("app.services.signaling_service.CallSessionRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_by_id = AsyncMock(return_value=active_call)

        with pytest.raises(ValueError, match="Call is already terminated"):
            await SignalingService.validate_connection(mock_db, str(active_call.id), caller)

@pytest.mark.anyio
@patch("app.services.signaling_service.manager.send_to_user")
async def test_process_message_offer(mock_send_to_user, mock_db, caller, receiver, active_call):
    with patch("app.services.signaling_service.CallSessionRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_by_id = AsyncMock(return_value=active_call)

        msg = {
            "type": "call_offer",
            "session_id": str(active_call.id),
            "payload": {"sdp": "offer-sdp"}
        }

        await SignalingService.process_message(mock_db, str(active_call.id), caller, msg)
        mock_send_to_user.assert_called_once_with(str(active_call.id), str(receiver.id), msg)

@pytest.mark.anyio
@patch("app.services.signaling_service.manager.send_to_user")
@patch("app.services.signaling_service.CallService.end_call")
async def test_process_message_end_call(mock_end_call, mock_send_to_user, mock_db, caller, receiver, active_call):
    with patch("app.services.signaling_service.CallSessionRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_by_id = AsyncMock(return_value=active_call)

        msg = {
            "type": "call_end",
            "session_id": str(active_call.id),
            "payload": {}
        }

        await SignalingService.process_message(mock_db, str(active_call.id), caller, msg)
        mock_send_to_user.assert_called_once_with(str(active_call.id), str(receiver.id), msg)
        mock_end_call.assert_called_once_with(mock_db, caller, active_call.id)
