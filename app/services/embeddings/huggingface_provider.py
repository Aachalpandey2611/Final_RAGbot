import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List
import logging
from fastapi import HTTPException, status
from app.services.embeddings.base import EmbeddingProvider
from app.core.config import settings

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=2)

class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    _model = None

    def __init__(self):
        self._model_name = settings.HF_EMBEDDING_MODEL
        self._dimension = settings.EMBEDDING_DIMENSION
        self._ensure_model_loaded()

    def _ensure_model_loaded(self):
        if HuggingFaceEmbeddingProvider._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading HuggingFace model: {self._model_name}...")
                HuggingFaceEmbeddingProvider._model = SentenceTransformer(self._model_name)
                logger.info("Model loaded successfully.")
            except ImportError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="sentence-transformers is not installed."
                )
            except Exception as e:
                logger.error(f"Failed to load HF model: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to load HuggingFace embedding model."
                )

    async def embed_text(self, text: str) -> List[float]:
        def _embed():
            return HuggingFaceEmbeddingProvider._model.encode(text).tolist()

        try:
            return await asyncio.get_running_loop().run_in_executor(executor, _embed)
        except Exception as e:
            logger.error(f"HF embedding failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate embedding with HuggingFace."
            )

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        def _embed():
            return HuggingFaceEmbeddingProvider._model.encode(texts).tolist()

        try:
            return await asyncio.get_running_loop().run_in_executor(executor, _embed)
        except Exception as e:
            logger.error(f"HF batch embedding failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate batch embeddings with HuggingFace."
            )

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension
