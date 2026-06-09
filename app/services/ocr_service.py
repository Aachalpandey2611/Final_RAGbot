"""Main OCR Service"""
import io
import time
from typing import Optional, List
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

from app.core.logging import logger
from app.services.ocr.base import BaseOCRProvider, OCRResult
from app.services.ocr.factory import OCRFactory, OCRProviderType
from app.services.ocr.preprocessing import ImagePreprocessor


class OCRService:
    """Main OCR service for managing OCR operations"""
    
    # Supported file formats
    SUPPORTED_FORMATS = {"png", "jpg", "jpeg", "tiff", "tif", "pdf"}
    
    def __init__(
        self,
        default_provider: str = "paddle",
        languages: Optional[List[str]] = None,
        use_gpu: bool = False,
    ):
        self.default_provider = default_provider
        self.languages = languages or ["en"]
        self.use_gpu = use_gpu
        self.providers = {}
    
    def get_provider(
        self,
        provider_type: Optional[str] = None,
    ) -> BaseOCRProvider:
        """
        Get or create an OCR provider
        
        Args:
            provider_type: Type of provider to use (defaults to default_provider)
            
        Returns:
            OCR provider instance
        """
        provider_type = provider_type or self.default_provider
        
        if provider_type not in self.providers:
            try:
                self.providers[provider_type] = OCRFactory.create(
                    provider_type,
                    languages=self.languages,
                    use_gpu=self.use_gpu,
                )
                logger.info(f"Initialized {provider_type} OCR provider")
            except Exception as e:
                logger.error(f"Failed to initialize {provider_type}: {str(e)}")
                raise
        
        return self.providers[provider_type]
    
    async def extract_text_from_file(
        self,
        file_path: str,
        provider: Optional[str] = None,
        languages: Optional[List[str]] = None,
        preprocess: bool = True,
    ) -> OCRResult:
        """
        Extract text from a file
        
        Args:
            file_path: Path to image or PDF file
            provider: OCR provider to use
            languages: Languages to recognize
            preprocess: Whether to preprocess image
            
        Returns:
            OCR result
        """
        file_ext = Path(file_path).suffix.lower().lstrip(".")
        
        if file_ext not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported file format: {file_ext}. "
                f"Supported formats: {self.SUPPORTED_FORMATS}"
            )
        
        # Load image
        if file_ext == "pdf":
            images = self._load_pdf(file_path)
        else:
            image = cv2.imread(file_path)
            if image is None:
                raise ValueError(f"Failed to load image: {file_path}")
            images = [image]
        
        # Process each page/image
        results = []
        for image in images:
            result = await self.extract_text_from_image(
                image,
                provider=provider,
                languages=languages,
                preprocess=preprocess,
            )
            results.append(result)
        
        # Combine results if multiple pages
        if len(results) == 1:
            return results[0]
        
        return self._combine_results(results)
    
    async def extract_text_from_image(
        self,
        image: np.ndarray,
        provider: Optional[str] = None,
        languages: Optional[List[str]] = None,
        preprocess: bool = True,
    ) -> OCRResult:
        """
        Extract text from an image array
        
        Args:
            image: Image as numpy array or PIL Image
            provider: OCR provider to use
            languages: Languages to recognize
            preprocess: Whether to preprocess image
            
        Returns:
            OCR result
        """
        # Convert PIL Image to numpy array if needed
        if isinstance(image, Image.Image):
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Validate image
        if not isinstance(image, np.ndarray):
            raise ValueError("Image must be numpy array or PIL Image")
        
        # Preprocess if requested
        if preprocess:
            image = ImagePreprocessor.preprocess_pipeline(image)
        
        # Get provider and extract text
        ocr_provider = self.get_provider(provider)
        result = await ocr_provider.extract_text(
            image,
            languages=languages or self.languages,
            extract_tables=True,
        )
        
        return result
    
    async def extract_text_from_bytes(
        self,
        file_bytes: bytes,
        file_name: str,
        provider: Optional[str] = None,
        languages: Optional[List[str]] = None,
    ) -> OCRResult:
        """
        Extract text from file bytes
        
        Args:
            file_bytes: File content as bytes
            file_name: Original file name (for format detection)
            provider: OCR provider to use
            languages: Languages to recognize
            
        Returns:
            OCR result
        """
        file_ext = Path(file_name).suffix.lower().lstrip(".")
        
        if file_ext == "pdf":
            # For PDF, we need to convert to images first
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(file_bytes)
            
            results = []
            for image in images:
                result = await self.extract_text_from_image(
                    np.array(image),
                    provider=provider,
                    languages=languages,
                )
                results.append(result)
            
            return self._combine_results(results) if len(results) > 1 else results[0]
        else:
            # For image files
            nparr = np.frombuffer(file_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("Failed to decode image from bytes")
            
            return await self.extract_text_from_image(
                image,
                provider=provider,
                languages=languages,
            )
    
    async def extract_tables(
        self,
        image: np.ndarray,
        provider: Optional[str] = None,
    ) -> List:
        """
        Extract tables from image
        
        Args:
            image: Image as numpy array
            provider: OCR provider to use
            
        Returns:
            List of extracted tables
        """
        ocr_provider = self.get_provider(provider)
        return await ocr_provider.extract_tables(image)
    
    @staticmethod
    def _load_pdf(pdf_path: str) -> List[np.ndarray]:
        """Convert PDF pages to images"""
        try:
            from pdf2image import convert_from_path
            images_pil = convert_from_path(pdf_path, dpi=300)
            images = [cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR) for img in images_pil]
            return images
        except Exception as e:
            raise RuntimeError(f"Failed to load PDF: {str(e)}")
    
    @staticmethod
    def _combine_results(results: List[OCRResult]) -> OCRResult:
        """Combine results from multiple pages"""
        combined_text = " ".join([r.text for r in results])
        combined_regions = []
        combined_tables = []
        combined_confidences = []
        
        for result in results:
            combined_regions.extend(result.regions)
            combined_tables.extend(result.tables)
            combined_confidences.append(result.overall_confidence)
        
        overall_confidence = np.mean(combined_confidences) if combined_confidences else 0.0
        
        return OCRResult(
            text=combined_text,
            regions=combined_regions,
            tables=combined_tables,
            overall_confidence=overall_confidence,
            processing_time_ms=sum(r.processing_time_ms for r in results),
            provider=results[0].provider if results else "unknown",
        )
