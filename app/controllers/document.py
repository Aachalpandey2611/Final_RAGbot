import logging
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.schemas.chunk import ChunkListResponse, ChunkCreateRequest
from app.schemas.chunk import ChunkResponse
from app.schemas.embedding import EmbedDocumentRequest, EmbeddingStatusResponse
from app.services.document import DocumentService
from app.services.chunk import DocumentChunkService
from app.repositories.chunk import DocumentChunkRepository
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
    description="Uploads a document (PDF, DOCX, TXT, CSV) up to 10MB, validates it, saves it securely, and stores its metadata.",
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"User {current_user.id} is uploading file: {file.filename}")
    service = DocumentService(db)
    return await service.upload_document(file=file, user_id=current_user.id)

@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List uploaded documents",
    description="Returns a paginated list of all documents uploaded by the authenticated user.",
)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    return await service.list_documents(user_id=current_user.id, skip=skip, limit=limit)

@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
    description="Retrieves metadata details of a specific uploaded document owned by the user.",
)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    return await service.get_document(document_id=document_id, user_id=current_user.id)

@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    description="Deletes document metadata from the database and removes the associated file from the storage system.",
)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"User {current_user.id} requested deletion of document_id={document_id}")
    service = DocumentService(db)
    await service.delete_document(document_id=document_id, user_id=current_user.id)

@router.post(
    "/documents/{document_id}/chunk",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Chunk a document",
    description="Reads document contents, splits it recursively into chunks, and stores them.",
)
async def chunk_document(
    document_id: int,
    req_body: ChunkCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"User {current_user.id} requested chunking of document_id={document_id}")
    # Run chunking synchronously (inline) to avoid Celery broker issues in local dev
    chunk_service = DocumentChunkService(db)
    chunks = await chunk_service.chunk_document(
        document_id=document_id,
        user_id=current_user.id,
        chunk_size=req_body.chunk_size,
        chunk_overlap=req_body.chunk_overlap,
    )
    await db.commit()
    return {
        "message": f"Document chunked successfully into {len(chunks)} chunks.",
        "document_id": document_id,
    }

@router.get(
    "/documents/{document_id}/chunks",
    response_model=ChunkListResponse,
    summary="Get document chunks",
    description="Retrieves a list of all stored text chunks for a specific document.",
)
async def get_document_chunks(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentChunkService(db)
    chunks = await service.get_document_chunks(document_id=document_id, user_id=current_user.id)
    return {
        "document_id": document_id,
        "total": len(chunks),
        "chunks": chunks
    }


@router.get(
    "/chunks/{chunk_id}",
    response_model=ChunkResponse,
    summary="Get a single chunk by id",
    description="Retrieve a single chunk's content and metadata by its id.",
)
async def get_chunk_by_id(
    chunk_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chunk_repo = DocumentChunkRepository(db)
    chunk = await chunk_repo.get(chunk_id)
    if not chunk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")
    # Verify ownership via document relationship
    if chunk.document.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
    return chunk


@router.get(
    "/chunks",
    response_model=ChunkListResponse,
    summary="Query chunks",
    description="Query chunks by type or document",
)
async def query_chunks(
    chunk_type: str | None = Query(None),
    document_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chunk_repo = DocumentChunkRepository(db)
    # Simple filters: by document_id or chunk_type
    if document_id is not None:
        # Verify ownership
        doc_service = DocumentService(db)
        await doc_service.get_document(document_id=document_id, user_id=current_user.id)
        chunks = await chunk_repo.get_by_document(document_id)
    else:
        # Fetch all and filter in-memory (for now)
        all_chunks = await chunk_repo.get_multi(0, 1000)
        chunks = [c for c in all_chunks if (chunk_type is None or c.chunk_type == chunk_type) and c.document.user_id == current_user.id]

    return {"document_id": document_id or 0, "total": len(chunks), "chunks": chunks}

@router.post(
    "/documents/{document_id}/embed",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate embeddings for document chunks",
    description="Generates vector embeddings for all unembedded chunks of a document.",
)
async def embed_document_chunks(
    document_id: int,
    req_body: EmbedDocumentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"User {current_user.id} requested embedding for document_id={document_id}")
    # Run embedding synchronously (inline) to avoid Celery broker issues in local dev
    service = EmbeddingService(db)
    result = await service.embed_document(
        document_id=document_id,
        user_id=current_user.id,
        provider_name=req_body.provider
    )
    await db.commit()
    return {
        "message": "Document embedding completed successfully.",
        "document_id": document_id,
    }

@router.get(
    "/documents/{document_id}/embedding-status",
    response_model=EmbeddingStatusResponse,
    summary="Get document embedding status",
    description="Retrieves the progress of embedding generation for a specific document.",
)
async def get_embedding_status(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = EmbeddingService(db)
    return await service.get_embedding_status(document_id=document_id, user_id=current_user.id)

