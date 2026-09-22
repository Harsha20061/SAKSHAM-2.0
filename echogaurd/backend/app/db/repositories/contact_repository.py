import uuid
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.contact import Contact

class ContactRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: uuid.UUID, contact_user_id: uuid.UUID, nickname: str, is_trusted: bool = False) -> Contact:
        contact = Contact(
            user_id=user_id,
            contact_user_id=contact_user_id,
            nickname=nickname,
            is_trusted=is_trusted
        )
        self.db.add(contact)
        return contact

    async def get_by_id(self, contact_id: uuid.UUID) -> Optional[Contact]:
        result = await self.db.execute(select(Contact).filter(Contact.id == contact_id))
        return result.scalar_one_or_none()

    async def get_user_contacts(self, user_id: uuid.UUID) -> List[Contact]:
        result = await self.db.execute(select(Contact).filter(Contact.user_id == user_id))
        return list(result.scalars().all())

    async def get_trusted_contacts(self, user_id: uuid.UUID) -> List[Contact]:
        result = await self.db.execute(
            select(Contact).filter(
                and_(Contact.user_id == user_id, Contact.is_trusted == True)
            )
        )
        return list(result.scalars().all())

    async def exists(self, user_id: uuid.UUID, contact_user_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(Contact.id).filter(
                and_(Contact.user_id == user_id, Contact.contact_user_id == contact_user_id)
            )
        )
        return result.first() is not None

    async def update(self, contact: Contact, nickname: Optional[str] = None, is_trusted: Optional[bool] = None) -> Contact:
        if nickname is not None:
            contact.nickname = nickname
        if is_trusted is not None:
            contact.is_trusted = is_trusted
        # Caller commits
        return contact

    async def delete(self, contact: Contact) -> None:
        await self.db.delete(contact)
        # Caller commits
