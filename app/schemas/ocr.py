"""OCR Schemas"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Tuple
from enum import Enum


class OCRProviderEnum(str, Enum):
    """Available OCR providers"""
    PADDLE = "paddle"
    TESSERACT = "tesseract"
    DOCTR = "doctr"


class OCRLanguageEnum(str, Enum):
    """Supported OCR languages"""
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
    AUTO = "auto"


class TextRegionSchema(BaseModel):
    """Text region with bounding box"""
    text: str = Field(..., description="Extracted text")
    bbox: Tuple[float, float, float, float] = Field(..., description="Bounding box (x1, y1, x2, y2)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    language: Optional[str] = Field(None, description="Detected language")
    
    class Config:
        from_attributes = True


class TableSchema(BaseModel):
    """Extracted table"""
    rows: List[List[str]] = Field(..., description="Table rows")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    bbox: Tuple[float, float, float, float] = Field(..., description="Table bounding box")
    
    class Config:
        from_attributes = True


class OCRResultSchema(BaseModel):
    """OCR processing result"""
    text: str = Field(..., description="Extracted full text")
    regions: List[TextRegionSchema] = Field(..., description="Text regions with bounding boxes")
    tables: List[TableSchema] = Field(default=[], description="Extracted tables")
    languages_detected: List[str] = Field(default=[], description="Detected languages")
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    image_width: int = Field(..., description="Image width in pixels")
    image_height: int = Field(..., description="Image height in pixels")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    provider: str = Field(..., description="OCR provider used")
    
    class Config:
        from_attributes = True


class OCRRequestSchema(BaseModel):
    """OCR processing request"""
    provider: Optional[OCRProviderEnum] = Field(
        OCRProviderEnum.PADDLE,
        description="OCR provider to use"
    )
    languages: Optional[List[OCRLanguageEnum]] = Field(
        [OCRLanguageEnum.ENGLISH],
        description="Languages to recognize"
    )
    extract_tables: bool = Field(
        True,
        description="Whether to extract tables"
    )
    preprocess: bool = Field(
        True,
        description="Whether to preprocess image"
    )
    confidence_threshold: float = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold"
    )


class OCRStatusSchema(BaseModel):
    """OCR processing status"""
    task_id: str = Field(..., description="Task ID")
    status: str = Field(..., description="Processing status (pending, processing, completed, failed)")
    progress: int = Field(0, ge=0, le=100, description="Progress percentage")
    result: Optional[OCRResultSchema] = Field(None, description="Processing result")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        from_attributes = True


class OCRBatchRequestSchema(BaseModel):
    """Batch OCR processing request"""
    task_name: str = Field(..., description="Task name")
    provider: Optional[OCRProviderEnum] = Field(
        OCRProviderEnum.PADDLE,
        description="OCR provider to use"
    )
    languages: Optional[List[OCRLanguageEnum]] = Field(
        [OCRLanguageEnum.ENGLISH],
        description="Languages to recognize"
    )
    extract_tables: bool = Field(True, description="Whether to extract tables")
    preprocess: bool = Field(True, description="Whether to preprocess images")


class OCRBatchStatusSchema(BaseModel):
    """Batch OCR processing status"""
    batch_id: str = Field(..., description="Batch ID")
    status: str = Field(..., description="Processing status")
    total_files: int = Field(..., description="Total files in batch")
    processed_files: int = Field(..., description="Number of processed files")
    failed_files: int = Field(..., description="Number of failed files")
    progress: int = Field(0, ge=0, le=100, description="Progress percentage")
    results: Optional[List[Dict]] = Field(None, description="Processing results")
