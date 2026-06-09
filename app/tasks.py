import asyncio
import logging
from celery import shared_task
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.services.chunk import DocumentChunkService
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)

# Synchronous execution helper inside event loop for async services
def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# Create task engine and session maker
engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI_ASYNC, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="app.tasks.chunk_document_task"
)
def chunk_document_task(self, document_id: int, user_id: int, chunk_size: int = None, chunk_overlap: int = None):
    """
    Background worker task to parse and segment documents asynchronously.
    """
    logger.info(f"Background task: Segmenting document_id={document_id} for user_id={user_id}")
    
    async def run():
        async with AsyncSessionLocal() as db:
            service = DocumentChunkService(db)
            await service.chunk_document(
                document_id=document_id,
                user_id=user_id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            # Commit changes since session is managed manually here
            await db.commit()

    try:
        run_async(run())
        logger.info(f"Background task: Segmenting completed successfully for document_id={document_id}")
    except Exception as exc:
        logger.error(f"Error during chunking segment task: {str(exc)}")
        # Exponential backoff retry
        raise self.retry(exc=exc, countdown=min(2 ** self.request.retries * 10, 180))


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=15,
    name="app.tasks.embed_document_chunks_task"
)
def embed_document_chunks_task(self, document_id: int, user_id: int, provider: str = None):
    """
    Background worker task to generate vector embeddings asynchronously.
    Features automatic retry logic to handle rate limit blocks or timeout failures.
    """
    logger.info(f"Background task: Generating embeddings for document_id={document_id}")
    
    async def run():
        async with AsyncSessionLocal() as db:
            service = EmbeddingService(db)
            await service.embed_document(
                document_id=document_id,
                user_id=user_id,
                provider_name=provider
            )
            await db.commit()

    try:
        run_async(run())
        logger.info(f"Background task: Embedding generated successfully for document_id={document_id}")
    except Exception as exc:
        logger.error(f"Error generating embeddings asynchronously: {str(exc)}")
        raise self.retry(exc=exc, countdown=min(2 ** self.request.retries * 20, 300))
