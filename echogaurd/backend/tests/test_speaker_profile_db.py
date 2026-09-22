import asyncio
import io
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import Base
from app.db.models.contact import Contact
from app.db.models.speaker_profile import SpeakerProfile
from app.db.models.user import User
from app.services.ai_service import AIService
from app.services.speaker_profile_service import SpeakerProfileService, SpeakerProfileStore

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIO_DIR = PROJECT_ROOT / "VoiceSecurity" / "audio"
GENUINE_WAV = AUDIO_DIR / "genuine_fixed.wav"
OTHER_WAV = AUDIO_DIR / "other_person_fixed.wav"


async def _with_db_session(test_fn):
    SpeakerProfile.__table_args__ = ()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await test_fn(session)

    await engine.dispose()


@pytest.fixture
def genuine_embedding():
    return SpeakerProfileService._generate_detector_embedding(GENUINE_WAV.read_bytes())


@pytest.fixture
def other_embedding():
    return SpeakerProfileService._generate_detector_embedding(OTHER_WAV.read_bytes())


def test_db_backed_verification_uses_in_memory_embedding(genuine_embedding):
    similarity, status = AIService.compare_with_profile(genuine_embedding, genuine_embedding)
    assert status == "VERIFIED"
    assert similarity == pytest.approx(1.0, abs=1e-6)

    similarity, status = AIService.compare_with_profile(genuine_embedding, np.array([0.0] * len(genuine_embedding)))
    assert status == "MISMATCH"
    assert similarity < 0.75

    similarity, status = AIService.compare_with_profile(genuine_embedding, None)
    assert similarity is None
    assert status == "NOT_ENROLLED"


def test_re_enrollment_keeps_only_one_active_profile(genuine_embedding):
    first = SpeakerProfile(
        id=uuid.uuid4(),
        contact_id=uuid.uuid4(),
        embedding=genuine_embedding,
        embedding_dimension=len(genuine_embedding),
        model_name="ECAPA-TDNN",
        model_version="ecapa-tdnn",
        sample_rate=16000,
        status="ACTIVE",
        consent_timestamp=datetime.now(timezone.utc),
    )
    second = SpeakerProfile(
        id=uuid.uuid4(),
        contact_id=first.contact_id,
        embedding=[value * 0.9 for value in genuine_embedding],
        embedding_dimension=len(genuine_embedding),
        model_name="ECAPA-TDNN",
        model_version="ecapa-tdnn",
        sample_rate=16000,
        status="ACTIVE",
        consent_timestamp=datetime.now(timezone.utc),
    )

    first.status = "REVOKED"
    active_profiles = [profile for profile in [first, second] if profile.status == "ACTIVE"]

    assert len(active_profiles) == 1
    assert active_profiles[0].id == second.id
    assert first.status == "REVOKED"
    assert second.status == "ACTIVE"


def test_failed_re_enrollment_preserves_old_active_profile(genuine_embedding):
    async def _run(session):
        owner = User(id=uuid.uuid4(), username="owner", display_name="Owner")
        contact = Contact(id=uuid.uuid4(), user_id=owner.id, contact_user_id=uuid.uuid4(), nickname="Buddy", is_trusted=True)
        session.add_all([owner, contact])
        await session.commit()

        store = SpeakerProfileStore(session)
        original = await store.save(
            contact_id=contact.id,
            embedding=genuine_embedding,
            model_name="ECAPA-TDNN",
            model_version="ecapa-tdnn",
            sample_rate=16000,
            consent_timestamp=datetime.now(timezone.utc),
        )
        await session.commit()

        svc = SpeakerProfileService(session)
        invalid_file = UploadFile(filename="bad.wav", file=io.BytesIO(b"not-a-real-wav-file"))

        with pytest.raises(Exception):
            await svc.update_profile(owner.id, contact.id, invalid_file, consent=True)

        await session.refresh(original)
        assert original.status == "ACTIVE"

    asyncio.run(_with_db_session(_run))


def test_live_verification_works_without_legacy_npy(genuine_embedding, tmp_path):
    missing_contact_id = uuid.uuid4()
    legacy_npy = tmp_path / "legacy-speaker-database" / f"{missing_contact_id}.npy"
    assert not legacy_npy.exists()

    active_profile = SpeakerProfile(
        id=uuid.uuid4(),
        contact_id=missing_contact_id,
        embedding=genuine_embedding,
        embedding_dimension=len(genuine_embedding),
        model_name="ECAPA-TDNN",
        model_version="ecapa-tdnn",
        sample_rate=16000,
        status="ACTIVE",
        consent_timestamp=datetime.now(timezone.utc),
    )

    similarity, status = AIService.compare_with_profile(genuine_embedding, active_profile.embedding)
    assert status == "VERIFIED"
    assert similarity == pytest.approx(1.0, abs=1e-6)
    assert legacy_npy.exists() is False


def test_revoked_profile_is_not_used_for_verification(genuine_embedding):
    async def _run(session):
        owner = User(id=uuid.uuid4(), username="owner", display_name="Owner")
        contact = Contact(id=uuid.uuid4(), user_id=owner.id, contact_user_id=uuid.uuid4(), nickname="Buddy", is_trusted=True)
        session.add_all([owner, contact])
        await session.commit()

        store = SpeakerProfileStore(session)
        profile = await store.save(
            contact_id=contact.id,
            embedding=genuine_embedding,
            model_name="ECAPA-TDNN",
            model_version="ecapa-tdnn",
            sample_rate=16000,
            consent_timestamp=datetime.now(timezone.utc),
        )
        await session.commit()

        profile.status = "REVOKED"
        profile.revoked_at = datetime.now(timezone.utc)
        await session.commit()

        active_profile = await store.get_active(contact.id)
        assert active_profile is None

    asyncio.run(_with_db_session(_run))
