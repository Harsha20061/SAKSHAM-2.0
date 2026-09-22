import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.db.models.user import User
from app.db.models.call_session import CallStatus
from app.db.repositories.call_session_repository import CallSessionRepository
from app.db.repositories.risk_event_repository import RiskEventRepository
from app.models.schemas import RiskEventRequest, RiskEventResponse
from app.db.models.risk_event import RiskLevel
from app.models.schemas import CallSecurityReportResponse

class RiskEventService:
    @staticmethod
    async def create_risk_event(
        db: AsyncSession,
        current_user: User,
        call_id: str,
        request: RiskEventRequest
    ) -> RiskEventResponse:
        try:
            call_uuid = uuid.UUID(call_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid call ID")

        call_repo = CallSessionRepository(db)
        call = await call_repo.get_by_id(call_uuid)

        if not call:
            raise HTTPException(status_code=404, detail="Call not found")

        # Participant check
        if current_user.id != call.caller_id and current_user.id != call.receiver_id:
            raise HTTPException(status_code=404, detail="Call not found")

        # Status check
        if call.status in [CallStatus.ENDED, CallStatus.FAILED]:
            raise HTTPException(status_code=400, detail="Cannot create risk event for a terminal call")

        # Map string enum to db enum
        risk_level_enum = RiskLevel(request.risk_level)

        risk_repo = RiskEventRepository(db)
        event = await risk_repo.create(
            call_id=call_uuid,
            spoof_probability=request.spoof_probability,
            speaker_similarity=request.speaker_similarity,
            scam_score=request.scam_score,
            risk_score=request.risk_score,
            risk_level=risk_level_enum,
            latency_ms=request.latency_ms,
            indicators=request.indicators
        )

        await db.commit()
        await db.refresh(event)

        return RiskEventResponse(
            id=str(event.id),
            call_id=str(event.call_id),
            spoof_probability=event.spoof_probability,
            speaker_similarity=event.speaker_similarity,
            scam_score=event.scam_score,
            risk_score=event.risk_score,
            risk_level=event.risk_level.value,
            indicators=event.indicators,
            latency_ms=event.latency_ms,
            timestamp=event.timestamp
        )

    @staticmethod
    async def get_call_events(
        db: AsyncSession,
        current_user: User,
        call_id: str
    ) -> List[RiskEventResponse]:
        try:
            call_uuid = uuid.UUID(call_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid call ID")

        call_repo = CallSessionRepository(db)
        call = await call_repo.get_by_id(call_uuid)

        if not call:
            raise HTTPException(status_code=404, detail="Call not found")

        # Participant check
        if current_user.id != call.caller_id and current_user.id != call.receiver_id:
            raise HTTPException(status_code=404, detail="Call not found")

        risk_repo = RiskEventRepository(db)
        events = await risk_repo.get_call_events(call_uuid)

        return [
            RiskEventResponse(
                id=str(event.id),
                call_id=str(event.call_id),
                spoof_probability=event.spoof_probability,
                speaker_similarity=event.speaker_similarity,
                scam_score=event.scam_score,
                risk_score=event.risk_score,
                risk_level=event.risk_level.value,
                indicators=event.indicators,
                latency_ms=event.latency_ms,
                timestamp=event.timestamp
            ) for event in events
        ]

    @staticmethod
    async def get_latest_event(
        db: AsyncSession,
        current_user: User,
        call_id: str
    ) -> Optional[RiskEventResponse]:
        try:
            call_uuid = uuid.UUID(call_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid call ID")

        call_repo = CallSessionRepository(db)
        call = await call_repo.get_by_id(call_uuid)

        if not call:
            raise HTTPException(status_code=404, detail="Call not found")

        # Participant check
        if current_user.id != call.caller_id and current_user.id != call.receiver_id:
            raise HTTPException(status_code=404, detail="Call not found")

        risk_repo = RiskEventRepository(db)
        event = await risk_repo.get_latest_event(call_uuid)

        if not event:
            return None

        return RiskEventResponse(
            id=str(event.id),
            call_id=str(event.call_id),
            spoof_probability=event.spoof_probability,
            speaker_similarity=event.speaker_similarity,
            scam_score=event.scam_score,
            risk_score=event.risk_score,
            risk_level=event.risk_level.value,
            indicators=event.indicators,
            latency_ms=event.latency_ms,
            timestamp=event.timestamp
        )

    @staticmethod
    async def get_call_security_report(
        db: AsyncSession,
        current_user: User,
        call_id: str,
    ) -> CallSecurityReportResponse:
        try:
            call_uuid = uuid.UUID(call_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid call ID")

        call_repo = CallSessionRepository(db)
        call = await call_repo.get_by_id(call_uuid)
        if not call or current_user.id != call.receiver_id:
            raise HTTPException(status_code=404, detail="Call not found")

        risk_repo = RiskEventRepository(db)
        events = await risk_repo.get_call_events(call_uuid)
        latest = events[-1] if events else None
        peak = max(events, key=lambda event: event.risk_score) if events else None
        indicators = list(dict.fromkeys(
            indicator
            for event in events
            for indicator in (event.indicators or [])
        ))

        duration_seconds = None
        if call.started_at and call.ended_at:
            duration_seconds = max(
                0.0,
                (call.ended_at - call.started_at).total_seconds(),
            )

        recommendation = {
            "LOW": "No significant impersonation or social-engineering indicators detected.",
            "SUSPICIOUS": "Verify the caller independently before taking sensitive action.",
            "HIGH": "Do not share OTPs, passwords, financial information, or confidential documents. Verify the caller through an independent trusted channel.",
        }.get(latest.risk_level.value if latest else None)

        return CallSecurityReportResponse(
            call_id=str(call.id),
            duration_seconds=duration_seconds,
            status="COMPLETED" if call.status == CallStatus.ENDED else call.status.value,
            started_at=call.started_at,
            ended_at=call.ended_at,
            final_risk_score=latest.risk_score if latest else None,
            final_risk_level=latest.risk_level.value if latest else None,
            peak_risk_score=peak.risk_score if peak else None,
            voice_authenticity_risk=latest.spoof_probability if latest else None,
            speaker_verification_status=(
                "NOT ENROLLED" if latest and latest.speaker_similarity is None
                else (
                    "VERIFIED"
                    if latest and latest.speaker_similarity >= 0.75
                    else "MISMATCH"
                    if latest
                    else None
                )
            ),
            speaker_similarity=latest.speaker_similarity if latest else None,
            scam_probability=latest.scam_score if latest else None,
            indicators=indicators,
            recommended_action=recommendation,
        )
