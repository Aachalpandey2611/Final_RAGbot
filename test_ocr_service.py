"""
OCR Service Unit Tests - Core Infrastructure
Tests the OCR service components without requiring heavy OCR dependencies
"""

import pytest
import sys
import numpy as np
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Add app to path
sys.path.insert(0, '.')

from app.services.ocr.base import (
    BaseOCRProvider, 
    OCRResult, 
    TextRegion, 
    Table,
    OCRLanguage,
)
from app.services.ocr.factory import OCRFactory, OCRProviderType


class TestOCRDataClasses:
    """Test OCR data classes"""
    
    def test_text_region_creation(self):
        """Test TextRegion creation and serialization"""
        region = TextRegion(
            text="Hello World",
            bbox=(10.0, 20.0, 100.0, 35.0),
            confidence=0.95,
            language="en",
        )
        
        assert region.text == "Hello World"
        assert region.bbox == (10.0, 20.0, 100.0, 35.0)
        assert region.confidence == 0.95
        assert region.language == "en"
        
        # Test serialization
        region_dict = region.to_dict()
        assert region_dict["text"] == "Hello World"
        assert region_dict["confidence"] == 0.95
    
    def test_table_creation(self):
        """Test Table creation and serialization"""
        table = Table(
            rows=[["Header1", "Header2"], ["Cell1", "Cell2"]],
            confidence=0.90,
            bbox=(0.0, 100.0, 500.0, 300.0),
        )
        
        assert len(table.rows) == 2
        assert len(table.rows[0]) == 2
        assert table.confidence == 0.90
        
        # Test serialization
        table_dict = table.to_dict()
        assert len(table_dict["rows"]) == 2
        assert table_dict["confidence"] == 0.90
    
    def test_ocr_result_creation(self):
        """Test OCRResult creation with regions and tables"""
        regions = [
            TextRegion("Text1", (0, 0, 50, 20), 0.95, "en"),
            TextRegion("Text2", (0, 25, 50, 45), 0.92, "en"),
        ]
        tables = [
            Table([["A", "B"], ["C", "D"]], 0.88, (60, 0, 200, 100)),
        ]
        
        result = OCRResult(
            text="Text1 Text2",
            regions=regions,
            tables=tables,
            languages_detected=["en"],
            overall_confidence=0.93,
            image_width=800,
            image_height=600,
            processing_time_ms=1234.5,
            provider="TestProvider",
        )
        
        assert result.text == "Text1 Text2"
        assert len(result.regions) == 2
        assert len(result.tables) == 1
        assert result.overall_confidence == 0.93
        
        # Test serialization
        result_dict = result.to_dict()
        assert "text" in result_dict
        assert "regions" in result_dict
        assert "tables" in result_dict
        assert result_dict["overall_confidence"] == 0.93


class TestOCRLanguageEnum:
    """Test OCR language enumeration"""
    
    def test_language_enum_values(self):
        """Test that all expected languages are available"""
        languages = [lang.value for lang in OCRLanguage]
        
        assert "en" in languages
        assert "es" in languages
        assert "fr" in languages
        assert "ch" in languages
        assert "ja" in languages
        assert "ko" in languages
        assert "ru" in languages
        assert "ar" in languages
    
    def test_language_enum_count(self):
        """Test number of supported languages"""
        languages = list(OCRLanguage)
        assert len(languages) >= 15, "Should support 15+ languages"


class TestBaseOCRProvider:
    """Test BaseOCRProvider interface"""
    
    def test_provider_initialization(self):
        """Test provider initialization with languages"""
        # Create a mock provider
        class MockProvider(BaseOCRProvider):
            async def extract_text(self, image, languages=None, extract_tables=True):
                return OCRResult(
                    text="Mock text",
                    regions=[],
                    provider="Mock",
                )
            
            async def extract_tables(self, image):
                return []
        
        provider = MockProvider(languages=["en", "es"])
        assert provider.languages == ["en", "es"]
        assert provider.provider_name == "MockProvider"
    
    def test_supported_languages(self):
        """Test get_supported_languages method"""
        class MockProvider(BaseOCRProvider):
            async def extract_text(self, image, languages=None, extract_tables=True):
                return OCRResult(text="", regions=[], provider="Mock")
            
            async def extract_tables(self, image):
                return []
        
        provider = MockProvider()
        supported = provider.get_supported_languages()
        
        assert len(supported) >= 15
        assert "en" in supported
        assert "ch" in supported
    
    def test_image_validation(self):
        """Test image validation"""
        class MockProvider(BaseOCRProvider):
            async def extract_text(self, image, languages=None, extract_tables=True):
                return OCRResult(text="", regions=[], provider="Mock")
            
            async def extract_tables(self, image):
                return []
        
        provider = MockProvider()
        
        # Valid grayscale image
        valid_gray = np.zeros((100, 100), dtype=np.uint8)
        assert provider.validate_image(valid_gray) is True
        
        # Valid color image
        valid_color = np.zeros((100, 100, 3), dtype=np.uint8)
        assert provider.validate_image(valid_color) is True
        
        # Invalid: too small
        too_small = np.zeros((5, 5), dtype=np.uint8)
        assert provider.validate_image(too_small) is False
        
        # Invalid: wrong type
        assert provider.validate_image("not an image") is False
        
        # Invalid: wrong shape
        wrong_shape = np.zeros((100, 100, 100, 3), dtype=np.uint8)
        assert provider.validate_image(wrong_shape) is False


class TestOCRFactory:
    """Test OCR provider factory"""
    
    def test_provider_type_enum(self):
        """Test provider type enumeration"""
        providers = [p.value for p in OCRProviderType]
        assert "paddle" in providers
        assert "tesseract" in providers
        assert "doctr" in providers
    
    def test_get_supported_providers(self):
        """Test getting list of supported providers"""
        supported = OCRFactory.get_supported_providers()
        assert len(supported) >= 3
        assert "paddle" in supported
    
    def test_factory_with_mock_provider(self):
        """Test factory pattern with mock provider"""
        class CustomMockProvider(BaseOCRProvider):
            async def extract_text(self, image, languages=None, extract_tables=True):
                return OCRResult(text="Custom", regions=[], provider="CustomMock")
            
            async def extract_tables(self, image):
                return []
        
        # Register custom provider
        OCRFactory.register_provider("custom_mock", CustomMockProvider)
        
        # Verify it was registered
        supported = OCRFactory.get_supported_providers()
        assert "custom_mock" in supported or "CustomMockProvider" in str(supported)


class TestImagePreprocessing:
    """Test image preprocessing module"""
    
    def test_preprocessing_imports(self):
        """Test that preprocessing module can be imported"""
        from app.services.ocr.preprocessing import ImagePreprocessor
        assert hasattr(ImagePreprocessor, 'grayscale')
        assert hasattr(ImagePreprocessor, 'denoise')
        assert hasattr(ImagePreprocessor, 'thresholding')
        assert hasattr(ImagePreprocessor, 'preprocess_pipeline')
    
    def test_grayscale_conversion(self):
        """Test grayscale conversion"""
        from app.services.ocr.preprocessing import ImagePreprocessor
        
        # Create color image (BGR)
        color_image = np.ones((100, 100, 3), dtype=np.uint8) * 100
        
        # Convert to grayscale
        gray = ImagePreprocessor.grayscale(color_image)
        
        assert len(gray.shape) == 2
        assert gray.shape == (100, 100)
    
    def test_resize_operation(self):
        """Test image resizing"""
        from app.services.ocr.preprocessing import ImagePreprocessor
        
        image = np.ones((100, 100), dtype=np.uint8)
        resized = ImagePreprocessor.resize(image, scale=2.0)
        
        assert resized.shape == (200, 200)
    
    def test_preprocessing_pipeline(self):
        """Test full preprocessing pipeline"""
        from app.services.ocr.preprocessing import ImagePreprocessor
        
        # Create test image
        image = np.ones((200, 200, 3), dtype=np.uint8) * 100
        
        # Run pipeline
        result = ImagePreprocessor.preprocess_pipeline(
            image,
            deskew=False,  # Skip deskew as it's complex
            denoise=True,
            contrast_enhance=True,
            threshold=False,
            resize_scale=1.0,
        )
        
        assert result is not None
        assert isinstance(result, np.ndarray)
        assert len(result.shape) == 2  # Should be grayscale


class TestOCRSchemas:
    """Test OCR Pydantic schemas"""
    
    def test_schema_imports(self):
        """Test that schemas can be imported"""
        from app.schemas.ocr import (
            OCRRequestSchema,
            OCRResultSchema,
            OCRStatusSchema,
            OCRBatchRequestSchema,
            OCRBatchStatusSchema,
            TextRegionSchema,
            TableSchema,
        )
        
        # Create valid request
        request = OCRRequestSchema(
            provider="paddle",
            languages=["en"],
            extract_tables=True,
            preprocess=True,
            confidence_threshold=0.3,
        )
        
        assert request.provider == "paddle"
        assert len(request.languages) == 1
        assert request.confidence_threshold == 0.3


class TestOCRModels:
    """Test OCR database models"""
    
    def test_model_imports(self):
        """Test that models can be imported"""
        from app.models.ocr import OCRJob, OCRBatch, OCRCache
        
        # Just verify they can be imported
        assert OCRJob is not None
        assert OCRBatch is not None
        assert OCRCache is not None


class TestOCRRepository:
    """Test OCR repository interface"""
    
    def test_repository_imports(self):
        """Test that repositories can be imported"""
        from app.repositories.ocr import (
            OCRJobRepository,
            OCRBatchRepository,
            OCRCacheRepository,
        )
        
        assert OCRJobRepository is not None
        assert OCRBatchRepository is not None
        assert OCRCacheRepository is not None


class TestOCRController:
    """Test OCR API controller"""
    
    def test_controller_imports(self):
        """Test that controller can be imported"""
        from app.controllers.ocr import router
        
        assert router is not None
        assert hasattr(router, 'routes')


class TestOCRTasks:
    """Test OCR Celery tasks"""
    
    def test_task_imports(self):
        """Test that tasks can be imported"""
        from app.tasks_ocr import (
            process_ocr_file,
            process_ocr_batch,
            cleanup_old_ocr_jobs,
            cleanup_ocr_cache,
            calculate_file_hash,
        )
        
        assert process_ocr_file is not None
        assert process_ocr_batch is not None
        assert cleanup_old_ocr_jobs is not None
        assert cleanup_ocr_cache is not None
    
    def test_file_hash_calculation(self):
        """Test file hash calculation"""
        import tempfile
        import os
        from app.tasks_ocr import calculate_file_hash
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = f.name
        
        try:
            # Calculate hash
            file_hash = calculate_file_hash(temp_path)
            
            # Verify hash is valid SHA256 (64 characters)
            assert len(file_hash) == 64
            assert all(c in '0123456789abcdef' for c in file_hash)
        finally:
            os.unlink(temp_path)


class TestOCRServiceIntegration:
    """Test main OCR service integration"""
    
    def test_ocr_service_initialization(self):
        """Test OCR service can be initialized"""
        from app.services.ocr_service import OCRService
        
        service = OCRService(
            default_provider="paddle",
            languages=["en"],
            use_gpu=False,
        )
        
        assert service.default_provider == "paddle"
        assert "en" in service.languages
        assert service.use_gpu is False
    
    def test_supported_formats(self):
        """Test supported file formats"""
        from app.services.ocr_service import OCRService
        
        service = OCRService()
        
        # Check supported formats
        assert "png" in service.SUPPORTED_FORMATS
        assert "jpg" in service.SUPPORTED_FORMATS
        assert "pdf" in service.SUPPORTED_FORMATS
        assert "tiff" in service.SUPPORTED_FORMATS


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
