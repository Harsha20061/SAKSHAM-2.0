import asyncio
import uuid

import uuid
import pytest

from fastapi.testclient import TestClient
from unittest.mock import patch



from app.main import app
from app.db.models.user import User


client = TestClient(app)


@pytest.fixture
def mock_authenticate_analysis_ws():
    with patch(
        "app.api.routes.analysis.authenticate_analysis_ws"
    ) as mock_auth:
        yield mock_auth


@pytest.fixture
def mock_validate_connection():
    with patch(
        "app.api.routes.analysis.SignalingService.validate_connection"
    ) as mock_validate:
        yield mock_validate


def test_analysis_ws_missing_token():
    try:
        with client.websocket_connect(
            "/api/analysis/ws/test-session"
        ):
            pass

        assert False, "Should have disconnected"

    except Exception as exc:
        assert (
            getattr(exc, "code", None) == 1008
            or "1008" in repr(exc)
        )


def test_analysis_ws_invalid_token(
    mock_authenticate_analysis_ws,
):
    mock_authenticate_analysis_ws.return_value = None

    try:
        with client.websocket_connect(
            "/api/analysis/ws/test-session?token=invalid"
        ):
            pass

        assert False, "Should have disconnected"

    except Exception as exc:
        assert (
            getattr(exc, "code", None) == 1008
            or "1008" in repr(exc)
        )


def test_analysis_ws_invalid_session(
    mock_authenticate_analysis_ws,
):
    mock_user = User(
        id=uuid.uuid4(),
        username="test",
    )

    mock_authenticate_analysis_ws.return_value = mock_user

    try:
        with client.websocket_connect(
            "/api/analysis/ws/not-a-uuid?token=valid"
        ):
            pass

        assert False, "Should have disconnected"

    except Exception as exc:
        assert (
            getattr(exc, "code", None) == 1008
            or "1008" in repr(exc)
        )


def test_analysis_ws_connection_ready(
    mock_authenticate_analysis_ws,
    mock_validate_connection,
):
    mock_user = User(
        id=uuid.uuid4(),
        username="test",
    )

    mock_authenticate_analysis_ws.return_value = mock_user

    session_id = str(uuid.uuid4())

    with client.websocket_connect(
        f"/api/analysis/ws/{session_id}?token=valid"
    ) as websocket:

        data = websocket.receive_json()

        assert data["type"] == "analysis_ready"
        assert data["session_id"] == session_id

    mock_validate_connection.assert_awaited_once()


def test_analysis_ws_start_and_result(
    mock_authenticate_analysis_ws,
    mock_validate_connection,
):
    mock_user = User(
        id=uuid.uuid4(),
        username="test",
    )

    mock_authenticate_analysis_ws.return_value = mock_user

    session_id = str(uuid.uuid4())

    with client.websocket_connect(
        f"/api/analysis/ws/{session_id}?token=valid"
    ) as websocket:

        # ---------------------------------------------
        # Initial ready message
        # ---------------------------------------------

        ready = websocket.receive_json()

        assert ready["type"] == "analysis_ready"

        # ---------------------------------------------
        # Start analysis
        # ---------------------------------------------

        websocket.send_json(
            {
                "type": "analysis_start",
                "session_id": session_id,
                "payload": {
                    "scenario": "HIGH"
                },
            }
        )

        started = websocket.receive_json()

        assert started["type"] == "analysis_started"
        assert started["session_id"] == session_id
        assert started["payload"]["scenario"] == "HIGH"

        # ---------------------------------------------
        # Receive mock analysis result
        # ---------------------------------------------

        result = websocket.receive_json()

        assert result["type"] == "analysis_result"
        assert result["session_id"] == session_id

        payload = result["payload"]

        assert "spoof_probability" in payload
        assert "speaker_similarity" in payload
        assert "scam_score" in payload
        assert "risk_score" in payload
        assert "risk_level" in payload
        assert "indicators" in payload
        assert "latency_ms" in payload

        assert payload["risk_level"] == "HIGH"

        assert 0.0 <= payload["spoof_probability"] <= 1.0
        assert 0.0 <= payload["speaker_similarity"] <= 1.0
        assert 0.0 <= payload["scam_score"] <= 1.0
        assert 0.0 <= payload["risk_score"] <= 1.0

        # ---------------------------------------------
        # Stop analysis
        # ---------------------------------------------

        websocket.send_json(
            {
                "type": "analysis_stop",
                "session_id": session_id,
                "payload": {},
            }
        )

        stopped = websocket.receive_json()

        assert stopped["type"] == "analysis_stopped"
        assert stopped["session_id"] == session_id


def test_analysis_ws_scenario_defaults_to_low(
    mock_authenticate_analysis_ws,
    mock_validate_connection,
):
    mock_user = User(
        id=uuid.uuid4(),
        username="test",
    )

    mock_authenticate_analysis_ws.return_value = mock_user

    session_id = str(uuid.uuid4())

    with client.websocket_connect(
        f"/api/analysis/ws/{session_id}?token=valid"
    ) as websocket:

        ready = websocket.receive_json()

        assert ready["type"] == "analysis_ready"

        websocket.send_json(
            {
                "type": "analysis_start",
                "session_id": session_id,
                "payload": {},
            }
        )

        started = websocket.receive_json()

        assert started["type"] == "analysis_started"
        assert started["payload"]["scenario"] == "LOW"

        result = websocket.receive_json()

        assert result["type"] == "analysis_result"
        assert result["payload"]["risk_level"] == "LOW"

        websocket.send_json(
            {
                "type": "analysis_stop",
                "session_id": session_id,
                "payload": {},
            }
        )

        stopped = websocket.receive_json()

        assert stopped["type"] == "analysis_stopped"


def test_analysis_ws_invalid_scenario_defaults_to_low(
    mock_authenticate_analysis_ws,
    mock_validate_connection,
):
    mock_user = User(
        id=uuid.uuid4(),
        username="test",
    )

    mock_authenticate_analysis_ws.return_value = mock_user

    session_id = str(uuid.uuid4())

    with client.websocket_connect(
        f"/api/analysis/ws/{session_id}?token=valid"
    ) as websocket:

        websocket.receive_json()

        websocket.send_json(
            {
                "type": "analysis_start",
                "session_id": session_id,
                "payload": {
                    "scenario": "INVALID"
                },
            }
        )

        started = websocket.receive_json()

        assert started["type"] == "analysis_started"
        assert started["payload"]["scenario"] == "LOW"

        result = websocket.receive_json()

        assert result["type"] == "analysis_result"
        assert result["payload"]["risk_level"] == "LOW"

        websocket.send_json(
            {
                "type": "analysis_stop",
                "session_id": session_id,
                "payload": {},
            }
        )

        stopped = websocket.receive_json()

        assert stopped["type"] == "analysis_stopped"


def test_analysis_ws_ping(
    mock_authenticate_analysis_ws,
    mock_validate_connection,
):
    mock_user = User(
        id=uuid.uuid4(),
        username="test",
    )

    mock_authenticate_analysis_ws.return_value = mock_user

    session_id = str(uuid.uuid4())

    with client.websocket_connect(
        f"/api/analysis/ws/{session_id}?token=valid"
    ) as websocket:

        websocket.receive_json()

        websocket.send_json(
            {
                "type": "ping",
                "session_id": session_id,
                "payload": {},
            }
        )

        response = websocket.receive_json()

        assert response["type"] == "pong"
        assert response["session_id"] == session_id