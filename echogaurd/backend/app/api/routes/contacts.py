"""
Contacts API routes — thin handlers that delegate all logic to ContactService.

Endpoints:
  POST   /api/contacts
  GET    /api/contacts
  GET    /api/contacts/{contact_id}
  PATCH  /api/contacts/{contact_id}
  DELETE /api/contacts/{contact_id}
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.db.models.user import User
from app.models.schemas import (
    ContactResponse,
    CreateContactRequest,
    UpdateContactRequest,
)
from app.services.contact_service import ContactService
from app.services.speaker_profile_service import SpeakerProfileService

router = APIRouter()


def _svc(db: AsyncSession = Depends(get_db)) -> ContactService:
    return ContactService(db)


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    body: CreateContactRequest,
    current_user: User = Depends(get_current_user),
    svc: ContactService = Depends(_svc),
):
    return await svc.create_contact(
        owner_id=current_user.id,
        contact_user_id=body.contact_user_id,
        nickname=body.nickname,
        is_trusted=body.is_trusted,
    )


@router.get("", response_model=List[ContactResponse])
async def list_contacts(
    trusted_only: bool = Query(False, description="Return only trusted contacts"),
    current_user: User = Depends(get_current_user),
    svc: ContactService = Depends(_svc),
):
    return await svc.list_contacts(owner_id=current_user.id, trusted_only=trusted_only)


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: ContactService = Depends(_svc),
):
    return await svc.get_contact(owner_id=current_user.id, contact_id=contact_id)


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: uuid.UUID,
    body: UpdateContactRequest,
    current_user: User = Depends(get_current_user),
    svc: ContactService = Depends(_svc),
):
    return await svc.update_contact(
        owner_id=current_user.id,
        contact_id=contact_id,
        nickname=body.nickname,
        is_trusted=body.is_trusted,
    )


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: ContactService = Depends(_svc),
):
    await svc.delete_contact(owner_id=current_user.id, contact_id=contact_id)


@router.post("/{contact_id}/voice-profile", response_model=dict)
async def create_voice_profile(
    contact_id: uuid.UUID,
    file: UploadFile = File(...),
    consent: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = SpeakerProfileService(db)
    return await svc.create_profile(current_user.id, contact_id, file, consent)


@router.get("/{contact_id}/voice-profile")
async def get_voice_profile(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = SpeakerProfileService(db)
    return await svc.get_profile(current_user.id, contact_id)


@router.put("/{contact_id}/voice-profile")
async def update_voice_profile(
    contact_id: uuid.UUID,
    file: UploadFile = File(...),
    consent: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = SpeakerProfileService(db)
    return await svc.update_profile(current_user.id, contact_id, file, consent)


@router.delete("/{contact_id}/voice-profile")
async def delete_voice_profile(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = SpeakerProfileService(db)
    await svc.delete_profile(current_user.id, contact_id)
    return {"status": "REVOKED"}
