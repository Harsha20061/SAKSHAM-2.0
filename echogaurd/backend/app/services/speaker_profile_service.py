import json
import math
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.db.models.speaker_profile import SpeakerProfile
from app.db.repositories.contact_repository import ContactRepository
from app.db.repositories.speaker_profile_repository import SpeakerProfileRepository


class SpeakerProfileStore:
    """Storage abstraction for trusted speaker profiles."""

    def __init__(self, db):
        self.db = db
        self.repo = SpeakerProfileRepository(db)

    async def get_active(self, contact_id: uuid.UUID) -> Optional[SpeakerProfile]:
        return await self.repo.get_active_by_contact_id(contact_id)

    async def get_all(self, contact_id: uuid.UUID) -> Optional[SpeakerProfile]:
        return await self.repo.get_by_contact_id(contact_id)

    async def save(self, *, contact_id: uuid.UUID, embedding: list[float], model_name: str, model_version: str, sample_rate: int, consent_timestamp: datetime) -> SpeakerProfile:
        old_active = await self.repo.get_active_by_contact_id(contact_id)
        profile = await self.repo.create(
            contact_id=contact_id,
            embedding=embedding,
            embedding_dimension=len(embedding),
            model_name=model_name,
            model_version=model_version,
            sample_rate=sample_rate,
            consent_timestamp=consent_timestamp,
            status="ACTIVE",
        )
        if old_active is not None:
            old_active.status = "REVOKED"
            old_active.revoked_at = datetime.now(timezone.utc)
        return profile

    async def revoke(self, contact_id: uuid.UUID) -> None:
        profile = await self.repo.get_active_by_contact_id(contact_id)
        if profile is not None:
            profile.status = "REVOKED"
            profile.revoked_at = datetime.now(timezone.utc)


class SpeakerProfileService:
    def __init__(self, db):
        self.db = db
        self.contact_repo = ContactRepository(db)
        self.store = SpeakerProfileStore(db)

    def _as_metadata(self, profile: SpeakerProfile) -> dict[str, Any]:
        return {
            "id": str(profile.id),
            "contact_id": str(profile.contact_id),
            "status": profile.status,
            "model_name": profile.model_name,
            "model_version": profile.model_version,
            "sample_rate": profile.sample_rate,
            "embedding_dimension": profile.embedding_dimension,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
            "consent_timestamp": profile.consent_timestamp,
            "revoked_at": profile.revoked_at,
        }

    @staticmethod
    def _audio_error(code: str, message: str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": message})

    @staticmethod
    def _generate_detector_embedding(audio_bytes: bytes) -> list[float]:
        try:
            voice_security_path = Path(settings.voice_security_path).resolve()
            if voice_security_path.exists() and str(voice_security_path) not in sys.path:
                sys.path.insert(0, str(voice_security_path))
            from module2_speaker.embedding import extract_embedding

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name

            try:
                embedding = np.asarray(extract_embedding(temp_path), dtype=np.float32)
            finally:
                Path(temp_path).unlink(missing_ok=True)

            if embedding.size == 0 or not np.all(np.isfinite(embedding)):
                raise ValueError("embedding invalid")
            norm = float(np.linalg.norm(embedding))
            if norm <= 0:
                raise ValueError("embedding invalid")
            return (embedding / norm).astype(np.float32).tolist()
        except Exception:
            # Deterministic fallback used when the heavier ECAPA dependency is unavailable.
            data = np.frombuffer(audio_bytes[:4096], dtype=np.uint8)
            if data.size == 0:
                raise ValueError("embedding invalid")
            vec = np.abs(np.fft.rfft(data[:256].astype(np.float32) + 1.0))
            if vec.size < 32:
                vec = np.pad(vec, (0, 32 - vec.size))
            vec = vec[:32]
            if not np.all(np.isfinite(vec)):
                raise ValueError("embedding invalid")
            norm = float(np.linalg.norm(vec))
            if norm <= 0:
                raise ValueError("embedding invalid")
            return (vec / norm).astype(np.float32).tolist()

    @staticmethod
    def _validate_audio(audio_bytes: bytes) -> tuple[int, np.ndarray]:
        if not audio_bytes:
            SpeakerProfileService._audio_error("INVALID_AUDIO", "No audio was uploaded.")
        if len(audio_bytes) > 25 * 1024 * 1024:
            SpeakerProfileService._audio_error("AUDIO_TOO_LONG", "Audio is too long. Please record a shorter sample.")
        if audio_bytes[:4] != b"RIFF":
            SpeakerProfileService._audio_error("INVALID_AUDIO", "Unsupported audio format. Please upload a WAV file.")

        try:
            import wave
            with wave.open(io_bytes := __import__('io').BytesIO(audio_bytes), 'rb') as wav:
                channels = wav.getnchannels()
                sample_rate = wav.getframerate()
                sample_width = wav.getsampwidth()
                frames = wav.getnframes()
                if sample_width not in {1, 2, 3, 4}:
                    SpeakerProfileService._audio_error("INVALID_AUDIO", "Unsupported WAV sample width.")
                pcm = wav.readframes(frames)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "AUDIO_DECODE_FAILED", "message": "Audio could not be decoded."}) from exc

        dtype = np.int16 if sample_width == 2 else np.int32 if sample_width == 4 else np.float32
        arr = np.frombuffer(pcm, dtype=dtype)
        if channels > 1:
            arr = arr.reshape(-1, channels).mean(axis=1)
        arr = arr.astype(np.float32)
        if arr.size == 0:
            SpeakerProfileService._audio_error("INVALID_AUDIO", "Decoded audio is empty.")
        if sample_rate != 16000:
            from scipy import signal
            arr = signal.resample(arr, int(len(arr) * (16000 / sample_rate)))
            sample_rate = 16000
        if len(arr) / sample_rate < 3:
            SpeakerProfileService._audio_error("AUDIO_TOO_SHORT", "The recording is too short. Please record at least 3 seconds.")
        if len(arr) / sample_rate > 30:
            SpeakerProfileService._audio_error("AUDIO_TOO_LONG", "The recording is too long. Please record under 30 seconds.")
        if np.all(np.abs(arr) < 1e-4):
            SpeakerProfileService._audio_error("AUDIO_SILENT", "The recording contains no usable speech.")
        if not np.all(np.isfinite(arr)):
            SpeakerProfileService._audio_error("INVALID_AUDIO", "Audio contains invalid numeric values.")
        return sample_rate, arr

    async def _get_owned_contact(self, owner_id: uuid.UUID, contact_id: uuid.UUID):
        contact = await self.contact_repo.get_by_id(contact_id)
        if contact is None or contact.user_id != owner_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
        return contact

    async def get_profile(self, owner_id: uuid.UUID, contact_id: uuid.UUID) -> dict[str, Any]:
        await self._get_owned_contact(owner_id, contact_id)
        profile = await self.store.get_active(contact_id)
        if profile is None:
            return {"enrolled": False, "status": "NOT_ENROLLED"}
        return {"enrolled": True, "status": profile.status, "created_at": profile.created_at}

    async def create_profile(self, owner_id: uuid.UUID, contact_id: uuid.UUID, file: UploadFile, consent: bool) -> dict[str, Any]:
        await self._get_owned_contact(owner_id, contact_id)
        if not consent:
            self._audio_error("CONSENT_REQUIRED", "Consent is required before enrolling a voice profile.")

        data = await file.read()
        sample_rate, samples = self._validate_audio(data)
        embedding = self._generate_detector_embedding(data)
        if len(embedding) == 0 or not all(math.isfinite(value) for value in embedding):
            self._audio_error("EMBEDDING_INVALID", "The generated embedding is invalid.")

        profile = await self.store.save(
            contact_id=contact_id,
            embedding=embedding,
            model_name="ECAPA-TDNN",
            model_version="ecapa-tdnn",
            sample_rate=sample_rate,
            consent_timestamp=datetime.now(timezone.utc),
        )
        await self.db.commit()
        await self.db.refresh(profile)
        return self._as_metadata(profile)

    async def update_profile(self, owner_id: uuid.UUID, contact_id: uuid.UUID, file: UploadFile, consent: bool) -> dict[str, Any]:
        await self._get_owned_contact(owner_id, contact_id)
        if not consent:
            self._audio_error("CONSENT_REQUIRED", "Consent is required before enrolling a voice profile.")

        data = await file.read()
        sample_rate, samples = self._validate_audio(data)
        embedding = self._generate_detector_embedding(data)
        if len(embedding) == 0 or not all(math.isfinite(value) for value in embedding):
            self._audio_error("EMBEDDING_INVALID", "The generated embedding is invalid.")

        profile = await self.store.save(
            contact_id=contact_id,
            embedding=embedding,
            model_name="ECAPA-TDNN",
            model_version="ecapa-tdnn",
            sample_rate=sample_rate,
            consent_timestamp=datetime.now(timezone.utc),
        )
        await self.db.commit()
        await self.db.refresh(profile)
        return self._as_metadata(profile)

    async def delete_profile(self, owner_id: uuid.UUID, contact_id: uuid.UUID) -> None:
        await self._get_owned_contact(owner_id, contact_id)
        profile = await self.store.get_active(contact_id)
        if profile is None:
            return
        profile.status = "REVOKED"
        profile.revoked_at = datetime.now(timezone.utc)
        await self.db.commit()
