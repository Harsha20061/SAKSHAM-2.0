"""
Call Session API routes — thin handlers delegating all logic to CallService.

Endpoints:
  POST  /api/calls
  GET   /api/calls
  GET   /api/calls/{call_id}
  PATCH /api/calls/{call_id}/status
  POST  /api/calls/{call_id}/end
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.db.models.user import User
from app.models.schemas import CallResponse, CreateCallRequest, UpdateCallStatusRequest
from app.services.call_service import CallService

router = APIRouter()


def _svc(db: AsyncSession = Depends(get_db)) -> CallService:
    return CallService(db)


@router.post("", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def create_call(
    body: CreateCallRequest,
    current_user: User = Depends(get_current_user),
    svc: CallService = Depends(_svc),
):
    return await svc.create_call(
        caller_id=current_user.id,
        receiver_id=body.receiver_id,
    )


@router.get("", response_model=List[CallResponse])
async def list_calls(
    status: Optional[str] = Query(None, description="Filter by status: RINGING|ACTIVE|ENDED|FAILED"),
    current_user: User = Depends(get_current_user),
    svc: CallService = Depends(_svc),
):
    return await svc.list_calls(user_id=current_user.id, status_filter=status)


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: CallService = Depends(_svc),
):
    return await svc.get_call(user_id=current_user.id, call_id=call_id)


@router.patch("/{call_id}/status", response_model=CallResponse)
async def update_call_status(
    call_id: uuid.UUID,
    body: UpdateCallStatusRequest,
    current_user: User = Depends(get_current_user),
    svc: CallService = Depends(_svc),
):
    return await svc.update_status(
        user_id=current_user.id,
        call_id=call_id,
        new_status=body.status,
    )


@router.post("/{call_id}/end", response_model=CallResponse)
async def end_call(
    call_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: CallService = Depends(_svc),
):
    return await svc.end_call(user_id=current_user.id, call_id=call_id)
