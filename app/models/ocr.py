"""OCR Models"""
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, ForeignKey, Table, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base


class OCRJob(Base):
    """OCR processing job"""
    __tablename__ = "ocr_jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    # Input
    file_name = Column(String(256), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer)  # Bytes
    file_format = Column(String(10))  # png, jpg, pdf, etc.
    
    # Configuration
    provider = Column(String(50), default="paddle")
    languages = Column(JSON)  # List of language codes
    extract_tables = Column(Integer, default=1)
    preprocess = Column(Integer, default=1)
    
    # Results
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    extracted_text = Column(Text)
    text_regions = Column(JSON)  # List of TextRegion objects
    tables = Column(JSON)  # List of Table objects
    overall_confidence = Column(Float)
    
    # Metadata
    image_width = Column(Integer)
    image_height = Column(Integer)
    processing_time_ms = Column(Float)
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Batch relationship (optional)
    batch_id = Column(String, ForeignKey("ocr_batches.id"), nullable=True)
    batch = relationship("OCRBatch", back_populates="jobs")
    
    # Indexes
    __table_args__ = (
        Index("idx_user_created", "user_id", "created_at"),
        Index("idx_status", "status"),
        Index("idx_file_format", "file_format"),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "file_name": self.file_name,
            "file_format": self.file_format,
            "provider": self.provider,
            "status": self.status,
            "extracted_text": self.extracted_text,
            "text_regions": self.text_regions,
            "tables": self.tables,
            "overall_confidence": self.overall_confidence,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class OCRBatch(Base):
    """Batch OCR processing job"""
    __tablename__ = "ocr_batches"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    # Batch info
    batch_name = Column(String(256), nullable=False)
    
    # Configuration
    provider = Column(String(50), default="paddle")
    languages = Column(JSON)
    extract_tables = Column(Integer, default=1)
    preprocess = Column(Integer, default=1)
    
    # Progress
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships: jobs associated with this batch
    jobs = relationship("OCRJob", back_populates="batch", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_user_batch_created", "user_id", "created_at"),
        Index("idx_batch_status", "status"),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "batch_name": self.batch_name,
            "status": self.status,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "failed_files": self.failed_files,
            "progress": int((self.processed_files / self.total_files * 100) if self.total_files > 0 else 0),
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class OCRCache(Base):
    """Cache for OCR results"""
    __tablename__ = "ocr_cache"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # File hash for identifying duplicate
    file_hash = Column(String(256), unique=True, nullable=False)
    file_name = Column(String(256))
    
    # Cached result
    extracted_text = Column(Text)
    text_regions = Column(JSON)
    tables = Column(JSON)
    overall_confidence = Column(Float)
    
    # Metadata
    provider = Column(String(50))
    languages = Column(JSON)
    image_width = Column(Integer)
    image_height = Column(Integer)
    processing_time_ms = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_file_hash", "file_hash"),
        Index("idx_created", "created_at"),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "file_hash": self.file_hash,
            "extracted_text": self.extracted_text,
            "overall_confidence": self.overall_confidence,
            "provider": self.provider,
        }
