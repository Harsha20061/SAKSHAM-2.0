import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        username: str,
        display_name: str,
        password_hash: Optional[str] = None,
    ) -> User:
        user = User(
            username=username,
            display_name=display_name,
            password_hash=password_hash,
        )

        self.db.add(user)

        # The caller is responsible for committing the transaction.
        return user

    async def get_by_id(
        self,
        user_id: uuid.UUID,
    ) -> Optional[User]:
        result = await self.db.execute(
            select(User).filter(User.id == user_id)
        )

        return result.scalar_one_or_none()

    async def get_by_username(
        self,
        username: str,
    ) -> Optional[User]:
        result = await self.db.execute(
            select(User).filter(User.username == username)
        )

        return result.scalar_one_or_none()

    async def exists_by_username(
        self,
        username: str,
    ) -> bool:
        result = await self.db.execute(
            select(User.id).filter(User.username == username)
        )

        return result.first() is not None

    async def search_users(
        self,
        query: str,
        exclude_user_id: uuid.UUID,
        limit: int = 10,
    ) -> list[User]:
        result = await self.db.execute(
            select(User)
            .where(
                User.username.ilike(f"%{query}%"),
                User.id != exclude_user_id,
            )
            .order_by(User.username)
            .limit(limit)
        )

        return list(result.scalars().all())