"""DocTR OCR Provider Implementation"""
import time
import numpy as np
from typing import List, Optional
from doctr.io import DocumentFile
from doctr.models import ocr_predictor

from .base import BaseOCRProvider, OCRResult, TextRegion, Table
from .preprocessing import ImagePreprocessor


class DocTRProvider(BaseOCRProvider):
    """DocTR (Document Text Recognition) implementation"""
    
    def __init__(
        self,
        languages: Optional[List[str]] = None,
        use_gpu: bool = False,
    ):
        super().__init__(languages)
        self.provider_name = "DocTR"
        self.use_gpu = use_gpu
        
        # Initialize DocTR
        self.model = ocr_predictor(
            pretrained=True,
            assume_straight_pages=False,
            detect_language=True,
        )
    
    async def extract_text(
        self,
        image: np.ndarray,
        languages: Optional[List[str]] = None,
        extract_tables: bool = True,
    ) -> OCRResult:
        """Extract text from image using DocTR"""
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
            # Create document from image
            doc = DocumentFile.from_pdf(preprocessed)
            
            # Run OCR
            result = self.model(preprocessed)
            
            # Parse results
            regions = []
            tables = []
            all_text = []
            confidences = []
            detected_languages = set()
            
            # Process pages
            for page in result.pages:
                h, w = page.dimensions
                
                # Extract text from blocks
                for block in page.blocks:
                    for line in block.lines:
                        for word in line.words:
                            if word.value:
                                # Get bounding box
                                bbox = word.geometry
                                # DocTR returns (x_min, y_min, x_max, y_max) normalized
                                # Convert to pixel coordinates
                                x1 = int(bbox[0][0] * w)
                                y1 = int(bbox[0][1] * h)
                                x2 = int(bbox[1][0] * w)
                                y2 = int(bbox[1][1] * h)
                                
                                region = TextRegion(
                                    text=word.value,
                                    bbox=(x1, y1, x2, y2),
                                    confidence=word.confidence,
                                )
                                regions.append(region)
                                all_text.append(word.value)
                                confidences.append(word.confidence)
                
                # Extract tables if requested
                if extract_tables and hasattr(page, "tables"):
                    for tbl in page.tables:
                        table_data = self._parse_table(tbl, w, h)
                        if table_data:
                            tables.append(table_data)
            
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
                tables=tables,
                languages_detected=list(detected_languages) or (languages or self.languages),
                overall_confidence=overall_confidence,
                image_width=w,
                image_height=h,
                processing_time_ms=processing_time,
                provider=self.provider_name,
            )
        
        except Exception as e:
            raise RuntimeError(f"DocTR extraction failed: {str(e)}")
    
    async def extract_tables(self, image: np.ndarray) -> List[Table]:
        """Extract tables from image using DocTR's table detection"""
        try:
            # Create document and run OCR
            doc = DocumentFile.from_pdf(image)
            result = self.model(image)
            
            tables = []
            for page in result.pages:
                h, w = page.dimensions
                if hasattr(page, "tables"):
                    for tbl in page.tables:
                        table_data = self._parse_table(tbl, w, h)
                        if table_data:
                            tables.append(table_data)
            
            return tables
        
        except Exception as e:
            raise RuntimeError(f"DocTR table extraction failed: {str(e)}")
    
    @staticmethod
    def _parse_table(tbl, page_width: int, page_height: int) -> Optional[Table]:
        """Parse table structure into Table object"""
        try:
            rows = []
            if hasattr(tbl, "rows"):
                for row in tbl.rows:
                    row_cells = []
                    for cell in row:
                        if hasattr(cell, "value"):
                            row_cells.append(cell.value)
                        elif isinstance(cell, str):
                            row_cells.append(cell)
                    if row_cells:
                        rows.append(row_cells)
            
            if not rows:
                return None
            
            # Get table geometry if available
            bbox = (0, 0, page_width, page_height)
            if hasattr(tbl, "geometry"):
                geom = tbl.geometry
                x1 = int(geom[0][0] * page_width)
                y1 = int(geom[0][1] * page_height)
                x2 = int(geom[1][0] * page_width)
                y2 = int(geom[1][1] * page_height)
                bbox = (x1, y1, x2, y2)
            
            confidence = getattr(tbl, "confidence", 0.95)
            
            return Table(
                rows=rows,
                confidence=confidence,
                bbox=bbox,
            )
        except Exception:
            return None
