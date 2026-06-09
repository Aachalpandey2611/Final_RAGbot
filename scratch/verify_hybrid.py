import asyncio
import os
import sys

# Ensure backend directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.document import DocumentChunk
from app.services.rag.bm25 import BM25
from app.services.rag.reranker import Reranker

async def main():
    print("--- Testing BM25 ---")
    chunks = [
        DocumentChunk(id=1, content="FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.8+ based on standard Python type hints."),
        DocumentChunk(id=2, content="Chroma is the AI-native open-source vector database. Chroma makes it easy to build LLM apps by making knowledge, facts, and skills pluggable for LLMs."),
        DocumentChunk(id=3, content="Hybrid search combines dense vector retrieval with sparse keyword retrieval such as BM25 to get the best of both worlds."),
    ]
    
    bm25 = BM25(chunks)
    scores = bm25.score("hybrid search combinations")
    for chunk, score in scores:
        print(f"Chunk ID: {chunk.id}, BM25 Score: {score:.4f}, Content: {chunk.content[:60]}...")
        
    print("\n--- Testing Reranker ---")
    reranker = Reranker()
    # This will download the cross-encoder model (if not already cached) and rank the chunks
    ranked = reranker.rerank("hybrid search combinations", chunks)
    for chunk, score in ranked:
        print(f"Chunk ID: {chunk.id}, Rerank Score: {score:.4f}, Content: {chunk.content[:60]}...")

if __name__ == "__main__":
    asyncio.run(main())
