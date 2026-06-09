import logging
from typing import List, Tuple
from sentence_transformers import CrossEncoder
from app.core.config import settings
from app.models.document import DocumentChunk

logger = logging.getLogger(__name__)

class Reranker:
    """
    Reranks document chunks against a query using a Cross-Encoder model.
    """
    _model = None

    @classmethod
    def get_model(cls) -> CrossEncoder:
        if cls._model is None:
            logger.info(f"Loading Cross-Encoder model: {settings.RERANKER_MODEL_NAME}...")
            # Automatically uses GPU if available, falls back to CPU
            cls._model = CrossEncoder(settings.RERANKER_MODEL_NAME)
            logger.info("Cross-Encoder model loaded successfully.")
        return cls._model

    def rerank(self, query: str, chunks: List[DocumentChunk]) -> List[Tuple[DocumentChunk, float]]:
        """
        Computes semantic relevance scores for (query, chunk_text) pairs.
        Returns a list of (chunk, score) sorted descending by relevance score.
        """
        if not chunks:
            return []

        try:
            model = self.get_model()
            pairs = [(query, chunk.content) for chunk in chunks]
            scores = model.predict(pairs)
            
            # Zip and sort descending
            results = list(zip(chunks, [float(s) for s in scores]))
            results.sort(key=lambda x: x[1], reverse=True)
            return results
        except Exception as e:
            logger.error(f"Error during reranking: {str(e)}. Falling back to input order.")
            return [(chunk, 0.0) for chunk in chunks]
