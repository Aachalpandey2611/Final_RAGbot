import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.document import DocumentRepository
from app.repositories.chunk import DocumentChunkRepository
from app.services.embeddings.factory import get_embedding_provider
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.chunk_repo = DocumentChunkRepository(db)

    async def embed_document(self, document_id: int, user_id: int, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Embed all unembedded chunks of a document.
        """
        # 1. Verify ownership
        document = await self.doc_repo.get_by_id_and_owner(document_id, user_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found."
            )

        # 2. Get chunks that need embeddings
        unembedded_chunks = await self.chunk_repo.get_unembedded_by_document(document_id)
        if not unembedded_chunks:
            # Everything already embedded
            return await self.get_embedding_status(document_id, user_id)

        # 3. Instantiate provider
        provider = get_embedding_provider(provider_name)
        model_name = provider.model_name
        
        logger.info(f"Embedding {len(unembedded_chunks)} chunks for document {document_id} using {model_name}...")

        # 4. Extract texts and generate embeddings
        texts = [chunk.content for chunk in unembedded_chunks]
        
        # Depending on provider and size, batching may be necessary. 
        # For this implementation, we assume the provider handles reasonable batch sizes natively.
        try:
            embeddings = await provider.embed_batch(texts)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate embeddings."
            )
            
        # 5. Save embeddings to Vector DB & SQLite/PostgreSQL
        try:
            vector_store = get_vector_store()
            ids = [str(chunk.id) for chunk in unembedded_chunks]
            metadatas = [
                {
                    "document_id": document_id,
                    "user_id": user_id,
                    "chunk_index": chunk.chunk_index,
                    "embedding_model": model_name
                }
                for chunk in unembedded_chunks
            ]
            await vector_store.insert(
                collection_name="document_chunks",
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=texts
            )
        except Exception as e:
            logger.error(f"Failed to insert embeddings into Vector Database: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save embeddings to vector database."
            )

        for chunk, embedding in zip(unembedded_chunks, embeddings):
            await self.chunk_repo.update_embedding(
                chunk_id=chunk.id,
                embedding=embedding,
                model_name=model_name
            )

        logger.info(f"Successfully embedded {len(embeddings)} chunks for document {document_id}.")
        return await self.get_embedding_status(document_id, user_id)

    async def get_embedding_status(self, document_id: int, user_id: int) -> Dict[str, Any]:
        """
        Get the embedding progress/status of a document.
        """
        # Verify ownership
        document = await self.doc_repo.get_by_id_and_owner(document_id, user_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found."
            )
            
        all_chunks = await self.chunk_repo.get_by_document(document_id)
        total_chunks = len(all_chunks)
        
        embedded_count = await self.chunk_repo.get_embedded_count(document_id)
        
        embedding_model = None
        if all_chunks and all_chunks[0].embedding_model:
            embedding_model = all_chunks[0].embedding_model
            
        return {
            "document_id": document_id,
            "total_chunks": total_chunks,
            "embedded_chunks": embedded_count,
            "embedding_model": embedding_model,
            "is_complete": total_chunks > 0 and total_chunks == embedded_count
        }
