from typing import List
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.document import DocumentChunk

class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    def __init__(self, db: AsyncSession):
        super().__init__(DocumentChunk, db)

    async def get_by_document(self, document_id: int) -> List[DocumentChunk]:
        """
        Fetch all chunks for a document, sorted by chunk_index.
        """
        query = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_by_document(self, document_id: int) -> None:
        """
        Delete all chunks associated with a document.
        """
        query = delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        await self.db.execute(query)
        await self.db.commit()

    async def get_unembedded_by_document(self, document_id: int) -> List[DocumentChunk]:
        """Fetch chunks that do not have embeddings yet."""
        query = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .where(DocumentChunk.embedding == None)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_embedded_count(self, document_id: int) -> int:
        """Count chunks that have embeddings."""
        from sqlalchemy import func
        query = select(func.count(DocumentChunk.id)).where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.embedding != None
        )
        result = await self.db.execute(query)
        return result.scalar_one()

    async def update_embedding(self, chunk_id: int, embedding: List[float], model_name: str) -> None:
        """Update the embedding for a specific chunk."""
        from sqlalchemy import update
        from datetime import datetime, timezone
        query = (
            update(DocumentChunk)
            .where(DocumentChunk.id == chunk_id)
            .values(
                embedding=embedding,
                embedding_model=model_name,
                embedded_at=datetime.now(timezone.utc)
            )
        )
        await self.db.execute(query)
        await self.db.commit()
