import uuid
import datetime
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import get_current_user
from app.db.models.user import User

client = TestClient(app)

USER_ID = uuid.uuid4()
CALL_ID = uuid.uuid4()
EVENT_ID = uuid.uuid4()

def _mock_user():
    u = MagicMock(spec=User)
    u.id = USER_ID
    u.username = "testuser"
    return u

@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = _mock_user
    yield
    app.dependency_overrides.clear()

# Mock RiskEventResponse
class MockRiskEventResponse:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def dict(self):
        return {
            "id": self.id,
            "call_id": self.call_id,
            "spoof_probability": self.spoof_probability,
            "speaker_similarity": self.speaker_similarity,
            "scam_score": self.scam_score,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "indicators": self.indicators,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp.isoformat()
        }

def make_mock_response():
    return MockRiskEventResponse(
        id=str(EVENT_ID),
        call_id=str(CALL_ID),
        spoof_probability=0.92,
        speaker_similarity=0.21,
        scam_score=0.88,
        risk_score=0.87,
        risk_level="HIGH",
        indicators=["money_request", "urgency"],
        latency_ms=640,
        timestamp=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    )

def test_create_risk_event_route():
    payload = {
        "spoof_probability": 0.92,
        "speaker_similarity": 0.21,
        "scam_score": 0.88,
        "risk_score": 0.87,
        "risk_level": "HIGH",
        "indicators": ["money_request", "urgency"],
        "latency_ms": 640
    }

    with patch('app.api.routes.risk_events.RiskEventService.create_risk_event', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = make_mock_response()

        response = client.post(f"/api/calls/{CALL_ID}/risk-events", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] == "HIGH"
        assert data["spoof_probability"] == 0.92

def test_get_risk_events_route():
    with patch('app.api.routes.risk_events.RiskEventService.get_call_events', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = [make_mock_response()]

        response = client.get(f"/api/calls/{CALL_ID}/risk-events")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["risk_level"] == "HIGH"

def test_get_latest_risk_event_route():
    with patch('app.api.routes.risk_events.RiskEventService.get_latest_event', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = make_mock_response()

        response = client.get(f"/api/calls/{CALL_ID}/risk-events/latest")
        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] == "HIGH"
        assert "urgency" in data["indicators"]

def test_get_latest_risk_event_route_not_found():
    with patch('app.api.routes.risk_events.RiskEventService.get_latest_event', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None

        response = client.get(f"/api/calls/{CALL_ID}/risk-events/latest")
        assert response.status_code == 404

def test_create_risk_event_validation_error():
    payload = {
        "spoof_probability": 1.5,  # Invalid
        "speaker_similarity": 0.21,
        "scam_score": 0.88,
        "risk_score": 0.87,
        "risk_level": "HIGH",
        "indicators": ["money_request", "urgency"],
        "latency_ms": 640
    }

    response = client.post(f"/api/calls/{CALL_ID}/risk-events", json=payload)
    assert response.status_code == 422

def test_create_risk_event_unauthorized():
    app.dependency_overrides.clear()
    payload = {
        "spoof_probability": 0.1,
        "speaker_similarity": 0.9,
        "scam_score": 0.1,
        "risk_score": 0.1,
        "risk_level": "LOW",
        "indicators": [],
        "latency_ms": 100
    }
    response = client.post(f"/api/calls/{CALL_ID}/risk-events", json=payload)
    assert response.status_code == 401
