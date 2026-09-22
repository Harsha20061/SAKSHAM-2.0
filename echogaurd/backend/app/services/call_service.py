"""
CallService — owns all business rules for the call session feature.

Architecture: Route → CallService → CallSessionRepository / UserRepository → DB

State machine (only these transitions are legal):
  RINGING → ACTIVE  | set started_at
  RINGING → ENDED   | set ended_at
  RINGING → FAILED  | set ended_at
  ACTIVE  → ENDED   | set ended_at
  ACTIVE  → FAILED  | set ended_at
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.call_session import CallSession, CallStatus
from app.db.repositories.call_session_repository import CallSessionRepository
from app.db.repositories.user_repository import UserRepository

# ── valid state transitions ────────────────────────────────────────────────────
_VALID_TRANSITIONS: dict = {
    CallStatus.RINGING: {CallStatus.ACTIVE, CallStatus.ENDED, CallStatus.FAILED},
    CallStatus.ACTIVE:  {CallStatus.ENDED,  CallStatus.FAILED},
    CallStatus.ENDED:   set(),   # terminal
    CallStatus.FAILED:  set(),   # terminal
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CallService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.call_repo = CallSessionRepository(db)
        self.user_repo = UserRepository(db)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _as_response_dict(self, call: CallSession) -> dict:
        return {
            "id": str(call.id),
            "caller_id": str(call.caller_id),
            "receiver_id": str(call.receiver_id),
            "status": call.status.value if isinstance(call.status, CallStatus) else str(call.status),
            "started_at": call.started_at,
            "ended_at": call.ended_at,
            "created_at": call.created_at,
        }

    async def _get_participant_call(
        self, participant_id: uuid.UUID, call_id: uuid.UUID
    ) -> CallSession:
        """Return call only when participant_id is caller or receiver; else 404."""
        call = await self.call_repo.get_by_id(call_id)
        if call is None or (call.caller_id != participant_id and call.receiver_id != participant_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")
        return call

    def _validate_transition(self, current: CallStatus, target: CallStatus) -> None:
        allowed = _VALID_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition: {current.value} -> {target.value}",
            )

    # ── CREATE ────────────────────────────────────────────────────────────────

    async def create_call(
        self, caller_id: uuid.UUID, receiver_id: uuid.UUID
    ) -> dict:
        if caller_id == receiver_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot call yourself",
            )

        receiver = await self.user_repo.get_by_id(receiver_id)
        if receiver is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiver not found",
            )

        call = await self.call_repo.create(
            caller_id=caller_id,
            receiver_id=receiver_id,
            status=CallStatus.RINGING,
        )
        await self.db.commit()
        await self.db.refresh(call)
        return self._as_response_dict(call)

    # ── LIST ──────────────────────────────────────────────────────────────────

    async def list_calls(
        self, user_id: uuid.UUID, status_filter: Optional[str] = None
    ) -> List[dict]:
        if status_filter is not None:
            try:
                enum_status = CallStatus(status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter: {status_filter}",
                )
            calls = await self.call_repo.get_user_calls_by_status(user_id, enum_status)
        else:
            calls = await self.call_repo.get_user_calls(user_id)
        return [self._as_response_dict(c) for c in calls]

    # ── GET ───────────────────────────────────────────────────────────────────

    async def get_call(self, user_id: uuid.UUID, call_id: uuid.UUID) -> dict:
        call = await self._get_participant_call(user_id, call_id)
        return self._as_response_dict(call)

    # ── UPDATE STATUS ─────────────────────────────────────────────────────────

    async def update_status(
        self, user_id: uuid.UUID, call_id: uuid.UUID, new_status: str
    ) -> dict:
        call = await self._get_participant_call(user_id, call_id)
        target = CallStatus(new_status)
        self._validate_transition(call.status, target)

        now = _now_utc()

        if target == CallStatus.ACTIVE:
            await self.call_repo.set_started_at(call, now)

        if target in (CallStatus.ENDED, CallStatus.FAILED):
            await self.call_repo.set_ended_at(call, now)

        await self.call_repo.update_status(call_id, target)
        await self.db.commit()
        await self.db.refresh(call)
        return self._as_response_dict(call)

    # ── END CALL ──────────────────────────────────────────────────────────────

    async def end_call(self, user_id: uuid.UUID, call_id: uuid.UUID) -> dict:
        call = await self._get_participant_call(user_id, call_id)

        # Already terminated — return current state without corrupting timestamps
        if call.status in (CallStatus.ENDED, CallStatus.FAILED):
            return self._as_response_dict(call)

        self._validate_transition(call.status, CallStatus.ENDED)
        now = _now_utc()
        await self.call_repo.set_ended_at(call, now)
        await self.call_repo.update_status(call_id, CallStatus.ENDED)
        await self.db.commit()
        await self.db.refresh(call)
        return self._as_response_dict(call)
