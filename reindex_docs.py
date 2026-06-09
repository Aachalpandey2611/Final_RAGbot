import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete

from app.core.config import settings
from app.models.document import Document, DocumentChunk
from app.services.chunking import AdaptiveChunkingEngine
from app.services.embeddings.factory import get_embedding_provider
from app.services.vector_store import get_vector_store

async def reindex_all():
    print("Connecting to DB...")
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI_ASYNC)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    provider = get_embedding_provider("huggingface")
    vector_store = get_vector_store()
    chunker = AdaptiveChunkingEngine(default_chunk_size=1200, default_overlap=300)
    
    async with async_session() as db:
        # 1. Fetch all documents
        print("Fetching documents...")
        res = await db.execute(select(Document))
        docs = res.scalars().all()
        
        if not docs:
            print("No documents found.")
            return
            
        print(f"Found {len(docs)} documents to reindex.")
        
        # 2. Clear all existing chunks
        print("Deleting old chunks from PostgreSQL...")
        await db.execute(delete(DocumentChunk))
        await db.commit()
        
        print("Re-indexing starting...")
        
        for doc in docs:
            print(f"Processing Doc ID: {doc.id} ({doc.filename})")
            
            # Read file content if needed, or if it's already in the DB?
            # Wait, `Document` model does NOT store the raw text in the db. We have to read from the file system.
            file_path = os.path.join(settings.UPLOAD_DIR, doc.filename)
            
            # For simplicity, if we don't have the file, we can't re-index. We will assume the user uploaded the files 
            # and they are in the UPLOAD_DIR. But wait, `test_upload.py` usually loads files. If `doc.filename` is stored, 
            # we need to parse it again or what? Let's check `app/services/ingestion/orchestrator.py`
            # If the files are already in `uploads/`, we can read them. Wait, text extraction depends on the file type.
            # Let's import the extractor.
            from app.services.ingestion.loaders import PDFLoader, DocxLoader, CSVLoader, TextLoader, ExcelLoader, ZipLoader
            
            # Simple factory based on filename
            ext = doc.filename.split('.')[-1].lower() if '.' in doc.filename else ''
            if ext == 'pdf':
                loader = PDFLoader()
            elif ext in ('doc', 'docx'):
                loader = DocxLoader()
            elif ext == 'csv':
                loader = CSVLoader()
            elif ext in ('xls', 'xlsx'):
                loader = ExcelLoader()
            elif ext == 'zip':
                loader = ZipLoader()
            else:
                loader = TextLoader()
                
            try:
                if not os.path.exists(file_path):
                    if hasattr(doc, 'file_path') and doc.file_path and os.path.exists(doc.file_path):
                        file_path = doc.file_path
                    else:
                        print(f"File {file_path} not found.")
                        continue
                        
                documents_data = await loader.load(file_path)
                content = "\n\n".join([d['text'] for d in documents_data])
                content = content.replace('\x00', '')
                    
                # Chunk
                texts = chunker.chunk(content, doc_type="auto", chunk_size=1200, chunk_overlap=300)
                
                new_chunks = []
                for idx, t in enumerate(texts):
                    c = DocumentChunk(document_id=doc.id, content=t, chunk_index=idx)
                    db.add(c)
                    new_chunks.append(c)
                    
                await db.commit()
                
                # We need to refresh to get IDs
                for c in new_chunks:
                    await db.refresh(c)
                    
                print(f"Created {len(new_chunks)} chunks for Doc {doc.id}")
                
                # Embed and save to vector store
                for c in new_chunks:
                    try:
                        embedding = await provider.embed_text(c.content)
                    except AttributeError:
                        embedding = await provider.embed_query(c.content)
                        
                    metadata = {"document_id": doc.id, "chunk_index": c.chunk_index}
                    await vector_store.insert(
                        collection_name="document_chunks",
                        documents=[c.content],
                        embeddings=[embedding],
                        ids=[str(c.id)],
                        metadatas=[metadata]
                    )
            except Exception as e:
                print(f"Error processing doc {doc.id}: {e}")
                
        print("Re-indexing complete!")

if __name__ == "__main__":
    asyncio.run(reindex_all())
