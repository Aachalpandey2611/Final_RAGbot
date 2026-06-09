"""OCR Controller"""
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import io

from app.core.deps import get_db, get_current_user
from app.core.logging import logger
from app.schemas.ocr import (
    OCRRequestSchema,
    OCRResultSchema,
    OCRStatusSchema,
    OCRBatchRequestSchema,
    OCRBatchStatusSchema,
)
from app.repositories.ocr import OCRJobRepository, OCRBatchRepository, OCRCacheRepository
from app.services.ocr_service import OCRService
from app.tasks_ocr import process_ocr_file, process_ocr_batch, calculate_file_hash
from app.models.ocr import OCRJob, OCRBatch


router = APIRouter(prefix="/api/ocr", tags=["OCR"])

# Initialize OCR service
ocr_service = OCRService(default_provider="paddle")


@router.post("/extract", response_model=OCRResultSchema)
async def extract_text_from_upload(
    file: UploadFile = File(...),
    request: OCRRequestSchema = Depends(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Extract text from uploaded image or PDF
    
    Supported formats: PNG, JPG, JPEG, TIFF, PDF
    """
    try:
        # Validate file format
        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in ocr_service.SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {file_ext}. Supported: {ocr_service.SUPPORTED_FORMATS}",
            )
        
        # Read file
        content = await file.read()
        
        # Extract text
        result = await ocr_service.extract_text_from_bytes(
            content,
            file.filename,
            provider=request.provider.value,
            languages=[lang.value for lang in request.languages],
        )
        
        # Filter regions by confidence
        filtered_regions = [
            r for r in result.regions
            if r.confidence >= request.confidence_threshold
        ]
        
        logger.info(f"OCR extraction completed for {file.filename}")
        
        return OCRResultSchema(
            text=result.text,
            regions=[r.to_dict() for r in filtered_regions],
            tables=[t.to_dict() for t in result.tables],
            languages_detected=result.languages_detected,
            overall_confidence=result.overall_confidence,
            image_width=result.image_width,
            image_height=result.image_height,
            processing_time_ms=result.processing_time_ms,
            provider=result.provider,
        )
    
    except Exception as e:
        logger.error(f"OCR extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-async", response_model=OCRStatusSchema)
async def extract_text_async(
    file: UploadFile = File(...),
    request: OCRRequestSchema = Depends(),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Asynchronously extract text from uploaded image (returns job status)
    """
    try:
        # Validate format
        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in ocr_service.SUPPORTED_FORMATS:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {file_ext}")
        
        # Save uploaded file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Create job record
        job_repo = OCRJobRepository(db)
        job = job_repo.create(
            user_id=current_user["id"],
            file_name=file.filename,
            file_path=tmp_path,
            file_size=len(content),
            file_format=file_ext,
            provider=request.provider.value,
            languages=[lang.value for lang in request.languages],
            extract_tables=int(request.extract_tables),
            preprocess=int(request.preprocess),
            status="pending",
        )
        
        # Queue task
        process_ocr_file.delay(
            job.id,
            tmp_path,
            provider=request.provider.value,
            languages=[lang.value for lang in request.languages],
            extract_tables=request.extract_tables,
            preprocess=request.preprocess,
        )
        
        logger.info(f"OCR job created: {job.id}")
        
        return OCRStatusSchema(
            task_id=job.id,
            status="pending",
            progress=0,
        )
    
    except Exception as e:
        logger.error(f"Failed to create OCR job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}", response_model=OCRStatusSchema)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get OCR job status and results"""
    job_repo = OCRJobRepository(db)
    job = job_repo.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    response = OCRStatusSchema(
        task_id=job.id,
        status=job.status,
        error=job.error_message,
    )
    
    if job.status == "completed" and job.extracted_text:
        response.result = OCRResultSchema(
            text=job.extracted_text,
            regions=job.text_regions or [],
            tables=job.tables or [],
            languages_detected=job.languages or [],
            overall_confidence=job.overall_confidence or 0.0,
            image_width=job.image_width or 0,
            image_height=job.image_height or 0,
            processing_time_ms=job.processing_time_ms or 0.0,
            provider=job.provider,
        )
        response.progress = 100
    elif job.status == "processing":
        response.progress = 50
    
    return response


@router.get("/jobs", response_model=List[OCRStatusSchema])
def list_user_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List user's OCR jobs"""
    job_repo = OCRJobRepository(db)
    jobs = job_repo.get_user_jobs(
        current_user["id"],
        skip=skip,
        limit=limit,
        status=status,
    )
    
    return [
        OCRStatusSchema(
            task_id=job.id,
            status=job.status,
            progress=100 if job.status == "completed" else 50 if job.status == "processing" else 0,
            error=job.error_message,
        )
        for job in jobs
    ]


@router.post("/batch", response_model=OCRBatchStatusSchema)
async def create_batch_job(
    files: List[UploadFile] = File(...),
    request: OCRBatchRequestSchema = Depends(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create batch OCR processing job"""
    try:
        import tempfile
        import os
        
        # Save files and collect paths
        file_paths = []
        for file in files:
            file_ext = file.filename.split(".")[-1].lower()
            if file_ext not in ocr_service.SUPPORTED_FORMATS:
                raise HTTPException(status_code=400, detail=f"Unsupported format: {file_ext}")
            
            content = await file.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                tmp.write(content)
                file_paths.append(tmp.name)
        
        # Create batch record
        batch_repo = OCRBatchRepository(db)
        batch = batch_repo.create(
            user_id=current_user["id"],
            batch_name=request.task_name,
            provider=request.provider.value,
            languages=[lang.value for lang in request.languages],
            extract_tables=int(request.extract_tables),
            preprocess=int(request.preprocess),
            status="pending",
            total_files=len(file_paths),
        )
        
        # Queue batch task
        process_ocr_batch.delay(
            batch.id,
            file_paths,
            provider=request.provider.value,
            languages=[lang.value for lang in request.languages],
            extract_tables=request.extract_tables,
            preprocess=request.preprocess,
        )
        
        logger.info(f"OCR batch created: {batch.id}")
        
        return OCRBatchStatusSchema(
            batch_id=batch.id,
            status="pending",
            total_files=len(file_paths),
            processed_files=0,
            failed_files=0,
            progress=0,
        )
    
    except Exception as e:
        logger.error(f"Failed to create batch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/{batch_id}", response_model=OCRBatchStatusSchema)
def get_batch_status(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get batch processing status"""
    batch_repo = OCRBatchRepository(db)
    batch = batch_repo.get(batch_id)
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    if batch.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    progress = int(
        ((batch.processed_files + batch.failed_files) / batch.total_files * 100)
        if batch.total_files > 0
        else 0
    )
    
    return OCRBatchStatusSchema(
        batch_id=batch.id,
        status=batch.status,
        total_files=batch.total_files,
        processed_files=batch.processed_files,
        failed_files=batch.failed_files,
        progress=progress,
    )


@router.get("/providers", tags=["OCR"])
def get_supported_providers():
    """Get list of supported OCR providers"""
    from app.services.ocr.factory import OCRFactory
    return {
        "providers": OCRFactory.get_supported_providers(),
    }


@router.get("/languages", tags=["OCR"])
def get_supported_languages():
    """Get list of supported OCR languages"""
    from app.services.ocr.base import OCRLanguage
    return {
        "languages": [
            {"code": lang.value, "name": lang.name}
            for lang in OCRLanguage
        ]
    }
