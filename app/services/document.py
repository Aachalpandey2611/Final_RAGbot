import logging
import os
import uuid
from typing import Dict, Any, List, Optional
import anyio
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document
from app.repositories.document import DocumentRepository

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self, db: AsyncSession):
        self.doc_repo = DocumentRepository(db)

    async def upload_document(self, file: UploadFile, user_id: int) -> Document:
        """
        Validate, save to disk, and save metadata of an uploaded document.
        """
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename cannot be empty."
            )

        # 1. Validate File Extension
        ext = os.path.splitext(file.filename)[1].lower()
        allowed_exts = {".pdf", ".docx", ".doc", ".txt", ".csv", ".md", ".png", ".jpg", ".jpeg", ".xlsx", ".xls", ".zip"}
        if ext not in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '{ext}' is not allowed. Supported extensions: .pdf, .docx, .doc, .txt, .csv, .md, .png, .jpg, .jpeg, .xlsx, .xls, .zip"
            )

        # 2. Validate MIME Type / Content Type
        # We also added "text/markdown" and "application/octet-stream" in config to support md files
        if file.content_type not in settings.ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{file.content_type}' is not allowed. Supported types: PDF, DOCX, TXT, CSV, MD."
            )

        # 3. Validate File Size using UploadFile.size (if available, otherwise we'll check while reading)
        if file.size and file.size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds the maximum allowed limit of {settings.MAX_UPLOAD_SIZE / (1024 * 1024)}MB."
            )

        # 4. Generate Secure Unique Filename
        secure_filename = f"{uuid.uuid4()}{ext}"
        
        # Ensure upload directory exists
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(settings.UPLOAD_DIR, secure_filename)

        # 5. Save the file in chunks to disk & verify size limits on-the-fly
        await file.seek(0)
        actual_size = 0
        try:
            async with await anyio.open_file(file_path, "wb") as out_file:
                while True:
                    chunk = await file.read(8192)
                    if not chunk:
                        break
                    actual_size += len(chunk)
                    if actual_size > settings.MAX_UPLOAD_SIZE:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File size exceeds the maximum allowed limit of {settings.MAX_UPLOAD_SIZE / (1024 * 1024)}MB."
                        )
                    await out_file.write(chunk)
        except HTTPException:
            # Delete the partially written file if size limit was exceeded
            if os.path.exists(file_path):
                os.remove(file_path)
            raise
        except Exception as e:
            logger.error(f"Error writing file to disk: {str(e)}")
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while saving the file."
            )

        # 6. Save metadata in DB
        try:
            document_data = {
                "filename": secure_filename,
                "original_filename": file.filename,
                "file_type": file.content_type,
                "file_path": file_path,
                "file_size": actual_size,
                "user_id": user_id,
            }
            document = await self.doc_repo.create(document_data)
            logger.info(f"Document uploaded and registered: {secure_filename} for user_id={user_id}")
            return document
        except Exception as e:
            logger.error(f"Error saving document metadata: {str(e)}")
            # Cleanup file from disk if DB insert fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while saving the document metadata."
            )

    async def list_documents(
        self, user_id: int, skip: int = 0, limit: int = 50
    ) -> Dict[str, Any]:
        """
        List all documents for a specific user.
        """
        documents = await self.doc_repo.get_by_user(user_id, skip, limit)
        total = await self.doc_repo.count_by_user(user_id)
        return {"total": total, "documents": documents}

    async def get_document(self, document_id: int, user_id: int) -> Document:
        """
        Get document details. Validates ownership.
        """
        document = await self.doc_repo.get_by_id_and_owner(document_id, user_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found."
            )
        return document

    async def delete_document(self, document_id: int, user_id: int) -> None:
        """
        Delete a document metadata from DB, remove the file from disk, and clean up vector store.
        """
        document = await self.doc_repo.get_by_id_and_owner(document_id, user_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found."
            )
        
        # 1. Clean up from Vector Store
        try:
            from app.repositories.chunk import DocumentChunkRepository
            chunk_repo = DocumentChunkRepository(self.doc_repo.db)
            chunks = await chunk_repo.get_by_document(document_id)
            chunk_ids = [str(c.id) for c in chunks]
            if chunk_ids:
                from app.services.vector_store import get_vector_store
                vector_store = get_vector_store()
                await vector_store.delete(collection_name="document_chunks", ids=chunk_ids)
                logger.info(f"Deleted {len(chunk_ids)} embeddings from vector store for document {document_id}")
        except Exception as e:
            logger.error(f"Failed to delete embeddings from vector store during document deletion: {str(e)}")

        # 2. Delete from DB
        await self.doc_repo.delete(document.id)
        
        # 3. Delete from Disk
        try:
            if os.path.exists(document.file_path):
                os.remove(document.file_path)
                logger.info(f"Deleted file from disk: {document.file_path}")
        except Exception as e:
            logger.error(f"Failed to delete file from disk {document.file_path}: {str(e)}")
            # We don't fail the request since DB record is already deleted, but we log the error.
