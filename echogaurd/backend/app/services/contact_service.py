"""
ContactService — owns all business rules for the contacts feature.

Architecture: Route → ContactService → ContactRepository / UserRepository → DB
"""
import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.contact import Contact
from app.db.repositories.contact_repository import ContactRepository
from app.db.repositories.user_repository import UserRepository


class ContactService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.contact_repo = ContactRepository(db)
        self.user_repo = UserRepository(db)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _as_response_dict(self, contact: Contact) -> dict:
        return {
            "id": str(contact.id),
            "contact_user_id": str(contact.contact_user_id),
            "nickname": contact.nickname,
            "is_trusted": contact.is_trusted,
            "created_at": contact.created_at,
        }

    async def _get_owned_contact(self, owner_id: uuid.UUID, contact_id: uuid.UUID) -> Contact:
        """Return contact only if it exists AND belongs to owner_id; else 404."""
        contact = await self.contact_repo.get_by_id(contact_id)
        if contact is None or contact.user_id != owner_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
        return contact

    # ── CREATE ────────────────────────────────────────────────────────────────

    async def create_contact(
        self,
        owner_id: uuid.UUID,
        contact_user_id: uuid.UUID,
        nickname: str,
        is_trusted: bool,
    ) -> dict:
        # Prevent self-contact
        if owner_id == contact_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot add yourself as a contact",
            )

        # Verify target user exists
        target_user = await self.user_repo.get_by_id(contact_user_id)
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target user not found",
            )

        # Prevent duplicate relationship
        if await self.contact_repo.exists(owner_id, contact_user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Contact relationship already exists",
            )

        contact = await self.contact_repo.create(
            user_id=owner_id,
            contact_user_id=contact_user_id,
            nickname=nickname,
            is_trusted=is_trusted,
        )
        await self.db.commit()
        await self.db.refresh(contact)
        return self._as_response_dict(contact)

    # ── LIST ──────────────────────────────────────────────────────────────────

    async def list_contacts(
        self, owner_id: uuid.UUID, trusted_only: bool = False
    ) -> List[dict]:
        if trusted_only:
            contacts = await self.contact_repo.get_trusted_contacts(owner_id)
        else:
            contacts = await self.contact_repo.get_user_contacts(owner_id)
        return [self._as_response_dict(c) for c in contacts]

    # ── GET ───────────────────────────────────────────────────────────────────

    async def get_contact(self, owner_id: uuid.UUID, contact_id: uuid.UUID) -> dict:
        contact = await self._get_owned_contact(owner_id, contact_id)
        return self._as_response_dict(contact)

    # ── UPDATE ────────────────────────────────────────────────────────────────

    async def update_contact(
        self,
        owner_id: uuid.UUID,
        contact_id: uuid.UUID,
        nickname: Optional[str],
        is_trusted: Optional[bool],
    ) -> dict:
        contact = await self._get_owned_contact(owner_id, contact_id)
        contact = await self.contact_repo.update(contact, nickname=nickname, is_trusted=is_trusted)
        await self.db.commit()
        await self.db.refresh(contact)
        return self._as_response_dict(contact)

    # ── DELETE ────────────────────────────────────────────────────────────────

    async def delete_contact(self, owner_id: uuid.UUID, contact_id: uuid.UUID) -> None:
        contact = await self._get_owned_contact(owner_id, contact_id)
        await self.contact_repo.delete(contact)
        await self.db.commit()
