from fastapi import HTTPException, status
import logging
from app.services.embeddings.base import EmbeddingProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_embedding_provider(provider_name: str = None) -> EmbeddingProvider:
    """
    Factory function to get the appropriate embedding provider.
    """
    provider_name = provider_name or settings.EMBEDDING_PROVIDER
    
    if provider_name.lower() == "gemini":
        from app.services.embeddings.gemini_provider import GeminiEmbeddingProvider
        return GeminiEmbeddingProvider()
    elif provider_name.lower() == "huggingface":
        from app.services.embeddings.huggingface_provider import HuggingFaceEmbeddingProvider
        return HuggingFaceEmbeddingProvider()
    else:
        logger.error(f"Unknown embedding provider: {provider_name}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown embedding provider configured: {provider_name}"
        )
