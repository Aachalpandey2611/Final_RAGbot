"""OCR Repository"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models.ocr import OCRJob, OCRBatch, OCRCache
from app.repositories.base import BaseRepository


class OCRJobRepository(BaseRepository[OCRJob]):
    """Repository for OCR jobs"""
    
    def __init__(self, db: Session):
        super().__init__(OCRJob, db)
    
    def get_user_jobs(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> List[OCRJob]:
        """Get user's OCR jobs"""
        query = self.db.query(self.model).filter(self.model.user_id == user_id)
        
        if status:
            query = query.filter(self.model.status == status)
        
        return query.order_by(desc(self.model.created_at)).offset(skip).limit(limit).all()
    
    def get_by_status(self, status: str, limit: int = 100) -> List[OCRJob]:
        """Get jobs by status"""
        return (
            self.db.query(self.model)
            .filter(self.model.status == status)
            .order_by(self.model.created_at)
            .limit(limit)
            .all()
        )
    
    def update_job_result(
        self,
        job_id: str,
        extracted_text: str,
        text_regions: dict,
        tables: list,
        overall_confidence: float,
        processing_time_ms: float,
        image_width: int,
        image_height: int,
    ) -> OCRJob:
        """Update job with results"""
        job = self.get(job_id)
        if job:
            job.extracted_text = extracted_text
            job.text_regions = text_regions
            job.tables = tables
            job.overall_confidence = overall_confidence
            job.processing_time_ms = processing_time_ms
            job.image_width = image_width
            job.image_height = image_height
            job.status = "completed"
            self.db.commit()
        return job
    
    def update_job_status(self, job_id: str, status: str, error: Optional[str] = None) -> OCRJob:
        """Update job status"""
        job = self.get(job_id)
        if job:
            job.status = status
            if error:
                job.error_message = error
            self.db.commit()
        return job
    
    def delete_old_jobs(self, days: int = 30) -> int:
        """Delete jobs older than specified days"""
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        count = self.db.query(self.model).filter(self.model.created_at < cutoff_date).delete()
        self.db.commit()
        return count


class OCRBatchRepository(BaseRepository[OCRBatch]):
    """Repository for OCR batches"""
    
    def __init__(self, db: Session):
        super().__init__(OCRBatch, db)
    
    def get_user_batches(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OCRBatch]:
        """Get user's OCR batches"""
        return (
            self.db.query(self.model)
            .filter(self.model.user_id == user_id)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_status(self, status: str, limit: int = 50) -> List[OCRBatch]:
        """Get batches by status"""
        return (
            self.db.query(self.model)
            .filter(self.model.status == status)
            .order_by(self.model.created_at)
            .limit(limit)
            .all()
        )
    
    def update_batch_progress(
        self,
        batch_id: str,
        total_files: Optional[int] = None,
        processed_files: Optional[int] = None,
        failed_files: Optional[int] = None,
        status: Optional[str] = None,
    ) -> OCRBatch:
        """Update batch progress"""
        batch = self.get(batch_id)
        if batch:
            if total_files is not None:
                batch.total_files = total_files
            if processed_files is not None:
                batch.processed_files = processed_files
            if failed_files is not None:
                batch.failed_files = failed_files
            if status is not None:
                batch.status = status
            self.db.commit()
        return batch


class OCRCacheRepository(BaseRepository[OCRCache]):
    """Repository for OCR cache"""
    
    def __init__(self, db: Session):
        super().__init__(OCRCache, db)
    
    def get_by_file_hash(self, file_hash: str) -> Optional[OCRCache]:
        """Get cached result by file hash"""
        return self.db.query(self.model).filter(self.model.file_hash == file_hash).first()
    
    def cache_result(
        self,
        file_hash: str,
        file_name: str,
        extracted_text: str,
        text_regions: dict,
        tables: list,
        overall_confidence: float,
        provider: str,
        languages: list,
        image_width: int,
        image_height: int,
        processing_time_ms: float,
    ) -> OCRCache:
        """Cache OCR result"""
        cache_entry = self.get_by_file_hash(file_hash)
        
        if cache_entry:
            # Update existing
            cache_entry.extracted_text = extracted_text
            cache_entry.text_regions = text_regions
            cache_entry.tables = tables
            cache_entry.overall_confidence = overall_confidence
        else:
            # Create new
            cache_entry = self.create(
                file_hash=file_hash,
                file_name=file_name,
                extracted_text=extracted_text,
                text_regions=text_regions,
                tables=tables,
                overall_confidence=overall_confidence,
                provider=provider,
                languages=languages,
                image_width=image_width,
                image_height=image_height,
                processing_time_ms=processing_time_ms,
            )
        
        return cache_entry
    
    def delete_old_cache(self, days: int = 90) -> int:
        """Delete cache older than specified days"""
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        count = self.db.query(self.model).filter(self.model.created_at < cutoff_date).delete()
        self.db.commit()
        return count
