import google.generativeai as genai
from typing import List
from fastapi import HTTPException, status
import logging
from app.services.embeddings.base import EmbeddingProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self):
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gemini API key is not configured."
            )
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model_name = settings.GEMINI_EMBEDDING_MODEL
        self._dimension = settings.EMBEDDING_DIMENSION

    async def embed_text(self, text: str) -> List[float]:
        try:
            result = genai.embed_content(
                model=self._model_name,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Gemini embedding failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate embedding with Gemini."
            )

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            result = genai.embed_content(
                model=self._model_name,
                content=texts,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Gemini batch embedding failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate batch embeddings with Gemini."
            )

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension
