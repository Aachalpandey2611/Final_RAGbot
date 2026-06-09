from typing import List

class EmbeddingProvider:
    """
    Abstract base class for all embedding providers.
    """
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        raise NotImplementedError()
        
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        raise NotImplementedError()

    @property
    def model_name(self) -> str:
        """Return the name of the model being used."""
        raise NotImplementedError()

    @property
    def dimension(self) -> int:
        """Return the dimension of the embedding vectors."""
        raise NotImplementedError()
