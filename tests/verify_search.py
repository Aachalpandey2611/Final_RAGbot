import asyncio
from app.services.embeddings.factory import get_embedding_provider
from app.services.vector_store import get_vector_store
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.repositories.chunk import DocumentChunkRepository

async def main():
    print(f"Using Vector DB: {settings.VECTOR_DB_PROVIDER}")
    provider = get_embedding_provider("huggingface")
    vector_store = get_vector_store()
    
    query = "leave policy"
    print(f"\nSearching for: '{query}'")
    
    query_embedding = await provider.embed_text(query)
    
    results = await vector_store.search(
        collection_name="document_chunks",
        query_embedding=query_embedding,
        limit=3
    )
    
    print(f"\nFound {len(results)} chunks from Vector DB.")
    
    print("\n--- Top Relevant Chunks ---")
    async with AsyncSessionLocal() as db:
        chunk_repo = DocumentChunkRepository(db)
        for i, res in enumerate(results):
            chunk_id = int(res['id'])
            score = res['score']
            
            chunk = await chunk_repo.get(chunk_id)
            content_preview = chunk.content[:200].replace("\n", " ") + "..." if chunk else "Chunk not found in DB"
            
            print(f"\n[Result {i+1}] (Chunk ID: {chunk_id}, Distance Score: {score:.4f})")
            print(f"Content: {content_preview}")

if __name__ == "__main__":
    asyncio.run(main())
