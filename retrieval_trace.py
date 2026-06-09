"""
Retrieval Trace Script
Prints a full retrieval trace for a given query without generating an LLM answer.
"""
import asyncio
import os
import sys
import time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.models.document import Document, DocumentChunk
from app.services.retrieval.retrieval_orchestrator import RetrievalOrchestrator
from app.services.rag.context_builder import ContextBuilder
from app.services.llm.factory import get_llm_provider

QUERY = (
    "A Postpaid customer initiates a Bill Plan Change through MyJio "
    "and provides payment details along with an EWallet Reservation Reference ID. "
    "Describe the complete flow."
)

# Which user_id owns these docs? Adjust if needed.
USER_ID = 1


async def run_trace():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI_ASYNC)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Build a map of document_id -> original_filename once
    async with async_session() as db:
        res = await db.execute(select(Document.id, Document.original_filename, Document.filename))
        doc_map = {}
        for row in res.all():
            doc_map[row[0]] = row[1] or row[2] or f"DocID:{row[0]}"

    async with async_session() as db:
        orchestrator = RetrievalOrchestrator(db)

        # ─── 1. Original Query ───
        print("=" * 100)
        print("RETRIEVAL TRACE")
        print("=" * 100)
        print(f"\n1. ORIGINAL QUERY:\n   {QUERY}\n")

        # ─── 2. Query Expansion ───
        llm = get_llm_provider("gemini")
        expansion_prompt = (
            f"Extract critical keywords, technical entities, and system names from this query: "
            f"'{QUERY}'. Return ONLY a space-separated list of 5-8 exact terms to use for a "
            f"search engine. Include implicit related terms if known."
        )
        try:
            keywords = await llm.generate_response(expansion_prompt)
            expanded_query = f"{QUERY} {keywords}"
        except Exception as e:
            keywords = f"(expansion failed: {e})"
            expanded_query = QUERY

        print(f"2. EXPANDED QUERY:\n   Keywords: {keywords}")
        print(f"   Full:     {expanded_query}\n")

        # ─── 3. BM25 Search ───
        t0 = time.perf_counter()
        bm25_results = await orchestrator.bm25_search(expanded_query, user_id=USER_ID, top_k=20)
        t_bm25 = time.perf_counter() - t0

        print(f"3. BM25 RESULTS  ({len(bm25_results)} hits, {t_bm25:.2f}s)")
        print("-" * 100)
        print(f"{'Rank':>4}  {'ChunkID':>8}  {'DocID':>6}  {'BM25 Score':>11}  {'Document Name':<40}  Preview")
        print("-" * 100)
        for i, r in enumerate(bm25_results, 1):
            chunk = r['chunk']
            doc_id = getattr(chunk, 'document_id', '?')
            doc_name = doc_map.get(doc_id, f"DocID:{doc_id}")
            preview = (getattr(chunk, 'content', '') or '')[:80].replace('\n', ' ').replace('\r', '')
            print(f"{i:>4}  {r['id']:>8}  {doc_id:>6}  {r['score']:>11.4f}  {doc_name:<40}  {preview}...")
        print()

        # ─── 4. Vector Search ───
        t0 = time.perf_counter()
        vector_results = await orchestrator.vector_search(expanded_query, user_id=USER_ID, top_k=20)
        t_vec = time.perf_counter() - t0

        print(f"4. VECTOR SEARCH RESULTS  ({len(vector_results)} hits, {t_vec:.2f}s)")
        print("-" * 100)
        print(f"{'Rank':>4}  {'ChunkID':>8}  {'DocID':>6}  {'Cos Score':>11}  {'Document Name':<40}  Preview")
        print("-" * 100)
        for i, r in enumerate(vector_results, 1):
            chunk = r['chunk']
            doc_id = getattr(chunk, 'document_id', '?')
            doc_name = doc_map.get(doc_id, f"DocID:{doc_id}")
            preview = (getattr(chunk, 'content', '') or '')[:80].replace('\n', ' ').replace('\r', '')
            print(f"{i:>4}  {r['id']:>8}  {doc_id:>6}  {r['score']:>11.4f}  {doc_name:<40}  {preview}...")
        print()

        # ─── 5. RRF Merge ───
        merged = orchestrator.merge_results(bm25_results, vector_results, top_k=20)
        print(f"5. RRF MERGED CANDIDATES  ({len(merged)} results)")
        print("-" * 100)
        print(f"{'Rank':>4}  {'ChunkID':>8}  {'DocID':>6}  {'RRF Score':>11}  {'Sources':<25}  {'Document Name':<40}  Preview")
        print("-" * 100)
        for i, r in enumerate(merged, 1):
            chunk = r['chunk']
            doc_id = getattr(chunk, 'document_id', '?')
            doc_name = doc_map.get(doc_id, f"DocID:{doc_id}")
            sources = ", ".join(r.get('sources', []))
            preview = (getattr(chunk, 'content', '') or '')[:60].replace('\n', ' ').replace('\r', '')
            print(f"{i:>4}  {r['id']:>8}  {doc_id:>6}  {r['score']:>11.6f}  {sources:<25}  {doc_name:<40}  {preview}...")
        print()

        # ─── 6. Neighbor Expansion ───
        merged_with_neighbors = await orchestrator.fetch_neighbor_chunks(QUERY, merged)
        print(f"6. NEIGHBOR EXPANSION  (content expanded for {len(merged_with_neighbors)} candidates)")
        for i, r in enumerate(merged_with_neighbors[:5], 1):
            chunk = r['chunk']
            content_len = len(getattr(chunk, 'content', '') or '')
            sources = ", ".join(r.get('sources', []))
            print(f"   Rank {i}: ChunkID={r['id']}, content_len={content_len} chars, sources=[{sources}]")
        print()

        # ─── 7. Reranking ───
        t0 = time.perf_counter()
        reranked = orchestrator.rerank_results(expanded_query, merged_with_neighbors, top_k=20)
        t_rerank = time.perf_counter() - t0

        print(f"7. RERANKED RESULTS  ({len(reranked)} results, {t_rerank:.2f}s)")
        print("-" * 100)
        print(f"{'Rank':>4}  {'ChunkID':>8}  {'DocID':>6}  {'RRF Score':>11}  {'Rerank Score':>13}  {'Sources':<25}  {'Document Name':<40}")
        print("-" * 100)
        for i, r in enumerate(reranked, 1):
            chunk = r['chunk']
            doc_id = getattr(chunk, 'document_id', '?')
            doc_name = doc_map.get(doc_id, f"DocID:{doc_id}")
            sources = ", ".join(r.get('sources', []))
            print(f"{i:>4}  {r['id']:>8}  {doc_id:>6}  {r['score']:>11.6f}  {r['similarity']:>13.4f}  {sources:<25}  {doc_name:<40}")
        print()

        # ─── 8. Final Context Sent to LLM ───
        final_chunks = [r['chunk'] for r in reranked[:8]]  # top 8 sent to LLM
        context_string, citations = ContextBuilder.build_context(final_chunks)

        print(f"8. FINAL CONTEXT SENT TO LLM  ({len(final_chunks)} chunks, {len(context_string)} chars)")
        print("=" * 100)
        # Print first 4000 chars of context
        if len(context_string) > 4000:
            print(context_string[:4000])
            print(f"\n... [TRUNCATED — total {len(context_string)} chars] ...")
        else:
            print(context_string)
        print("=" * 100)

        print(f"\n9. CITATIONS METADATA:")
        for c in citations:
            print(f"   Source {c['source_index']}: ChunkID={c['chunk_id']}, DocID={c['document_id']}, "
                  f"File={c['filename']}")

        print("\n" + "=" * 100)
        print("TRACE COMPLETE — No LLM answer was generated.")
        print("=" * 100)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_trace())
