import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.chunk import DocumentChunkRepository
from app.services.vector_store import get_vector_store
from app.services.embeddings.factory import get_embedding_provider
from app.models.document import Document, DocumentChunk
from app.services.rag.bm25 import BM25
# Reranker (sentence-transformers) is optional and may be heavy; import lazily in __init__

logger = logging.getLogger(__name__)

class Retriever:
    """
    Responsible for retrieving relevant document chunks from the Vector Store 
    and Sparse Index (BM25), combining them, and reranking the results.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chunk_repo = DocumentChunkRepository(db)
        # Using the same provider configured for embedding documents
        self.provider = get_embedding_provider("huggingface")
        self.vector_store = get_vector_store()
        # Lazy-load reranker to avoid heavy import at module import time
        try:
            from app.services.rag.reranker import Reranker
            self.reranker = Reranker()
        except Exception:
            self.reranker = None

    async def _get_user_chunks_from_db(self, user_id: Optional[int]) -> List[DocumentChunk]:
        """
        Fetch all chunks owned by a user to construct the BM25 corpus.
        If no user_id is provided, fetches all chunks in the system.
        """
        if user_id is not None:
            query = (
                select(DocumentChunk)
                .join(Document, DocumentChunk.document_id == Document.id)
                .where(Document.user_id == user_id)
            )
        else:
            query = select(DocumentChunk)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _fetch_chunks_by_ids_with_user_check(self, chunk_ids: List[int], user_id: Optional[int]) -> List[DocumentChunk]:
        """
        Fetch chunks by their IDs while enforcing owner user_id constraint.
        """
        if not chunk_ids:
            return []
        
        if user_id is not None:
            query = (
                select(DocumentChunk)
                .join(Document, DocumentChunk.document_id == Document.id)
                .where(DocumentChunk.id.in_(chunk_ids))
                .where(Document.user_id == user_id)
            )
        else:
            query = select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))
            
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def retrieve(self, query: str, top_k: int = 3, user_id: Optional[int] = None) -> List[DocumentChunk]:
        """
        Retrieves the top_k relevant chunks for the given query using Hybrid Search & Reranking.
        """
        logger.info(f"Retrieving top {top_k} chunks for query: '{query}' (user_id={user_id})")
        
        candidate_limit = settings.HYBRID_SEARCH_TOP_N
        
        # 1. --- Vector Search ---
        vector_candidates = []
        try:
            try:
                query_embedding = await self.provider.embed_text(query)
            except AttributeError:
                if hasattr(self.provider, 'embed_query'):
                    query_embedding = await self.provider.embed_query(query)
                else:
                    raise
            
            search_results = await self.vector_store.search(
                collection_name="document_chunks",
                query_embedding=query_embedding,
                limit=candidate_limit
            )
            
            if search_results:
                vector_ids = [int(res['id']) for res in search_results]
                vector_chunks = await self._fetch_chunks_by_ids_with_user_check(vector_ids, user_id)
                
                # Map vector similarity scores
                score_map = {int(res['id']): res.get('score', 0.0) for res in search_results}
                for chunk in vector_chunks:
                    setattr(chunk, 'vector_score', score_map.get(chunk.id, 0.0))
                
                vector_candidates = vector_chunks
                logger.debug(f"Vector search returned {len(vector_candidates)} candidate chunks.")
        except Exception as e:
            logger.error(f"Failed vector search: {str(e)}")

        # 2. --- BM25 Sparse Search ---
        bm25_candidates = []
        try:
            user_chunks = await self._get_user_chunks_from_db(user_id)
            if user_chunks:
                bm25_engine = BM25(user_chunks)
                bm25_scores = bm25_engine.score(query)
                
                # Sort and pick top candidate_limit
                bm25_scores.sort(key=lambda x: x[1], reverse=True)
                top_bm25 = bm25_scores[:candidate_limit]
                
                for chunk, score in top_bm25:
                    if score > 0:  # Only count chunks with some term overlap
                        setattr(chunk, 'bm25_score', score)
                        bm25_candidates.append(chunk)
                logger.debug(f"BM25 search returned {len(bm25_candidates)} candidate chunks.")
        except Exception as e:
            logger.error(f"Failed BM25 search: {str(e)}")

        # 3. --- Merge Candidates ---
        # Combine lists and deduplicate by chunk ID
        candidate_dict = {}
        for chunk in vector_candidates + bm25_candidates:
            candidate_dict[chunk.id] = chunk
            
        candidates = list(candidate_dict.values())
        logger.info(f"Total hybrid candidate pool size: {len(candidates)}")
        
        if not candidates:
            return []

        # 4. --- Reranking Layer ---
        logger.info(f"Reranking {len(candidates)} candidate chunks...")
        reranked_results = self.reranker.rerank(query, candidates)
        
        # Take the top_k chunks
        final_chunks = []
        for chunk, rerank_score in reranked_results[:top_k]:
            setattr(chunk, 'similarity_score', rerank_score)
            final_chunks.append(chunk)
            
        logger.info(f"Successfully retrieved {len(final_chunks)} reranked chunks.")
        return final_chunks

