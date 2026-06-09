import logging
import google.generativeai as genai
from fastapi import HTTPException, status
from app.core.config import settings
from .base import LLMProvider

logger = logging.getLogger(__name__)

class GeminiLLMProvider(LLMProvider):
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gemini API key is not configured."
            )
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Using a reliable instruction model. Can be overridden in settings if needed.
        self._model_name = "gemini-2.5-flash"
        self.model = genai.GenerativeModel(self._model_name)

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate_response(self, prompt: str) -> str:
        try:
            logger.info(f"Generating LLM response using {self.model_name}")
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini LLM generation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate response from LLM."
            )

    from typing import AsyncGenerator
    async def generate_response_stream(self, prompt: str) -> 'AsyncGenerator[str, None]':
        try:
            logger.info(f"Streaming LLM response using {self.model_name}")
            response = await self.model.generate_content_async(prompt, stream=True)
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Gemini LLM stream generation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stream response from LLM."
            )
