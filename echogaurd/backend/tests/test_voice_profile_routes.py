import datetime
import uuid
import wave
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.db.models.user import User
from app.main import app

client = TestClient(app)
OWNER_ID = uuid.uuid4()
CONTACT_ID = uuid.uuid4()


def _mock_owner():
    user = MagicMock(spec=User)
    user.id = OWNER_ID
    user.username = "owner"
    user.display_name = "Owner"
    user.created_at = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    return user


def _override_auth(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides():
    app.dependency_overrides = {}


def _wav_bytes():
    import io

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        samples = [0, 2000, -2000, 0] * 250
        wav_file.writeframes((__import__('array').array("h", samples)).tobytes())
    return buffer.getvalue()


def test_get_voice_profile_not_enrolled():
    _override_auth(_mock_owner())
    with patch("app.api.routes.contacts.SpeakerProfileService") as MockSvc:
        MockSvc.return_value.get_profile = AsyncMock(return_value={"enrolled": False, "status": "NOT_ENROLLED"})
        response = client.get(f"/api/contacts/{CONTACT_ID}/voice-profile")
    assert response.status_code == 200
    assert response.json()["status"] == "NOT_ENROLLED"
    _clear_overrides()


def test_create_voice_profile_requires_consent():
    _override_auth(_mock_owner())
    with patch("app.api.routes.contacts.SpeakerProfileService") as MockSvc:
        MockSvc.return_value.create_profile = AsyncMock(
            side_effect=HTTPException(status_code=400, detail={"code": "CONSENT_REQUIRED", "message": "Consent is required"})
        )
        response = client.post(
            f"/api/contacts/{CONTACT_ID}/voice-profile",
            files={"file": ("sample.wav", _wav_bytes(), "audio/wav")},
            data={"consent": "false"},
        )
    assert response.status_code == 400
    _clear_overrides()
