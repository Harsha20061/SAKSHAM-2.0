import uuid
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.call_session import CallSession, CallStatus

class CallSessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, caller_id: uuid.UUID, receiver_id: uuid.UUID, status: CallStatus = CallStatus.RINGING) -> CallSession:
        call_session = CallSession(
            caller_id=caller_id,
            receiver_id=receiver_id,
            status=status
        )
        self.db.add(call_session)
        return call_session

    async def get_by_id(self, call_id: uuid.UUID) -> Optional[CallSession]:
        result = await self.db.execute(select(CallSession).filter(CallSession.id == call_id))
        return result.scalar_one_or_none()

    async def get_user_calls(self, user_id: uuid.UUID) -> List[CallSession]:
        result = await self.db.execute(
            select(CallSession).filter(
                or_(CallSession.caller_id == user_id, CallSession.receiver_id == user_id)
            ).order_by(CallSession.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(self, call_id: uuid.UUID, status: CallStatus) -> Optional[CallSession]:
        call_session = await self.get_by_id(call_id)
        if call_session:
            call_session.status = status
            # Transaction will be committed by caller
        return call_session

    async def end_call(self, call_id: uuid.UUID, ended_at: datetime) -> Optional[CallSession]:
        call_session = await self.get_by_id(call_id)
        if call_session:
            call_session.status = CallStatus.ENDED
            call_session.ended_at = ended_at
        return call_session

    async def get_user_calls_by_status(
        self, user_id: uuid.UUID, status: CallStatus
    ) -> List[CallSession]:
        result = await self.db.execute(
            select(CallSession).filter(
                or_(CallSession.caller_id == user_id, CallSession.receiver_id == user_id),
                CallSession.status == status,
            ).order_by(CallSession.created_at.desc())
        )
        return list(result.scalars().all())

    async def set_started_at(self, call: CallSession, started_at: datetime) -> None:
        """Set started_at only when it has not been set yet."""
        if call.started_at is None:
            call.started_at = started_at

    async def set_ended_at(self, call: CallSession, ended_at: datetime) -> None:
        if call.ended_at is None:
            call.ended_at = ended_at
