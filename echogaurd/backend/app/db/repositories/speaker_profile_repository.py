import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.speaker_profile import SpeakerProfile


class SpeakerProfileRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_contact_id(self, contact_id: uuid.UUID) -> Optional[SpeakerProfile]:
        result = await self.db.execute(
            select(SpeakerProfile)
            .where(SpeakerProfile.contact_id == contact_id)
            .order_by(SpeakerProfile.created_at.desc())
        )
        return result.scalars().first()

    async def get_active_by_contact_id(self, contact_id: uuid.UUID) -> Optional[SpeakerProfile]:
        result = await self.db.execute(
            select(SpeakerProfile).where(
                (SpeakerProfile.contact_id == contact_id)
                & (SpeakerProfile.status == "ACTIVE")
            ).order_by(SpeakerProfile.created_at.desc())
        )
        return result.scalars().first()

    async def create(
        self,
        *,
        contact_id: uuid.UUID,
        embedding: list[float],
        embedding_dimension: int,
        model_name: str,
        model_version: str,
        sample_rate: int,
        consent_timestamp: datetime,
        status: str = "ACTIVE",
    ) -> SpeakerProfile:
        profile = SpeakerProfile(
            contact_id=contact_id,
            embedding=embedding,
            embedding_dimension=embedding_dimension,
            model_name=model_name,
            model_version=model_version,
            sample_rate=sample_rate,
            status=status,
            consent_timestamp=consent_timestamp,
        )
        self.db.add(profile)
        return profile

    async def set_revoked(self, profile: SpeakerProfile) -> SpeakerProfile:
        profile.status = "REVOKED"
        profile.revoked_at = datetime.utcnow()
        return profile

    async def delete(self, profile: SpeakerProfile) -> None:
        await self.db.delete(profile)
