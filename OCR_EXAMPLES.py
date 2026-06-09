"""
OCR Service Demo & Usage Examples
Demonstrates how to use the OCR Processing Service
"""

# ============================================================================
# EXAMPLE 1: Basic Text Extraction
# ============================================================================

"""
Extract text from a single image file
"""

import asyncio
from app.services.ocr_service import OCRService

async def basic_extraction_example():
    # Initialize service
    ocr_service = OCRService(
        default_provider="paddle",
        languages=["en"],
        use_gpu=False,
    )
    
    # Extract text from image
    result = await ocr_service.extract_text_from_file(
        "/path/to/document.png",
        provider="paddle",
        languages=["en"],
        preprocess=True,
    )
    
    # Access results
    print(f"Extracted Text: {result.text}")
    print(f"Confidence: {result.overall_confidence:.2%}")
    print(f"Processing Time: {result.processing_time_ms:.0f}ms")
    print(f"Regions Found: {len(result.regions)}")
    print(f"Tables Found: {len(result.tables)}")
    
    # Iterate through text regions
    for region in result.regions:
        print(f"  - '{region.text}' at {region.bbox} (confidence: {region.confidence:.2%})")


# ============================================================================
# EXAMPLE 2: Multi-Language OCR
# ============================================================================

"""
Extract text in multiple languages
"""

async def multilingual_example():
    ocr_service = OCRService()
    
    # Extract text in multiple languages
    result = await ocr_service.extract_text_from_file(
        "/path/to/multilingual_document.pdf",
        languages=["en", "es", "fr", "ch"],  # English, Spanish, French, Chinese
        preprocess=True,
    )
    
    print(f"Detected Languages: {result.languages_detected}")
    print(f"Total Text: {len(result.text)} characters")


# ============================================================================
# EXAMPLE 3: Table Extraction
# ============================================================================

"""
Extract tables from document
"""

async def table_extraction_example():
    ocr_service = OCRService()
    
    result = await ocr_service.extract_text_from_file(
        "/path/to/spreadsheet.pdf",
        provider="doctr",  # DocTR is better for tables
        extract_tables=True,
    )
    
    # Access extracted tables
    for i, table in enumerate(result.tables):
        print(f"\nTable {i+1}:")
        print(f"  Rows: {len(table.rows)}")
        print(f"  Columns: {len(table.rows[0]) if table.rows else 0}")
        print(f"  Confidence: {table.confidence:.2%}")
        
        # Print table data
        for row in table.rows[:3]:  # First 3 rows
            print(f"    {row}")


# ============================================================================
# EXAMPLE 4: Image Preprocessing
# ============================================================================

"""
Use image preprocessing to improve OCR accuracy
"""

import cv2
import numpy as np
from app.services.ocr.preprocessing import ImagePreprocessor

def preprocessing_example():
    # Load image
    image = cv2.imread("/path/to/scanned_document.png")
    
    # Apply full preprocessing pipeline
    preprocessed = ImagePreprocessor.preprocess_pipeline(
        image,
        deskew=True,           # Straighten tilted text
        denoise=True,          # Remove noise
        contrast_enhance=True, # Enhance text-background contrast
        threshold=True,        # Convert to binary
        resize_scale=2.0,      # Upscale 2x for better OCR
    )
    
    # Save preprocessed image
    cv2.imwrite("/path/to/preprocessed.png", preprocessed)
    
    # Individual preprocessing operations
    gray = ImagePreprocessor.grayscale(image)
    deskewed = ImagePreprocessor.deskew(gray)
    denoised = ImagePreprocessor.denoise(deskewed, method="bilateralFilter")
    enhanced = ImagePreprocessor.enhance_contrast(denoised, method="clahe")


# ============================================================================
# EXAMPLE 5: Async Processing from File Bytes
# ============================================================================

"""
Process image from bytes (e.g., from uploaded file)
"""

async def bytes_extraction_example():
    ocr_service = OCRService()
    
    # Read file bytes
    with open("/path/to/image.jpg", "rb") as f:
        image_bytes = f.read()
    
    # Extract from bytes
    result = await ocr_service.extract_text_from_bytes(
        image_bytes,
        file_name="image.jpg",
        provider="paddle",
        languages=["en"],
    )
    
    print(f"Extracted: {result.text[:100]}...")


# ============================================================================
# EXAMPLE 6: API Usage with curl
# ============================================================================

"""
Using the OCR API via HTTP
"""

# Start API server first:
# uvicorn app.main:app --reload

# Example 1: Synchronous extraction
# curl -X POST http://localhost:8000/api/v1/ocr/extract \
#   -F "file=@document.pdf" \
#   -F "provider=paddle" \
#   -F "languages=en" \
#   -H "Authorization: Bearer YOUR_TOKEN"

# Example 2: Asynchronous extraction
# curl -X POST http://localhost:8000/api/v1/ocr/extract-async \
#   -F "file=@document.pdf" \
#   -F "provider=paddle" \
#   -H "Authorization: Bearer YOUR_TOKEN"
# 
# Response:
# {"task_id": "job-uuid", "status": "pending", "progress": 0}

# Example 3: Check job status
# curl http://localhost:8000/api/v1/ocr/job/job-uuid \
#   -H "Authorization: Bearer YOUR_TOKEN"

# Example 4: List user's jobs
# curl http://localhost:8000/api/v1/ocr/jobs \
#   -H "Authorization: Bearer YOUR_TOKEN"

# Example 5: Create batch job
# curl -X POST http://localhost:8000/api/v1/ocr/batch \
#   -F "files=@file1.pdf" -F "files=@file2.pdf" \
#   -F "task_name=Invoice Batch" \
#   -F "provider=paddle" \
#   -H "Authorization: Bearer YOUR_TOKEN"


# ============================================================================
# EXAMPLE 7: Python API Client
# ============================================================================

"""
Using OCR via Python HTTP client
"""

import httpx
import asyncio
import json

async def api_client_example():
    async with httpx.AsyncClient() as client:
        # Upload and extract
        with open("document.pdf", "rb") as f:
            response = await client.post(
                "http://localhost:8000/api/v1/ocr/extract",
                files={"file": f},
                data={
                    "provider": "paddle",
                    "languages": "en",
                    "extract_tables": True,
                },
                headers={"Authorization": "Bearer YOUR_TOKEN"},
            )
        
        result = response.json()
        print(f"Extracted Text: {result['text'][:200]}...")
        print(f"Confidence: {result['overall_confidence']:.2%}")
        print(f"Tables: {len(result['tables'])}")


# ============================================================================
# EXAMPLE 8: Direct Provider Usage
# ============================================================================

"""
Use OCR providers directly (if engines are installed)
"""

async def direct_provider_example():
    # Note: Requires paddleocr to be installed
    from app.services.ocr.paddle_provider import PaddleOCRProvider
    import cv2
    
    # Initialize provider
    provider = PaddleOCRProvider(
        languages=["en", "ch"],
        use_gpu=False,
    )
    
    # Load image
    image = cv2.imread("/path/to/image.png")
    
    # Extract text
    result = await provider.extract_text(
        image,
        languages=["en", "ch"],
        extract_tables=True,
    )
    
    print(result.to_dict())


# ============================================================================
# EXAMPLE 9: Provider Factory Usage
# ============================================================================

"""
Use provider factory to create different providers
"""

from app.services.ocr.factory import OCRFactory

def factory_example():
    # Create PaddleOCR provider
    paddle_provider = OCRFactory.create(
        "paddle",
        languages=["en"],
        use_gpu=False,
    )
    
    # Create Tesseract provider
    tesseract_provider = OCRFactory.create(
        "tesseract",
        languages=["en"],
    )
    
    # Create DocTR provider
    doctr_provider = OCRFactory.create(
        "doctr",
        languages=["en"],
        use_gpu=False,
    )
    
    # Get supported providers
    providers = OCRFactory.get_supported_providers()
    print(f"Available providers: {providers}")


# ============================================================================
# EXAMPLE 10: Batch Processing
# ============================================================================

"""
Process multiple files in batch
"""

async def batch_processing_example():
    ocr_service = OCRService()
    
    files = [
        "/path/to/document1.pdf",
        "/path/to/document2.pdf",
        "/path/to/document3.pdf",
    ]
    
    results = []
    for file_path in files:
        result = await ocr_service.extract_text_from_file(
            file_path,
            provider="paddle",
            preprocess=True,
        )
        results.append({
            "file": file_path,
            "text_length": len(result.text),
            "confidence": result.overall_confidence,
            "tables": len(result.tables),
        })
    
    for r in results:
        print(f"{r['file']}: {r['text_length']} chars, "
              f"confidence {r['confidence']:.2%}, "
              f"{r['tables']} tables")


# ============================================================================
# EXAMPLE 11: Error Handling
# ============================================================================

"""
Handle OCR errors gracefully
"""

async def error_handling_example():
    ocr_service = OCRService()
    
    try:
        result = await ocr_service.extract_text_from_file(
            "/path/to/invalid.gif",  # Unsupported format
            provider="paddle",
        )
    except ValueError as e:
        print(f"Validation Error: {e}")
        # Handle unsupported format
    except RuntimeError as e:
        print(f"Processing Error: {e}")
        # Handle OCR processing failure


# ============================================================================
# EXAMPLE 12: Data Analysis of OCR Results
# ============================================================================

"""
Analyze OCR results
"""

async def analysis_example():
    ocr_service = OCRService()
    
    result = await ocr_service.extract_text_from_file(
        "/path/to/document.pdf",
    )
    
    # Calculate statistics
    total_regions = len(result.regions)
    high_confidence = sum(1 for r in result.regions if r.confidence > 0.9)
    medium_confidence = sum(1 for r in result.regions if 0.7 <= r.confidence <= 0.9)
    low_confidence = sum(1 for r in result.regions if r.confidence < 0.7)
    
    print(f"OCR Statistics:")
    print(f"  Total regions: {total_regions}")
    print(f"  High confidence (>90%): {high_confidence}")
    print(f"  Medium confidence (70-90%): {medium_confidence}")
    print(f"  Low confidence (<70%): {low_confidence}")
    print(f"  Average confidence: {result.overall_confidence:.2%}")
    print(f"  Processing time: {result.processing_time_ms:.0f}ms")
    print(f"  Text length: {len(result.text)} characters")
    print(f"  Tables found: {len(result.tables)}")


# ============================================================================
# EXAMPLE 13: Using with FastAPI Dependency
# ============================================================================

"""
Use OCR service as FastAPI dependency
"""

from fastapi import FastAPI, Depends, UploadFile, File
from app.services.ocr_service import OCRService

app = FastAPI()

def get_ocr_service() -> OCRService:
    """Dependency for OCR service"""
    return OCRService(
        default_provider="paddle",
        languages=["en"],
    )

@app.post("/extract")
async def extract_text(
    file: UploadFile = File(...),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """Extract text from uploaded file"""
    content = await file.read()
    result = await ocr_service.extract_text_from_bytes(
        content,
        file.filename,
    )
    return result.to_dict()


# ============================================================================
# EXAMPLE 14: Celery Task Integration
# ============================================================================

"""
Use Celery for background OCR processing
"""

from app.tasks_ocr import process_ocr_file

def celery_task_example():
    # Queue a file for processing
    task = process_ocr_file.delay(
        job_id="job-123",
        file_path="/path/to/document.pdf",
        provider="paddle",
        languages=["en"],
    )
    
    # Get task result
    print(f"Task ID: {task.id}")
    print(f"Task Status: {task.status}")
    
    # Wait for completion (with timeout)
    try:
        result = task.get(timeout=300)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Task failed: {e}")


# ============================================================================
# EXAMPLE 15: Running All Examples
# ============================================================================

if __name__ == "__main__":
    print("OCR Service Examples")
    print("=" * 80)
    print()
    print("These examples demonstrate various ways to use the OCR service.")
    print()
    print("Before running, make sure to:")
    print("  1. Start the API server: uvicorn app.main:app")
    print("  2. Start Celery worker: celery -A app.core.celery_app worker")
    print("  3. Install OCR engines: pip install paddleocr pytesseract python-doctr")
    print()
    print("Choose an example to run:")
    print("  - Example 1: Basic text extraction")
    print("  - Example 2: Multi-language OCR")
    print("  - Example 3: Table extraction")
    print("  - Example 4: Image preprocessing")
    print("  - Example 5: Bytes extraction")
    print("  - Example 6: API with curl")
    print("  - Example 7: Python API client")
    print("  - Example 8: Direct provider usage")
    print("  - Example 9: Provider factory")
    print("  - Example 10: Batch processing")
    print("  - Example 11: Error handling")
    print("  - Example 12: Data analysis")
    print("  - Example 13: FastAPI dependency")
    print("  - Example 14: Celery tasks")
    print()
    print("For more information, see:")
    print("  - OCR_SERVICE_README.md (comprehensive documentation)")
    print("  - OCR_QUICK_START.txt (quick reference)")
    print("  - OCR_INTEGRATION_GUIDE.md (integration patterns)")
