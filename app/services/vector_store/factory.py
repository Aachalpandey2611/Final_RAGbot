from app.core.config import settings
from app.services.vector_store.base import VectorStore
from app.services.vector_store.chroma_provider import ChromaVectorStore

# Global instance to avoid multiple connection pools / file locks
_vector_store_instance = None

def get_vector_store() -> VectorStore:
    """
    Factory function to retrieve/create the configured vector store.
    """
    global _vector_store_instance
    if _vector_store_instance is not None:
        return _vector_store_instance

    provider = settings.VECTOR_DB_PROVIDER.lower()
    
    if provider == "chroma":
        _vector_store_instance = ChromaVectorStore(settings.CHROMA_PERSIST_DIRECTORY)
        return _vector_store_instance
    else:
        raise ValueError(f"Unsupported vector store provider: {provider}")
