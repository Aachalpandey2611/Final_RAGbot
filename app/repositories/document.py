from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.document import Document

class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: AsyncSession):
        super().__init__(Document, db)

    async def get_by_user(
        self, user_id: int, skip: int = 0, limit: int = 50
    ) -> List[Document]:
        """
        Get all documents for a specific user, ordered by most recent.
        """
        query = (
            select(Document)
            .where(Document.user_id == user_id)
            .where(Document.chunks.any())
            .order_by(Document.uploaded_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: int) -> int:
        """
        Count total documents for a user.
        """
        query = select(func.count(Document.id)).where(
            Document.user_id == user_id
        ).where(Document.chunks.any())
        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_by_id_and_owner(self, document_id: int, user_id: int) -> Optional[Document]:
        """
        Get a document by ID and verify ownership.
        """
        query = select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def delete_by_owner(
        self, document_id: int, user_id: int
    ) -> Optional[Document]:
        """
        Delete a document only if it belongs to the given user.
        """
        document = await self.get_by_id_and_owner(document_id, user_id)
        if document:
            await self.db.delete(document)
            await self.db.commit()
        return document
