from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.repositories.base import BaseRepository
from app.models.conversation import Conversation, Message


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, db: AsyncSession):
        super().__init__(Conversation, db)

    async def get_by_user(
        self, user_id: int, skip: int = 0, limit: int = 50
    ) -> List[Conversation]:
        """
        Get all conversations for a specific user, ordered by most recently updated.
        """
        query = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_with_messages(
        self, conversation_id: int, user_id: int
    ) -> Optional[Conversation]:
        """
        Get a single conversation with all its messages eagerly loaded.
        Verifies ownership via user_id.
        """
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def count_by_user(self, user_id: int) -> int:
        """
        Count total conversations for a user.
        """
        query = select(func.count(Conversation.id)).where(
            Conversation.user_id == user_id
        )
        result = await self.db.execute(query)
        return result.scalar_one()

    async def delete_by_owner(
        self, conversation_id: int, user_id: int
    ) -> Optional[Conversation]:
        """
        Delete a conversation only if it belongs to the given user.
        """
        query = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        result = await self.db.execute(query)
        conversation = result.scalar_one_or_none()
        if conversation:
            await self.db.delete(conversation)
            await self.db.commit()
        return conversation


class MessageRepository(BaseRepository[Message]):
    def __init__(self, db: AsyncSession):
        super().__init__(Message, db)

    async def get_by_conversation(
        self, conversation_id: int, skip: int = 0, limit: int = 100
    ) -> List[Message]:
        """
        Get messages for a conversation ordered chronologically.
        """
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_conversation(self, conversation_id: int) -> int:
        """
        Count total messages in a conversation.
        """
        query = select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
        result = await self.db.execute(query)
        return result.scalar_one()
