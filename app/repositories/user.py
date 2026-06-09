from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.user import User, UserToken

class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Fetch a user by email.
        """
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

class UserTokenRepository(BaseRepository[UserToken]):
    def __init__(self, db: AsyncSession):
        super().__init__(UserToken, db)

    async def get_active_token(self, token: str) -> Optional[UserToken]:
        """
        Get an unrevoked user refresh token.
        """
        query = select(UserToken).where(
            UserToken.token == token,
            UserToken.is_revoked == False
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def revoke_user_tokens(self, user_id: int) -> None:
        """
        Revoke all active tokens for a specific user (logout from all devices).
        """
        query = (
            update(UserToken)
            .where(UserToken.user_id == user_id, UserToken.is_revoked == False)
            .values(is_revoked=True)
        )
        await self.db.execute(query)
        await self.db.commit()

    async def revoke_token(self, token: str) -> None:
        """
        Revoke a specific token.
        """
        query = (
            update(UserToken)
            .where(UserToken.token == token)
            .values(is_revoked=True)
        )
        await self.db.execute(query)
        await self.db.commit()
