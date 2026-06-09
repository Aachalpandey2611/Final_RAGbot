import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.document import Document, DocumentChunk

async def check():
    async with AsyncSessionLocal() as session:
        # Get all documents
        res = await session.execute(select(Document))
        docs = res.scalars().all()
        print(f"Total documents in database: {len(docs)}")
        for d in docs:
            print(f"- Doc ID {d.id}: {d.original_filename}")
            
            # Count chunks
            c_res = await session.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == d.id)
            )
            chunks = c_res.scalars().all()
            print(f"  - Total chunks: {len(chunks)}")
            embedded_chunks = [c for c in chunks if c.embedding is not None]
            print(f"  - Embedded chunks: {len(embedded_chunks)}")
            if len(chunks) > 0:
                print(f"  - Sample chunk content: {chunks[0].content[:100]}...")

if __name__ == "__main__":
    asyncio.run(check())
