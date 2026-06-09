"""OCR Celery Tasks"""
import asyncio
import hashlib
from pathlib import Path
from typing import Optional, List

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.logging import logger
from app.services.ocr_service import OCRService
from app.repositories.ocr import OCRJobRepository, OCRBatchRepository, OCRCacheRepository


ocr_service = OCRService(default_provider="paddle")


@celery_app.task(bind=True, name="ocr.process_single_file")
def process_ocr_file(
    self,
    job_id: str,
    file_path: str,
    provider: str = "paddle",
    languages: Optional[List[str]] = None,
    extract_tables: bool = True,
    preprocess: bool = True,
):
    """Process single file with OCR"""
    db = SessionLocal()
    try:
        job_repo = OCRJobRepository(db)
        cache_repo = OCRCacheRepository(db)
        
        # Update job status
        job_repo.update_job_status(job_id, "processing")
        logger.info(f"Processing OCR job: {job_id}")
        
        # Calculate file hash for caching
        file_hash = calculate_file_hash(file_path)
        
        # Check cache
        cached = cache_repo.get_by_file_hash(file_hash)
        if cached:
            logger.info(f"Using cached result for job: {job_id}")
            job_repo.update_job_result(
                job_id,
                extracted_text=cached.extracted_text,
                text_regions=cached.text_regions,
                tables=cached.tables,
                overall_confidence=cached.overall_confidence,
                processing_time_ms=cached.processing_time_ms,
                image_width=cached.image_width,
                image_height=cached.image_height,
            )
            return {"status": "completed", "cached": True}
        
        # Process file
        try:
            # Run async function
            result = asyncio.run(
                ocr_service.extract_text_from_file(
                    file_path,
                    provider=provider,
                    languages=languages,
                    preprocess=preprocess,
                )
            )
            
            # Save result
            text_regions = [r.to_dict() for r in result.regions]
            tables = [t.to_dict() for t in result.tables]
            
            job_repo.update_job_result(
                job_id,
                extracted_text=result.text,
                text_regions=text_regions,
                tables=tables,
                overall_confidence=result.overall_confidence,
                processing_time_ms=result.processing_time_ms,
                image_width=result.image_width,
                image_height=result.image_height,
            )
            
            # Cache result
            cache_repo.cache_result(
                file_hash=file_hash,
                file_name=Path(file_path).name,
                extracted_text=result.text,
                text_regions=text_regions,
                tables=tables,
                overall_confidence=result.overall_confidence,
                provider=provider,
                languages=languages,
                image_width=result.image_width,
                image_height=result.image_height,
                processing_time_ms=result.processing_time_ms,
            )
            
            logger.info(f"OCR job completed: {job_id}")
            return {"status": "completed", "cached": False}
        
        except Exception as e:
            logger.error(f"OCR processing failed for job {job_id}: {str(e)}")
            job_repo.update_job_status(job_id, "failed", error=str(e))
            raise
    
    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        db.query(OCRJobRepository).filter(
            OCRJobRepository.id == job_id
        ).update({"status": "failed", "error_message": str(e)})
        db.commit()
        raise
    
    finally:
        db.close()


@celery_app.task(bind=True, name="ocr.process_batch")
def process_ocr_batch(
    self,
    batch_id: str,
    file_paths: List[str],
    provider: str = "paddle",
    languages: Optional[List[str]] = None,
    extract_tables: bool = True,
    preprocess: bool = True,
):
    """Process batch of files with OCR"""
    db = SessionLocal()
    try:
        batch_repo = OCRBatchRepository(db)
        job_repo = OCRJobRepository(db)
        cache_repo = OCRCacheRepository(db)
        
        # Initialize batch
        batch_repo.update_batch_progress(
            batch_id,
            total_files=len(file_paths),
            status="processing",
        )
        logger.info(f"Processing OCR batch: {batch_id} with {len(file_paths)} files")
        
        processed = 0
        failed = 0
        
        for file_path in file_paths:
            try:
                # Calculate file hash
                file_hash = calculate_file_hash(file_path)
                
                # Check cache
                cached = cache_repo.get_by_file_hash(file_hash)
                if not cached:
                    # Process file
                    result = asyncio.run(
                        ocr_service.extract_text_from_file(
                            file_path,
                            provider=provider,
                            languages=languages,
                            preprocess=preprocess,
                        )
                    )
                    
                    # Cache result
                    text_regions = [r.to_dict() for r in result.regions]
                    tables = [t.to_dict() for t in result.tables]
                    
                    cache_repo.cache_result(
                        file_hash=file_hash,
                        file_name=Path(file_path).name,
                        extracted_text=result.text,
                        text_regions=text_regions,
                        tables=tables,
                        overall_confidence=result.overall_confidence,
                        provider=provider,
                        languages=languages,
                        image_width=result.image_width,
                        image_height=result.image_height,
                        processing_time_ms=result.processing_time_ms,
                    )
                
                processed += 1
                
            except Exception as e:
                logger.error(f"Failed to process file {file_path}: {str(e)}")
                failed += 1
            
            # Update progress
            progress = int((processed + failed) / len(file_paths) * 100)
            batch_repo.update_batch_progress(
                batch_id,
                processed_files=processed,
                failed_files=failed,
            )
        
        # Mark batch complete
        batch_repo.update_batch_progress(
            batch_id,
            status="completed",
        )
        
        logger.info(f"OCR batch completed: {batch_id}")
        return {
            "status": "completed",
            "processed": processed,
            "failed": failed,
        }
    
    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}")
        batch_repo.update_batch_progress(batch_id, status="failed")
        raise
    
    finally:
        db.close()


@celery_app.task(name="ocr.cleanup_old_jobs")
def cleanup_old_ocr_jobs(days: int = 30):
    """Cleanup old OCR jobs"""
    db = SessionLocal()
    try:
        job_repo = OCRJobRepository(db)
        deleted = job_repo.delete_old_jobs(days=days)
        logger.info(f"Deleted {deleted} old OCR jobs")
        return {"deleted": deleted}
    finally:
        db.close()


@celery_app.task(name="ocr.cleanup_cache")
def cleanup_ocr_cache(days: int = 90):
    """Cleanup old OCR cache"""
    db = SessionLocal()
    try:
        cache_repo = OCRCacheRepository(db)
        deleted = cache_repo.delete_old_cache(days=days)
        logger.info(f"Deleted {deleted} old OCR cache entries")
        return {"deleted": deleted}
    finally:
        db.close()


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file for caching"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
