from app.core.config import settings
from .base import LLMProvider
from .gemini_provider import GeminiLLMProvider

def get_llm_provider(provider_name: str = "gemini") -> LLMProvider:
    """
    Factory function to get the configured LLM provider.
    Currently supports 'gemini'.
    """
    if provider_name.lower() == "gemini":
        return GeminiLLMProvider()
    
    # Fallback to gemini or raise error
    return GeminiLLMProvider()
