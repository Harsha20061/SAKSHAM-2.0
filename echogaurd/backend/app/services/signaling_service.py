import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.db.models.user import User
from app.db.models.call_session import CallSession, CallStatus
from app.db.repositories.call_session_repository import CallSessionRepository
from app.services.call_service import CallService
from app.services.websocket_manager import manager

logger = logging.getLogger(__name__)

class SignalingService:
    @staticmethod
    async def validate_connection(db: AsyncSession, session_id: str, current_user: User) -> CallSession:
        try:
            call_uuid = uuid.UUID(session_id)
        except ValueError:
            raise ValueError("Invalid session ID format")

        repo = CallSessionRepository(db)
        call = await repo.get_by_id(call_uuid)
        if not call:
            raise ValueError("Session not found")

        if current_user.id != call.caller_id and current_user.id != call.receiver_id:
            raise ValueError("Not a participant")

        if call.status in [CallStatus.ENDED, CallStatus.FAILED]:
            raise ValueError("Call is already terminated")

        return call

    @staticmethod
    async def process_message(db: AsyncSession, session_id: str, current_user: User, message: dict):
        call_uuid = uuid.UUID(session_id)
        repo = CallSessionRepository(db)
        call = await repo.get_by_id(call_uuid)

        if not call:
            return

        if call.status in [CallStatus.ENDED, CallStatus.FAILED]:
            return

        msg_type = message.get("type")
        other_user_id = str(call.receiver_id) if current_user.id == call.caller_id else str(call.caller_id)

        if msg_type in ["call_offer", "call_answer", "ice_candidate"]:
            await manager.send_to_user(session_id, other_user_id, message)

        elif msg_type == "call_end":
            await manager.send_to_user(session_id, other_user_id, message)
            await CallService.end_call(db, current_user, call_uuid)
