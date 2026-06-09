"""
Database models for document classification storage
"""

from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base


class ClassificationJob(Base):
    """Top-level classification job"""
    __tablename__ = "classification_jobs"
    
    id = Column(String, primary_key=True)
    document_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    job_metadata = Column(JSON, nullable=True)
    
    # Relationship
    classifications = relationship("DocumentClassification", back_populates="job", cascade="all, delete-orphan")


class DocumentClassification(Base):
    """Classification results for a document"""
    __tablename__ = "document_classifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("classification_jobs.id"), nullable=False, index=True)
    document_id = Column(String, nullable=False, index=True)
    
    # Classification result
    primary_class = Column(String, nullable=False, index=True)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    
    # Detailed scores
    class_scores = Column(JSON, nullable=True)  # Dict[ClassName, float]
    
    # Metadata and tags
    metadata = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)  # List[str]
    
    # Timestamps
    classified_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    job = relationship("ClassificationJob", back_populates="classifications")
    
    # Human review/feedback
    reviewed_by = Column(String, nullable=True)
    review_feedback = Column(Text, nullable=True)
    is_correct = Column(Integer, nullable=True)  # 1 = correct, 0 = incorrect, None = not reviewed


class ClassificationFeedback(Base):
    """User feedback on classifications for model improvement"""
    __tablename__ = "classification_feedback"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    classification_id = Column(Integer, ForeignKey("document_classifications.id"), nullable=False)
    
    # Feedback
    suggested_class = Column(String, nullable=True)
    feedback_text = Column(Text, nullable=True)
    is_useful = Column(Integer, nullable=True)  # 1 = useful, 0 = not useful
    
    # Meta
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
