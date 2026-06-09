"""OCR Service Module"""
from .base import BaseOCRProvider, OCRResult, TextRegion, Table, OCRLanguage

# Lazy imports for providers to avoid dependency issues
def __getattr__(name):
    if name == "OCRFactory":
        from .factory import OCRFactory
        return OCRFactory
    elif name == "PaddleOCRProvider":
        from .paddle_provider import PaddleOCRProvider
        return PaddleOCRProvider
    elif name == "TesseractOCRProvider":
        from .tesseract_provider import TesseractOCRProvider
        return TesseractOCRProvider
    elif name == "DocTRProvider":
        from .doctr_provider import DocTRProvider
        return DocTRProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "BaseOCRProvider",
    "OCRResult",
    "TextRegion",
    "Table",
    "OCRLanguage",
    "OCRFactory",
    "PaddleOCRProvider",
    "TesseractOCRProvider",
    "DocTRProvider",
]
