import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.risk_event import RiskEvent, RiskLevel

class RiskEventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        call_id: uuid.UUID,
        spoof_probability: float,
        speaker_similarity: float | None,
        scam_score: float,
        risk_score: float,
        risk_level: RiskLevel,
        latency_ms: float,
        indicators: List[str]
    ) -> RiskEvent:
        risk_event = RiskEvent(
            call_id=call_id,
            spoof_probability=spoof_probability,
            speaker_similarity=speaker_similarity,
            scam_score=scam_score,
            risk_score=risk_score,
            risk_level=risk_level,
            latency_ms=latency_ms,
            indicators=indicators
        )
        self.db.add(risk_event)
        return risk_event

    async def get_by_id(self, event_id: uuid.UUID) -> Optional[RiskEvent]:
        result = await self.db.execute(select(RiskEvent).filter(RiskEvent.id == event_id))
        return result.scalar_one_or_none()

    async def get_call_events(self, call_id: uuid.UUID) -> List[RiskEvent]:
        result = await self.db.execute(
            select(RiskEvent)
            .filter(RiskEvent.call_id == call_id)
            .order_by(RiskEvent.timestamp.asc())
        )
        return list(result.scalars().all())

    async def get_latest_event(self, call_id: uuid.UUID) -> Optional[RiskEvent]:
        result = await self.db.execute(
            select(RiskEvent)
            .filter(RiskEvent.call_id == call_id)
            .order_by(RiskEvent.timestamp.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
