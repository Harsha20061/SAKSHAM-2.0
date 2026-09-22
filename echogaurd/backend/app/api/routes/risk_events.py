from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models.user import User
from app.api.dependencies import get_current_user
from app.models.schemas import (
    CallSecurityReportResponse,
    RiskEventRequest,
    RiskEventResponse,
)
from app.services.risk_event_service import RiskEventService

router = APIRouter()

@router.post("/{call_id}/risk-events", response_model=RiskEventResponse)
async def create_risk_event(
    call_id: str,
    request: RiskEventRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await RiskEventService.create_risk_event(
        db=db,
        current_user=current_user,
        call_id=call_id,
        request=request
    )

@router.get("/{call_id}/risk-events", response_model=List[RiskEventResponse])
async def get_risk_events(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await RiskEventService.get_call_events(
        db=db,
        current_user=current_user,
        call_id=call_id
    )

@router.get("/{call_id}/risk-events/latest", response_model=RiskEventResponse)
async def get_latest_risk_event(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    event = await RiskEventService.get_latest_event(
        db=db,
        current_user=current_user,
        call_id=call_id
    )
    if not event:
        raise HTTPException(status_code=404, detail="No risk events found for call")
    return event

@router.get("/{call_id}/security-report", response_model=CallSecurityReportResponse)
async def get_security_report(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await RiskEventService.get_call_security_report(
        db=db,
        current_user=current_user,
        call_id=call_id,
    )
