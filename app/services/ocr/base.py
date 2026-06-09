"""Base OCR Provider Interface"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import numpy as np


class OCRLanguage(str, Enum):
    """Supported OCR Languages"""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    CHINESE_SIMPLIFIED = "ch"
    CHINESE_TRADITIONAL = "tra"
    JAPANESE = "ja"
    KOREAN = "ko"
    RUSSIAN = "ru"
    ARABIC = "ar"
    HINDI = "hi"
    PORTUGUESE = "pt"
    ITALIAN = "it"
    VIETNAMESE = "vi"
    THAI = "th"
    MULTIPLE = "auto"  # Auto-detect


@dataclass
class TextRegion:
    """Text region with bounding box and confidence"""
    text: str
    bbox: Tuple[float, float, float, float]  # (x1, y1, x2, y2)
    confidence: float
    language: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "language": self.language,
        }


@dataclass
class Table:
    """Extracted table with cells and structure"""
    rows: List[List[str]]
    confidence: float
    bbox: Tuple[float, float, float, float]
    
    def to_dict(self) -> Dict:
        return {
            "rows": self.rows,
            "confidence": self.confidence,
            "bbox": self.bbox,
        }


@dataclass
class OCRResult:
    """OCR Processing Result"""
    text: str
    regions: List[TextRegion]
    tables: List[Table] = field(default_factory=list)
    languages_detected: List[str] = field(default_factory=list)
    overall_confidence: float = 0.0
    image_width: int = 0
    image_height: int = 0
    processing_time_ms: float = 0.0
    provider: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "regions": [r.to_dict() for r in self.regions],
            "tables": [t.to_dict() for t in self.tables],
            "languages_detected": self.languages_detected,
            "overall_confidence": self.overall_confidence,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "processing_time_ms": self.processing_time_ms,
            "provider": self.provider,
        }


class BaseOCRProvider(ABC):
    """Base class for OCR providers"""
    
    def __init__(self, languages: Optional[List[str]] = None):
        self.languages = languages or ["en"]
        self.provider_name = self.__class__.__name__
    
    @abstractmethod
    async def extract_text(
        self,
        image: np.ndarray,
        languages: Optional[List[str]] = None,
        extract_tables: bool = True,
    ) -> OCRResult:
        """
        Extract text from image
        
        Args:
            image: Input image as numpy array
            languages: List of languages to recognize
            extract_tables: Whether to extract tables
            
        Returns:
            OCRResult with extracted text and metadata
        """
        pass
    
    @abstractmethod
    async def extract_tables(
        self,
        image: np.ndarray,
    ) -> List[Table]:
        """
        Extract tables from image
        
        Args:
            image: Input image as numpy array
            
        Returns:
            List of extracted tables
        """
        pass
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return [lang.value for lang in OCRLanguage]
    
    def validate_image(self, image: np.ndarray) -> bool:
        """Validate image format and dimensions"""
        if not isinstance(image, np.ndarray):
            return False
        if len(image.shape) not in [2, 3]:  # Grayscale or color
            return False
        if image.shape[0] < 10 or image.shape[1] < 10:  # Minimum dimensions
            return False
        return True
