"""Tesseract OCR Provider Implementation"""
import time
import numpy as np
import pytesseract
from typing import List, Optional
import cv2

from .base import BaseOCRProvider, OCRResult, TextRegion
from .preprocessing import ImagePreprocessor


class TesseractOCRProvider(BaseOCRProvider):
    """Tesseract OCR implementation"""
    
    def __init__(
        self,
        languages: Optional[List[str]] = None,
        tesseract_path: Optional[str] = None,
    ):
        super().__init__(languages)
        self.provider_name = "Tesseract"
        
        if tesseract_path:
            pytesseract.pytesseract.pytesseract_cmd = tesseract_path
    
    @staticmethod
    def _map_to_tesseract_languages(languages: List[str]) -> str:
        """Map language codes to Tesseract format"""
        tesseract_map = {
            "en": "eng",
            "es": "spa",
            "fr": "fra",
            "de": "deu",
            "ch": "chi_sim",  # Chinese Simplified
            "tra": "chi_tra",  # Chinese Traditional
            "ja": "jpn",
            "ko": "kor",
            "ru": "rus",
            "ar": "ara",
            "hi": "hin",
            "pt": "por",
            "it": "ita",
            "vi": "vie",
            "th": "tha",
        }
        
        tess_langs = []
        for lang in languages:
            if lang in tesseract_map:
                tess_langs.append(tesseract_map[lang])
        
        return "+".join(tess_langs) if tess_langs else "eng"
    
    async def extract_text(
        self,
        image: np.ndarray,
        languages: Optional[List[str]] = None,
        extract_tables: bool = True,
    ) -> OCRResult:
        """Extract text from image using Tesseract"""
        start_time = time.time()
        
        if not self.validate_image(image):
            raise ValueError("Invalid image format")
        
        # Preprocess image
        preprocessed = ImagePreprocessor.preprocess_pipeline(
            image,
            deskew=True,
            denoise=True,
            contrast_enhance=True,
            threshold=True,
            resize_scale=2.0,
        )
        
        try:
            # Map languages
            lang_codes = self._map_to_tesseract_languages(
                languages or self.languages
            )
            
            # Get detailed OCR data
            data = pytesseract.image_to_data(
                preprocessed,
                lang=lang_codes,
                output_type=pytesseract.Output.DICT,
                config="--psm 3",
            )
            
            # Parse results
            regions = []
            all_text = []
            confidences = []
            
            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                if not text:
                    continue
                
                conf = float(data["conf"][i])
                if conf < 0:  # Skip low confidence
                    continue
                
                x, y, w, h = (
                    data["left"][i],
                    data["top"][i],
                    data["width"][i],
                    data["height"][i],
                )
                bbox = (x, y, x + w, y + h)
                
                region = TextRegion(
                    text=text,
                    bbox=bbox,
                    confidence=conf / 100.0,  # Tesseract gives 0-100
                )
                regions.append(region)
                all_text.append(text)
                confidences.append(conf / 100.0)
            
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
            raise RuntimeError(f"Tesseract extraction failed: {str(e)}")
    
    async def extract_tables(self, image: np.ndarray) -> List:
        """Table extraction using Tesseract structure"""
        # Tesseract has limited table detection
        # Return empty list - use external table detection if needed
        return []
