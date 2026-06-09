import hashlib
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.chunk import DocumentChunkRepository
 # Lazy imports for optional heavy dependencies (vector store, embedding provider)
# BM25 and Reranker are imported lazily inside methods to avoid heavy import-time deps
from app.models.document import Document, DocumentChunk

logger = logging.getLogger(__name__)


class RetrievalOrchestrator:
    """
    Orchestrates hybrid retrieval: BM25 + Vector, merging, deduping, reranking.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chunk_repo = DocumentChunkRepository(db)
        try:
            from app.services.vector_store import get_vector_store
            from app.services.embeddings.factory import get_embedding_provider
            self.vector_store = get_vector_store()
            # default provider same as embeddings used elsewhere
            self.provider = get_embedding_provider("huggingface")
        except Exception:
            # In test or lightweight environments these may be unavailable.
            self.vector_store = None
            self.provider = None

        # Reranker will be lazy-imported when needed; allow tests to override
        self.reranker = None

    async def _get_user_chunks_from_db(self, user_id: Optional[int], target_filenames: Optional[List[str]] = None) -> List[DocumentChunk]:
        query = select(DocumentChunk).join(Document, DocumentChunk.document_id == Document.id)
        
        if user_id is not None:
            query = query.where(Document.user_id == user_id)
            
        if target_filenames:
            # Create OR conditions for partial or exact matches of filenames
            from sqlalchemy import or_
            conditions = []
            for name in target_filenames:
                name_clean = name.strip()
                conditions.append(Document.original_filename.ilike(f"%{name_clean}%"))
                conditions.append(Document.filename.ilike(f"%{name_clean}%"))
            if conditions:
                query = query.where(or_(*conditions))
                
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def bm25_search(self, query: str, user_id: Optional[int] = None, top_k: int = 10, target_filenames: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Return list of dicts: {id, chunk, score, source}
        """
        try:
            corpus = await self._get_user_chunks_from_db(user_id, target_filenames=target_filenames)
            if not corpus:
                return []

            try:
                from app.services.rag.bm25 import BM25
                bm25 = BM25(corpus)
                scores = bm25.score(query)
            except Exception:
                # Fallback: simple term-overlap scoring
                scores = []
                qtokens = set((query or "").lower().split())
                for chunk in corpus:
                    ctokens = set((getattr(chunk, 'content', '') or "").lower().split())
                    overlap = len(qtokens & ctokens)
                    scores.append((chunk, float(overlap)))
            # sort desc and pick top_k
            scores.sort(key=lambda x: x[1], reverse=True)
            results = []
            for chunk, score in scores[:top_k]:
                if score <= 0:
                    continue
                results.append({"id": int(getattr(chunk, 'id', None)), "chunk": chunk, "score": float(score), "source": "bm25"})
            return results
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []

    async def vector_search(self, query: str, user_id: Optional[int] = None, top_k: int = 10, target_filenames: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Run vector search and fetch matching chunks from DB."""
        try:
            # embed query
            try:
                query_embedding = await self.provider.embed_text(query)
            except AttributeError:
                if hasattr(self.provider, 'embed_query'):
                    query_embedding = await self.provider.embed_query(query)
                else:
                    raise

            search_results = await self.vector_store.search(collection_name="document_chunks", query_embedding=query_embedding, limit=top_k)
            if not search_results:
                return []

            ids = [int(r['id']) for r in search_results]
            # fetch chunks while enforcing user ownership and filename filters
            query = (
                select(DocumentChunk)
                .join(Document, DocumentChunk.document_id == Document.id)
                .where(DocumentChunk.id.in_(ids))
            )
            if user_id is not None:
                query = query.where(Document.user_id == user_id)
                
            if target_filenames:
                from sqlalchemy import or_
                conditions = []
                for name in target_filenames:
                    name_clean = name.strip()
                    conditions.append(Document.original_filename.ilike(f"%{name_clean}%"))
                    conditions.append(Document.filename.ilike(f"%{name_clean}%"))
                if conditions:
                    query = query.where(or_(*conditions))
                    
            result = await self.db.execute(query)
            chunks = list(result.scalars().all())

            # map scores
            score_map = {int(r['id']): float(r.get('score', 0.0)) for r in search_results}
            results = []
            for c in chunks:
                results.append({"id": int(c.id), "chunk": c, "score": float(score_map.get(int(c.id), 0.0)), "source": "vector"})
            return results
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    @staticmethod
    def _content_fingerprint(chunk) -> str:
        """Create a fingerprint from the first 200 chars of chunk content to detect duplicates."""
        content = (getattr(chunk, 'content', '') or '')[:200].strip()
        return hashlib.md5(content.encode('utf-8', errors='ignore')).hexdigest()

    def _dedup_by_content(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate chunks that have identical content (from duplicate document uploads).
        Keeps the first (highest-scored) chunk for each unique content fingerprint."""
        seen_fingerprints = set()
        deduped = []
        for item in items:
            fp = self._content_fingerprint(item['chunk'])
            if fp not in seen_fingerprints:
                seen_fingerprints.add(fp)
                deduped.append(item)
            else:
                logger.debug(f"Dedup: dropping chunk {item['id']} (duplicate content of an earlier chunk)")
        return deduped

    def merge_results(self, bm25_results: List[Dict[str, Any]], vector_results: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
        """Merge and deduplicate results using Reciprocal Rank Fusion (RRF)."""
        k = 60
        merged: Dict[int, Dict[str, Any]] = {}
        
        # Helper to apply RRF
        def apply_rrf(results, source_name):
            for rank, r in enumerate(results, 1):
                cid = int(r['id'])
                score = 1.0 / (k + rank)
                if cid not in merged:
                    merged[cid] = {"id": cid, "chunk": r['chunk'], "score": score, "sources": [source_name]}
                else:
                    merged[cid]['score'] += score
                    if source_name not in merged[cid]['sources']:
                        merged[cid]['sources'].append(source_name)

        # Apply BM25 ranking
        bm25_results.sort(key=lambda x: x['score'], reverse=True)
        apply_rrf(bm25_results, "bm25")
        
        # Apply Vector ranking
        vector_results.sort(key=lambda x: x['score'], reverse=True)
        apply_rrf(vector_results, "vector")

        # Sort by fused RRF score desc
        items = list(merged.values())
        items.sort(key=lambda x: x['score'], reverse=True)

        # Content-level deduplication: remove identical chunks from duplicate doc uploads
        items = self._dedup_by_content(items)

        return items[:top_k]

    def rerank_results(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
        """Rerank candidates using the configured reranker. Returns list with similarity scores.
        Each item: {id, chunk, score, sources, similarity}
        """
        if not candidates:
            return []

        chunks = [c['chunk'] for c in candidates]
        # Reranker returns list of tuples (chunk, score)
        try:
            # try lazy import of Reranker if available and not already set
            if not hasattr(self, 'reranker') or self.reranker is None:
                try:
                    from app.services.rag.reranker import Reranker
                    self.reranker = Reranker()
                except Exception:
                    self.reranker = None

            if self.reranker is not None:
                reranked = self.reranker.rerank(query, chunks)
                sim_map = {int(ch.id): float(score) for ch, score in reranked}
            else:
                # fallback: use existing score as similarity
                sim_map = {int(c['id']): float(c['score']) for c in candidates}
        except Exception as e:
            logger.error(f"Rerank failed: {e}")
            sim_map = {int(c['id']): 0.0 for c in candidates}

        results = []
        for c in candidates:
            cid = int(c['id'])
            results.append({
                "id": cid,
                "chunk": c['chunk'],
                "score": c['score'],
                "sources": c.get('sources', []),
                "similarity": sim_map.get(cid, 0.0),
            })

        # sort by similarity desc
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]

    async def fetch_neighbor_chunks(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fetch chunk_index +/- N for each candidate and CONCATENATE them to provide full context."""
        if not candidates:
            return []
            
        # Determine how many neighbors to fetch based on query context
        q_lower = query.lower()
        process_keywords = ["flow", "process", "steps", "guide", "how does", "route", "logic"]
        fetch_width = 2 if any(kw in q_lower for kw in process_keywords) else 1
            
        target_pairs = []
        for c in candidates:
            chunk = c['chunk']
            if hasattr(chunk, 'document_id') and hasattr(chunk, 'chunk_index'):
                if chunk.chunk_index is not None:
                    for offset in range(-fetch_width, fetch_width + 1):
                        if offset != 0:
                            target_pairs.append((chunk.document_id, chunk.chunk_index + offset))
                    
        if not target_pairs:
            return candidates
            
        conditions = []
        for doc_id, c_idx in target_pairs:
            if c_idx >= 0:
                conditions.append((DocumentChunk.document_id == doc_id) & (DocumentChunk.chunk_index == c_idx))
                
        if not conditions:
            return candidates
            
        from sqlalchemy import or_
        # Group conditions in batches to avoid overly large OR clauses
        batch_size = 50
        neighbors = []
        
        try:
            for i in range(0, len(conditions), batch_size):
                batch_conds = conditions[i:i+batch_size]
                query_db = select(DocumentChunk).where(or_(*batch_conds))
                result = await self.db.execute(query_db)
                neighbors.extend(list(result.scalars().all()))
            
            # Map neighbors by (document_id, chunk_index)
            neighbor_map = {}
            for n in neighbors:
                neighbor_map[(n.document_id, n.chunk_index)] = n.content
            
            # Concatenate content into existing candidates
            for c in candidates:
                chunk = c['chunk']
                doc_id = getattr(chunk, 'document_id', -1)
                c_idx = getattr(chunk, 'chunk_index', -1)
                
                if doc_id != -1 and c_idx != -1:
                    full_content = []
                    
                    # Prepend previous chunks
                    for offset in range(-fetch_width, 0):
                        prev_content = neighbor_map.get((doc_id, c_idx + offset), "")
                        if prev_content:
                            full_content.append(prev_content.strip())
                            
                    # Add current chunk
                    full_content.append(chunk.content.strip() if chunk.content else "")
                    
                    # Append next chunks
                    for offset in range(1, fetch_width + 1):
                        next_content = neighbor_map.get((doc_id, c_idx + offset), "")
                        if next_content:
                            full_content.append(next_content.strip())
                    
                    merged_text = "\n\n".join(filter(None, full_content))
                    
                    if len(full_content) > 1:
                        logger.info(f"Neighbor Expansion for Chunk {getattr(chunk, 'id', 'N/A')} (Doc {doc_id}): Merged {len(full_content)} chunks (-{fetch_width} to +{fetch_width}). Final len: {len(merged_text)} chars.")
                        if 'neighbor_expansion' not in c.get('sources', []):
                            c.setdefault('sources', []).append('neighbor_expansion')
                    
                    chunk.content = merged_text
                        
            return candidates
        except Exception as e:
            logger.error(f"Failed to fetch neighbor chunks: {e}")
            return candidates

    async def retrieve(self, query: str, top_k: int = 10, user_id: Optional[int] = None, target_filenames: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Full orchestration: BM25 -> Vector -> Merge -> Neighbors -> Rerank -> Return top_k
        Returns dict: {chunks: [...], retrieval_scores: {id: score}, source_type: {id: [sources]}}
        """
        # Retrieve at least 20 candidates per method
        fetch_limit = max(20, top_k * 2)
        
        # 1. BM25
        bm25_res = await self.bm25_search(query, user_id=user_id, top_k=fetch_limit, target_filenames=target_filenames)

        # 2. Vector
        vector_res = await self.vector_search(query, user_id=user_id, top_k=fetch_limit, target_filenames=target_filenames)

        # 3. Merge
        merged = self.merge_results(bm25_res, vector_res, top_k=fetch_limit)

        # 4. Fetch Neighbors
        merged_with_neighbors = await self.fetch_neighbor_chunks(query, merged)

        # 5. Rerank
        reranked = self.rerank_results(query, merged_with_neighbors, top_k=top_k)

        # 6. Format return
        chunks = []
        retrieval_scores: Dict[int, float] = {}
        source_type: Dict[int, List[str]] = {}

        for item in reranked:
            cid = int(item['id'])
            chunks.append(item['chunk'])
            retrieval_scores[cid] = float(item['similarity'])
            source_type[cid] = item.get('sources', [])

        return {"chunks": chunks, "retrieval_scores": retrieval_scores, "source_type": source_type}
