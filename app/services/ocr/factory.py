"""OCR Provider Factory"""
from typing import Optional, List
from enum import Enum

from .base import BaseOCRProvider


class OCRProviderType(str, Enum):
    """Supported OCR providers"""
    PADDLE = "paddle"
    TESSERACT = "tesseract"
    DOCTR = "doctr"


class OCRFactory:
    """Factory for creating OCR provider instances"""
    
    _providers = {}  # Will be lazily populated
    _provider_modules = {
        "paddle": ("paddle_provider", "PaddleOCRProvider"),
        "tesseract": ("tesseract_provider", "TesseractOCRProvider"),
        "doctr": ("doctr_provider", "DocTRProvider"),
    }
    
    @classmethod
    def _get_provider_class(cls, provider_type: str):
        """Dynamically load provider class"""
        if provider_type not in cls._provider_modules:
            raise ValueError(f"Unknown provider type: {provider_type}")
        
        # Check if already cached
        if provider_type in cls._providers:
            return cls._providers[provider_type]
        
        # Lazy load the provider class
        module_name, class_name = cls._provider_modules[provider_type]
        module = __import__(f".{module_name}", fromlist=[class_name], level=0)
        provider_class = getattr(module, class_name)
        
        cls._providers[provider_type] = provider_class
        return provider_class
    
    @classmethod
    def create(
        cls,
        provider_type: str,
        languages: Optional[List[str]] = None,
        use_gpu: bool = False,
        **kwargs,
    ) -> BaseOCRProvider:
        """
        Create an OCR provider instance
        
        Args:
            provider_type: Type of provider ('paddle', 'tesseract', 'doctr')
            languages: List of languages to support
            use_gpu: Whether to use GPU acceleration
            **kwargs: Additional provider-specific arguments
            
        Returns:
            OCR provider instance
            
        Raises:
            ValueError: If provider type is not supported
        """
        try:
            provider_enum = OCRProviderType(provider_type.lower())
        except ValueError:
            raise ValueError(
                f"Unsupported OCR provider: {provider_type}. "
                f"Supported providers: {list(OCRProviderType)}"
            )
        
        provider_class = cls._get_provider_class(provider_type.lower())
        
        # Create provider with appropriate arguments
        if provider_enum == OCRProviderType.PADDLE:
            return provider_class(
                languages=languages,
                use_gpu=use_gpu,
                **kwargs,
            )
        elif provider_enum == OCRProviderType.TESSERACT:
            return provider_class(
                languages=languages,
                **kwargs,
            )
        elif provider_enum == OCRProviderType.DOCTR:
            return provider_class(
                languages=languages,
                use_gpu=use_gpu,
                **kwargs,
            )
    
    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """Get list of supported provider types"""
        return [p.value for p in OCRProviderType]
    
    @classmethod
    def register_provider(
        cls,
        name: str,
        provider_class: type,
    ) -> None:
        """Register a custom OCR provider"""
        if not issubclass(provider_class, BaseOCRProvider):
            raise TypeError(
                f"Provider class must inherit from BaseOCRProvider"
            )
        cls._providers[name] = provider_class
