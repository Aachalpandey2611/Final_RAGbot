import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.conversation import ConversationRepository, MessageRepository
from app.models.conversation import Conversation, Message

logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.conv_repo = ConversationRepository(db)
        self.msg_repo = MessageRepository(db)

    # ---------- Conversation CRUD ----------

    async def create_conversation(self, user_id: int, title: str = "New Conversation") -> Conversation:
        """
        Create a new conversation for a user.
        """
        logger.info(f"Creating conversation for user_id={user_id}")
        return await self.conv_repo.create({
            "title": title,
            "user_id": user_id,
        })

    async def list_conversations(
        self, user_id: int, skip: int = 0, limit: int = 50
    ) -> Dict[str, Any]:
        """
        List all conversations for a user with total count.
        """
        conversations = await self.conv_repo.get_by_user(user_id, skip, limit)
        total = await self.conv_repo.count_by_user(user_id)
        return {"total": total, "conversations": conversations}

    async def get_conversation_detail(
        self, conversation_id: int, user_id: int
    ) -> Conversation:
        """
        Get a conversation with its messages. Validates ownership.
        """
        conversation = await self.conv_repo.get_with_messages(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return conversation

    async def update_conversation(
        self, conversation_id: int, user_id: int, title: str
    ) -> Conversation:
        """
        Update conversation title. Validates ownership.
        """
        conversation = await self.conv_repo.get_with_messages(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return await self.conv_repo.update(conversation, {"title": title})

    async def delete_conversation(self, conversation_id: int, user_id: int) -> None:
        """
        Delete a conversation. Validates ownership.
        """
        deleted = await self.conv_repo.delete_by_owner(conversation_id, user_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        logger.info(f"Deleted conversation_id={conversation_id} for user_id={user_id}")

    # ---------- Message CRUD ----------

    async def add_message(
        self, conversation_id: int, user_id: int, role: str, content: str
    ) -> Message:
        """
        Add a message to a conversation. Validates conversation ownership first.
        Also updates conversation's updated_at timestamp.
        """
        conversation = await self.conv_repo.get_with_messages(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        message = await self.msg_repo.create({
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
        })

        # Touch the conversation's updated_at
        await self.conv_repo.update(conversation, {
            "updated_at": datetime.now(timezone.utc)
        })

        return message

    async def list_messages(
        self, conversation_id: int, user_id: int, skip: int = 0, limit: int = 100
    ) -> Dict[str, Any]:
        """
        List messages in a conversation. Validates ownership.
        """
        # Ownership check
        conversation = await self.conv_repo.get_with_messages(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        messages = await self.msg_repo.get_by_conversation(conversation_id, skip, limit)
        total = await self.msg_repo.count_by_conversation(conversation_id)
        return {"total": total, "messages": messages}
