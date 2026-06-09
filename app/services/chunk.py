import os
import logging
import re
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from app.core.config import settings
except Exception:
    settings = None
from app.models.document import Document, DocumentChunk
from app.repositories.document import DocumentRepository
from app.repositories.chunk import DocumentChunkRepository
from app.services.ingestion.loaders import PDFLoader, DocxLoader, CSVLoader, TextLoader, ExcelLoader, ZipLoader, ImageLoader
from app.services.chunking import AdaptiveChunkingEngine

logger = logging.getLogger(__name__)

class DocumentChunkService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.chunk_repo = DocumentChunkRepository(db)

    async def chunk_document(
        self, 
        document_id: int, 
        user_id: int, 
        chunk_size: Optional[int] = None, 
        chunk_overlap: Optional[int] = None
    ) -> List[DocumentChunk]:
        """
        Loads document, extracts text using the appropriate loader,
        chunks the text, deletes any existing chunks, and saves the new chunks.
        """
        # 1. Fetch document and verify ownership
        document = await self.doc_repo.get_by_id_and_owner(document_id, user_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found."
            )

        if not os.path.exists(document.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found on disk."
            )

        # 2. Select Loader based on file type
        ext = os.path.splitext(document.original_filename)[1].lower()
        if ext == ".pdf":
            loader = PDFLoader()
        elif ext in [".docx", ".doc"]:
            loader = DocxLoader()
        elif ext == ".csv":
            loader = CSVLoader()
        elif ext in [".txt", ".md"]:
            loader = TextLoader()
        elif ext in [".xlsx", ".xls"]:
            loader = ExcelLoader()
        elif ext in [".zip"]:
            loader = ZipLoader()
        elif ext in [".png", ".jpg", ".jpeg"]:
            loader = ImageLoader()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format for chunking: {ext}"
            )

        # 3. Extract text
        try:
            loaded_parts = await loader.load(document.file_path)
        except Exception as e:
            logger.error(f"Error loading document {document_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to extract text from document: {str(e)}"
            )

        if not loaded_parts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No text could be extracted from the document."
            )

        # 4. Chunk text recursively
        # Use settings if available, otherwise default values
        default_chunk_size = getattr(settings, "DEFAULT_CHUNK_SIZE", 1000)
        default_chunk_overlap = getattr(settings, "DEFAULT_CHUNK_OVERLAP", 200)
        chunk_size = chunk_size if chunk_size is not None else default_chunk_size
        chunk_overlap = chunk_overlap if chunk_overlap is not None else default_chunk_overlap

        if chunk_overlap >= chunk_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chunk overlap must be smaller than chunk size."
            )

        chunker = AdaptiveChunkingEngine()
        chunks_to_create = []
        chunk_index = 0

        for part in loaded_parts:
            text = part["text"]
            base_meta = part.get("metadata", {})

            # Generate chunks using adaptive engine
            sub_chunks = chunker.chunk(text)
            for text_chunk in sub_chunks:
                # Sanitize text to remove null bytes that crash PostgreSQL
                text_chunk = text_chunk.replace('\x00', '')
                
                # Infer simple chunk metadata
                chunk_type = None
                section_title = None
                page_number = base_meta.get("page") if isinstance(base_meta, dict) else None

                # Heuristics to set chunk_type and section_title
                if text_chunk.strip().startswith("|") or "|" in text_chunk.splitlines()[0]:
                    chunk_type = "table"
                elif text_chunk.strip().startswith("def ") or text_chunk.strip().startswith("class "):
                    chunk_type = "code"
                elif re.match(r"(?m)^#{1,6}\s+", text_chunk):
                    chunk_type = "manual_heading"
                    # Extract heading line
                    first_line = text_chunk.strip().splitlines()[0]
                    section_title = first_line.strip('# ').strip()
                elif re.match(r"(?m)^(Section\s+\d+|\d+\.|\d+\.\d+)", text_chunk):
                    chunk_type = "policy_section"
                    first_line = text_chunk.strip().splitlines()[0]
                    section_title = first_line
                else:
                    chunk_type = "text"

                meta = {
                    **(base_meta or {}),
                    "original_filename": document.original_filename,
                    "char_length": len(text_chunk)
                }

                chunks_to_create.append({
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "content": text_chunk,
                    "meta_data": meta,
                    "chunk_type": chunk_type,
                    "chunking_strategy_used": "adaptive",
                    "parent_document_id": base_meta.get("parent_document") if isinstance(base_meta, dict) else None,
                    "section_title": section_title[:250] if section_title else None,
                    "page_number": page_number,
                })
                chunk_index += 1

        # 5. Persist chunks (idempotent: delete old chunks first)
        try:
            # Get old chunks and their IDs to clear from vector store
            old_chunks = await self.chunk_repo.get_by_document(document_id)
            old_ids = [str(c.id) for c in old_chunks]

            # Delete old chunks from PostgreSQL
            await self.chunk_repo.delete_by_document(document_id)

            # Delete old embeddings from Vector Store if they existed
            if old_ids:
                try:
                    from app.services.vector_store import get_vector_store
                    vector_store = get_vector_store()
                    await vector_store.delete(collection_name="document_chunks", ids=old_ids)
                    logger.info(f"Deleted {len(old_ids)} old embeddings from Vector Store for document {document_id}")
                except Exception as vs_err:
                    logger.error(f"Failed to delete old embeddings from vector store: {str(vs_err)}")

            # Insert new chunks
            created_chunks = []
            for chunk_data in chunks_to_create:
                db_chunk = await self.chunk_repo.create(chunk_data)
                created_chunks.append(db_chunk)

            logger.info(f"Successfully chunked document {document_id} into {len(created_chunks)} chunks.")
            return created_chunks

        except Exception as e:
            logger.error(f"Error persisting document chunks for document {document_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save document chunks to database."
            )

    async def get_document_chunks(self, document_id: int, user_id: int) -> List[DocumentChunk]:
        """
        Retrieve chunks for a specific document, verifying ownership first.
        """
        document = await self.doc_repo.get_by_id_and_owner(document_id, user_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found."
            )
        return await self.chunk_repo.get_by_document(document_id)
