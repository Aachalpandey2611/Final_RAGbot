# OCR Processing Service Documentation

## Overview

The OCR Processing Service is a production-grade microservice for extracting text, tables, and metadata from images and PDFs. It supports multiple OCR engines and provides features for image preprocessing, multi-language recognition, and result caching.

## Features

### Supported Formats

- **Images**: PNG, JPG, JPEG, TIFF
- **Documents**: Scanned PDFs

### OCR Engines

1. **PaddleOCR** - Fast, GPU-accelerated, multilingual support
2. **Tesseract** - Traditional OCR engine, excellent for printed text
3. **DocTR** - Document-focused OCR with table detection

### Core Features

- **Multi-Language OCR**: Support for 15+ languages including English, Chinese, Japanese, Korean, Arabic, and more
- **Table Extraction**: Automatic detection and extraction of table structures
- **Image Preprocessing**: Automatic deskewing, denoising, contrast enhancement
- **Confidence Scoring**: Confidence metrics for extracted text and tables
- **Result Caching**: Smart caching using file hashing to avoid redundant processing
- **Batch Processing**: Asynchronous batch job support for processing multiple files
- **Job Tracking**: Real-time job status monitoring and progress tracking

## Architecture

### Components

```
OCRService (Main Service)
├── OCRProviders (Base + Implementations)
│   ├── PaddleOCRProvider
│   ├── TesseractOCRProvider
│   └── DocTRProvider
├── ImagePreprocessor (Image Processing Pipeline)
├── Repositories (Database Layer)
│   ├── OCRJobRepository
│   ├── OCRBatchRepository
│   └── OCRCacheRepository
├── Celery Tasks (Async Processing)
└── API Controllers (REST Endpoints)
```

### Data Models

**OCRJob**: Individual file processing job

- Tracks file information, processing status, and results
- Indexes: user_id, status, file_format, created_at

**OCRBatch**: Batch processing job for multiple files

- Tracks batch progress and aggregate statistics
- Supports status monitoring for large-scale processing

**OCRCache**: Result caching layer

- Stores processed results using file hash for quick retrieval
- Automatic cleanup of old entries

## API Endpoints

### 1. Synchronous Text Extraction

```
POST /api/v1/ocr/extract
```

Extract text from a single uploaded file (blocks until complete).

**Request Parameters:**

```json
{
  "provider": "paddle",
  "languages": ["en"],
  "extract_tables": true,
  "preprocess": true,
  "confidence_threshold": 0.3
}
```

**Response:**

```json
{
  "text": "Extracted text content...",
  "regions": [
    {
      "text": "Line of text",
      "bbox": [10, 20, 100, 35],
      "confidence": 0.95,
      "language": "en"
    }
  ],
  "tables": [
    {
      "rows": [
        ["Header1", "Header2"],
        ["Cell1", "Cell2"]
      ],
      "confidence": 0.9,
      "bbox": [0, 100, 500, 300]
    }
  ],
  "languages_detected": ["en"],
  "overall_confidence": 0.93,
  "image_width": 800,
  "image_height": 600,
  "processing_time_ms": 1234.5,
  "provider": "PaddleOCR"
}
```

### 2. Asynchronous Text Extraction

```
POST /api/v1/ocr/extract-async
```

Queue a file for processing and return immediately with job ID.

**Response:**

```json
{
  "task_id": "job-uuid",
  "status": "pending",
  "progress": 0
}
```

### 3. Get Job Status

```
GET /api/v1/ocr/job/{job_id}
```

Get the current status and results of a processing job.

**Response:**

```json
{
  "task_id": "job-uuid",
  "status": "completed",
  "progress": 100,
  "result": { ... },
  "error": null
}
```

### 4. List User Jobs

```
GET /api/v1/ocr/jobs?skip=0&limit=100&status=completed
```

List all OCR jobs for the current user with optional filtering.

### 5. Batch Processing

```
POST /api/v1/ocr/batch
```

Submit multiple files for batch processing.

**Request:**

```json
{
  "task_name": "Invoice Processing Batch",
  "provider": "paddle",
  "languages": ["en"],
  "extract_tables": true,
  "preprocess": true
}
```

**Response:**

```json
{
  "batch_id": "batch-uuid",
  "status": "pending",
  "total_files": 10,
  "processed_files": 0,
  "failed_files": 0,
  "progress": 0
}
```

### 6. Get Batch Status

```
GET /api/v1/ocr/batch/{batch_id}
```

Monitor batch processing progress.

### 7. Supported Providers

```
GET /api/v1/ocr/providers
```

Get list of available OCR providers.

**Response:**

```json
{
  "providers": ["paddle", "tesseract", "doctr"]
}
```

### 8. Supported Languages

```
GET /api/v1/ocr/languages
```

Get list of supported languages for OCR.

**Response:**

```json
{
  "languages": [
    { "code": "en", "name": "ENGLISH" },
    { "code": "es", "name": "SPANISH" },
    { "code": "fr", "name": "FRENCH" },
    { "code": "ch", "name": "CHINESE_SIMPLIFIED" },
    { "code": "ja", "name": "JAPANESE" },
    { "code": "ko", "name": "KOREAN" },
    { "code": "ru", "name": "RUSSIAN" },
    { "code": "ar", "name": "ARABIC" }
  ]
}
```

## Image Preprocessing

The ImagePreprocessor module provides advanced image preprocessing to improve OCR accuracy:

### Preprocessing Pipeline

```python
from app.services.ocr.preprocessing import ImagePreprocessor

preprocessed_image = ImagePreprocessor.preprocess_pipeline(
    image,
    deskew=True,           # Straighten tilted text
    denoise=True,          # Remove noise
    contrast_enhance=True, # Enhance text-background contrast
    threshold=False,       # Apply binary thresholding
    resize_scale=2.0,      # Upscale image 2x
)
```

### Available Preprocessing Techniques

- **Deskewing**: Automatically straighten tilted text using contour analysis
- **Denoising**: Multiple methods (bilateral filter, morphological, Gaussian)
- **Thresholding**: Otsu, adaptive, and binary methods
- **Contrast Enhancement**: CLAHE and histogram equalization
- **Resizing**: Upscale images for better OCR accuracy
- **Border Removal**: Remove borders that interfere with OCR

## Usage Examples

### Python Service Usage

```python
from app.services.ocr_service import OCRService
import cv2

# Initialize service
ocr_service = OCRService(
    default_provider="paddle",
    languages=["en", "ch"],
    use_gpu=True,
)

# Extract text from file
result = await ocr_service.extract_text_from_file(
    "/path/to/image.png",
    provider="paddle",
    languages=["en"],
    preprocess=True,
)

print(f"Extracted text: {result.text}")
print(f"Confidence: {result.overall_confidence}")
print(f"Processing time: {result.processing_time_ms}ms")

# Extract from bytes
image_bytes = open("image.pdf", "rb").read()
result = await ocr_service.extract_text_from_bytes(
    image_bytes,
    "image.pdf",
    provider="doctr",  # Use DocTR for PDFs
)

# Extract tables only
tables = await ocr_service.extract_tables(image_array)
```

### API Usage Example

**cURL:**

```bash
# Synchronous extraction
curl -X POST http://localhost:8000/api/v1/ocr/extract \
  -F "file=@document.pdf" \
  -F "provider=paddle" \
  -F "languages=en" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Asynchronous extraction
curl -X POST http://localhost:8000/api/v1/ocr/extract-async \
  -F "file=@document.pdf" \
  -F "provider=doctr" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check job status
curl http://localhost:8000/api/v1/ocr/job/job-uuid \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Python:**

```python
import httpx
import asyncio

async def extract_text():
    async with httpx.AsyncClient() as client:
        with open("document.pdf", "rb") as f:
            files = {"file": f}
            data = {
                "provider": "paddle",
                "languages": "en",
                "extract_tables": True,
            }
            response = await client.post(
                "http://localhost:8000/api/v1/ocr/extract",
                files=files,
                data=data,
                headers={"Authorization": "Bearer TOKEN"},
            )
            return response.json()

result = asyncio.run(extract_text())
print(result)
```

## Provider Comparison

| Feature         | PaddleOCR       | Tesseract     | DocTR         |
| --------------- | --------------- | ------------- | ------------- |
| Speed           | ⭐⭐⭐⭐ Fast   | ⭐⭐⭐ Medium | ⭐⭐⭐ Medium |
| Accuracy        | ⭐⭐⭐⭐ High   | ⭐⭐⭐ Good   | ⭐⭐⭐⭐ High |
| Languages       | ⭐⭐⭐⭐ 15+    | ⭐⭐⭐ 100+   | ⭐⭐⭐ 15+    |
| GPU Support     | ✓               | ✗             | ✓             |
| Table Detection | △ Limited       | ✗             | ✓ Good        |
| Multilingual    | ✓ Excellent     | ✓ Good        | ✓ Good        |
| Memory Usage    | ⭐⭐⭐ Moderate | ⭐⭐⭐⭐ Low  | ⭐⭐ High     |

## Performance Optimization

### Caching Strategy

- File-based caching using SHA256 hashing
- Automatic cache cleanup (default: 90 days)
- Significant speedup for duplicate files

### GPU Acceleration

```python
# Enable GPU for PaddleOCR and DocTR
ocr_service = OCRService(
    default_provider="paddle",
    use_gpu=True,  # Enable GPU
)
```

### Batch Processing

- Queue multiple files for asynchronous processing
- Automatic progress tracking
- Configurable concurrency via Celery workers

### Preprocessing Optimization

```python
# Fast path: minimal preprocessing
ImagePreprocessor.preprocess_pipeline(
    image,
    deskew=False,
    denoise=False,
    contrast_enhance=False,
)

# Slow path: maximum accuracy
ImagePreprocessor.preprocess_pipeline(
    image,
    deskew=True,
    denoise=True,
    contrast_enhance=True,
    resize_scale=2.0,
)
```

## Celery Background Tasks

### Available Tasks

**process_ocr_file**: Process single file with OCR

```python
from app.tasks_ocr import process_ocr_file

process_ocr_file.delay(
    job_id="job-uuid",
    file_path="/path/to/file.png",
    provider="paddle",
    languages=["en"],
    extract_tables=True,
    preprocess=True,
)
```

**process_ocr_batch**: Process multiple files

```python
from app.tasks_ocr import process_ocr_batch

process_ocr_batch.delay(
    batch_id="batch-uuid",
    file_paths=["/path1.png", "/path2.pdf"],
    provider="doctr",
    languages=["en", "es"],
)
```

**cleanup_old_ocr_jobs**: Cleanup old job records

```python
from app.tasks_ocr import cleanup_old_ocr_jobs

cleanup_old_ocr_jobs.delay(days=30)
```

**cleanup_ocr_cache**: Cleanup old cache entries

```python
from app.tasks_ocr import cleanup_ocr_cache

cleanup_ocr_cache.delay(days=90)
```

### Monitoring

Check Flower UI for task monitoring:

```
http://localhost:5555
```

## Database Schema

### ocr_jobs

- Tracks individual file processing
- Stores extracted text, regions, tables
- Includes confidence metrics and processing time

### ocr_batches

- Tracks batch job progress
- Aggregates statistics (total, processed, failed)
- Links to individual jobs

### ocr_cache

- Stores results for quick retrieval
- Uses SHA256 file hash for identification
- Automatic expiration

## Configuration

### Environment Variables

```
OCR_DEFAULT_PROVIDER=paddle
OCR_DEFAULT_LANGUAGES=en,es,fr
OCR_USE_GPU=false
OCR_CACHE_RETENTION_DAYS=90
OCR_JOB_RETENTION_DAYS=30
```

### Settings in config.py

```python
class Settings(BaseSettings):
    OCR_DEFAULT_PROVIDER: str = "paddle"
    OCR_DEFAULT_LANGUAGES: List[str] = ["en"]
    OCR_USE_GPU: bool = False
    OCR_CACHE_RETENTION_DAYS: int = 90
    OCR_JOB_RETENTION_DAYS: int = 30
```

## Error Handling

### Common Errors

**Unsupported Format**

```
Status: 400
Detail: "Unsupported format: gif. Supported: {'png', 'jpg', 'jpeg', 'tiff', 'tif', 'pdf'}"
```

**Invalid Image**

```
Status: 500
Detail: "Failed to load image: /path/to/file"
```

**Provider Initialization Failure**

```
Status: 500
Detail: "Failed to initialize paddle: [error message]"
```

## Best Practices

1. **Preprocessing**: Use preprocessing for scanned documents, disable for high-quality images
2. **Provider Selection**:
   - Use PaddleOCR for multilingual or speed-critical applications
   - Use DocTR for document-heavy workloads with tables
   - Use Tesseract as fallback for compatibility
3. **Batch Processing**: Use batch API for multiple files to maximize efficiency
4. **Caching**: Monitor cache size and run cleanup tasks regularly
5. **Language Selection**: Use specific languages when possible (faster than auto-detect)
6. **Confidence Threshold**: Filter results by confidence threshold in API requests

## Troubleshooting

### High Memory Usage

- Disable preprocessing: `preprocess=False`
- Process files in batches with limited concurrency
- Monitor cache size and run cleanup

### Low Accuracy

- Enable preprocessing: `preprocess=True`
- Try different OCR provider (PaddleOCR → DocTR → Tesseract)
- Increase image resolution before processing
- Use specific language codes instead of auto-detect

### Slow Processing

- Enable GPU acceleration: `use_gpu=True`
- Use PaddleOCR instead of DocTR
- Disable table extraction if not needed
- Use async API for multiple files

### Out of Memory

- Process files in smaller batches
- Clear cache: `cleanup_ocr_cache.delay()`
- Reduce image resolution
- Use Tesseract (lower memory footprint)

## Migration & Integration

### Adding OCR Models

Add OCRJob and OCRBatch models to migrations:

```bash
alembic revision --autogenerate -m "Add OCR models"
alembic upgrade head
```

### Existing Data Integration

The OCR service can be integrated with existing document management:

```python
from app.models.ocr import OCRJob
from app.models.document import Document

# Link OCR result to document
document = Document()
ocr_job = OCRJob(
    user_id=document.user_id,
    file_path=document.file_path,
)
```

## Performance Metrics

Typical performance metrics (on CPU, 2-core):

| Provider   | File Type     | File Size | Time   | Confidence |
| ---------- | ------------- | --------- | ------ | ---------- |
| PaddleOCR  | PNG (800x600) | 500KB     | 2-3s   | 0.92       |
| Tesseract  | PNG (800x600) | 500KB     | 1-2s   | 0.85       |
| DocTR      | PDF (1 page)  | 1MB       | 3-4s   | 0.94       |
| With Cache | Any           | Any       | <100ms | Same       |

GPU acceleration provides 3-5x speedup for PaddleOCR and DocTR.

## License & Dependencies

- PaddleOCR: Apache 2.0
- Tesseract: Apache 2.0
- DocTR: MIT
- Supporting libraries: FastAPI, SQLAlchemy, Celery

## Support & Contributing

For issues, feature requests, or improvements, please refer to the project's contribution guidelines.
