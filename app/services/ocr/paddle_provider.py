"""PaddleOCR Provider Implementation"""
import time
import numpy as np
from typing import List, Optional, Tuple
from paddleocr import PaddleOCR

from .base import BaseOCRProvider, OCRResult, TextRegion
from .preprocessing import ImagePreprocessor


class PaddleOCRProvider(BaseOCRProvider):
    """PaddleOCR implementation"""
    
    def __init__(
        self,
        languages: Optional[List[str]] = None,
        use_gpu: bool = False,
        model_version: str = "2.7",
    ):
        super().__init__(languages)
        self.use_gpu = use_gpu
        self.model_version = model_version
        
        # Initialize PaddleOCR
        lang_codes = self._map_to_paddle_languages(languages or ["en"])
        self.ocr = PaddleOCR(
            use_gpu=use_gpu,
            lang=lang_codes,
            show_log=False,
        )
        self.provider_name = "PaddleOCR"
    
    @staticmethod
    def _map_to_paddle_languages(languages: List[str]) -> str:
        """Map language codes to PaddleOCR format"""
        paddle_map = {
            "en": "en",
            "ch": "ch",  # Chinese Simplified
            "tra": "ch_tra",  # Chinese Traditional
            "ja": "japan",
            "ko": "korean",
            "es": "es",
            "pt": "pt",
            "ru": "ru",
            "ar": "ar",
            "hi": "hi",
            "th": "th",
            "vi": "vi",
            "de": "de",
            "fr": "fr",
            "it": "it",
        }
        
        paddle_langs = []
        for lang in languages:
            if lang in paddle_map:
                paddle_langs.append(paddle_map[lang])
        
        return ",".join(paddle_langs) if paddle_langs else "en"
    
    async def extract_text(
        self,
        image: np.ndarray,
        languages: Optional[List[str]] = None,
        extract_tables: bool = True,
    ) -> OCRResult:
        """Extract text from image using PaddleOCR"""
        start_time = time.time()
        
        if not self.validate_image(image):
            raise ValueError("Invalid image format")
        
        # Preprocess image
        preprocessed = ImagePreprocessor.preprocess_pipeline(
            image,
            deskew=True,
            denoise=True,
            contrast_enhance=True,
            resize_scale=2.0,
        )
        
        try:
            # Run OCR
            result = self.ocr.ocr(preprocessed, cls=True)
            
            if not result or not result[0]:
                return OCRResult(
                    text="",
                    regions=[],
                    tables=[],
                    provider=self.provider_name,
                    image_width=image.shape[1],
                    image_height=image.shape[0],
                    processing_time_ms=(time.time() - start_time) * 1000,
                )
            
            # Parse results
            regions = []
            all_text = []
            confidences = []
            
            for line in result[0]:
                if len(line) >= 2:
                    bbox_points = line[0]
                    text = line[1][0]
                    confidence = float(line[1][1])
                    
                    # Convert bbox format
                    xs = [p[0] for p in bbox_points]
                    ys = [p[1] for p in bbox_points]
                    bbox = (min(xs), min(ys), max(xs), max(ys))
                    
                    region = TextRegion(
                        text=text,
                        bbox=bbox,
                        confidence=confidence,
                    )
                    regions.append(region)
                    all_text.append(text)
                    confidences.append(confidence)
            
            # Calculate overall confidence
            overall_confidence = (
                np.mean(confidences) if confidences else 0.0
            )
            
            # Combine text
            combined_text = " ".join(all_text)
            
            processing_time = (time.time() - start_time) * 1000
            
            return OCRResult(
                text=combined_text,
                regions=regions,
                languages_detected=languages or self.languages,
                overall_confidence=overall_confidence,
                image_width=image.shape[1],
                image_height=image.shape[0],
                processing_time_ms=processing_time,
                provider=self.provider_name,
            )
        
        except Exception as e:
            raise RuntimeError(f"PaddleOCR extraction failed: {str(e)}")
    
    async def extract_tables(self, image: np.ndarray) -> List:
        """Table extraction using structure recognition"""
        # PaddleOCR doesn't have dedicated table extraction
        # Return empty list - use external table detection if needed
        return []
