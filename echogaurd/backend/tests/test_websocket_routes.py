import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
from app.db.models.user import User
import uuid
import time

client = TestClient(app)

@pytest.fixture
def mock_authenticate_ws():
    with patch("app.api.routes.websocket.authenticate_ws") as mock_auth:
        yield mock_auth

@pytest.fixture
def mock_signaling_service():
    with patch("app.api.routes.websocket.SignalingService") as mock_ss:
        mock_ss.validate_connection = AsyncMock()
        mock_ss.process_message = AsyncMock()
        yield mock_ss

def test_websocket_missing_token():
    try:
        with client.websocket_connect("/api/ws/test-session"):
            pass
        assert False, "Should have disconnected"
    except Exception as e:
        assert getattr(e, "code", None) == 1008 or "1008" in repr(e)

def test_websocket_invalid_token(mock_authenticate_ws):
    mock_authenticate_ws.return_value = None
    try:
        with client.websocket_connect("/api/ws/test-session?token=invalid"):
            pass
        assert False, "Should have disconnected"
    except Exception as e:
        assert getattr(e, "code", None) == 1008 or "1008" in repr(e)

def test_websocket_invalid_session(mock_authenticate_ws, mock_signaling_service):
    mock_user = User(id=uuid.uuid4(), username="test")
    mock_authenticate_ws.return_value = mock_user
    mock_signaling_service.validate_connection.side_effect = ValueError("Not a participant")
    try:
        with client.websocket_connect("/api/ws/test-session?token=valid"):
            pass
        assert False, "Should have disconnected"
    except Exception as e:
        assert getattr(e, "code", None) == 1008 or "1008" in repr(e)

def test_websocket_ping_pong(mock_authenticate_ws, mock_signaling_service):
    mock_user = User(id=uuid.uuid4(), username="test")
    mock_authenticate_ws.return_value = mock_user
    with client.websocket_connect("/api/ws/test-session?token=valid") as websocket:
        websocket.send_json({
            "type": "ping",
            "session_id": "test-session",
            "payload": {}
        })
        data = websocket.receive_json()
        assert data["type"] == "pong"
        assert data["session_id"] == "test-session"

def test_websocket_unknown_message(mock_authenticate_ws, mock_signaling_service):
    mock_user = User(id=uuid.uuid4(), username="test")
    mock_authenticate_ws.return_value = mock_user
    with client.websocket_connect("/api/ws/test-session?token=valid") as websocket:
        websocket.send_json({
            "type": "unknown",
            "session_id": "test-session",
            "payload": {}
        })
        data = websocket.receive_json()
        assert data["type"] == "error"
        assert data["payload"]["code"] == "UNKNOWN_MESSAGE_TYPE"

def test_websocket_malformed_json(mock_authenticate_ws, mock_signaling_service):
    mock_user = User(id=uuid.uuid4(), username="test")
    mock_authenticate_ws.return_value = mock_user
    with client.websocket_connect("/api/ws/test-session?token=valid") as websocket:
        websocket.send_text("this is not json")
        data = websocket.receive_json()
        assert data["type"] == "error"
        assert data["payload"]["code"] == "INVALID_FORMAT"

def test_websocket_hello(mock_authenticate_ws, mock_signaling_service):
    mock_user = User(id=uuid.uuid4(), username="test")
    mock_authenticate_ws.return_value = mock_user
    with client.websocket_connect("/api/ws/test-session?token=valid") as websocket:
        websocket.send_json({
            "type": "hello",
            "session_id": "test-session",
            "payload": {}
        })
        data = websocket.receive_json()
        assert data["type"] == "hello_ack"
        assert data["payload"]["message"] == "Welcome"

def test_websocket_signaling(mock_authenticate_ws, mock_signaling_service):
    mock_user = User(id=uuid.uuid4(), username="test")
    mock_authenticate_ws.return_value = mock_user

    with client.websocket_connect(
        "/api/ws/test-session?token=valid"
    ) as websocket:

        websocket.send_json({
            "type": "call_offer",
            "session_id": "test-session",
            "payload": {
                "sdp": "...",
                "type": "offer"
            }
        })

        # Give the WebSocket handler time to process
        # the message before checking the async mock.
        time.sleep(0.1)

        mock_signaling_service.process_message.assert_called_once()