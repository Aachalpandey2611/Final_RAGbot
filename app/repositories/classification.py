"""
Repository for document classification data access
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Dict, Any, Optional
from app.models.classification import ClassificationJob, DocumentClassification, ClassificationFeedback


async def create_classification_job(db: AsyncSession, job_id: str, document_id: str, 
                                    filename: Optional[str] = None, metadata: Optional[Dict] = None) -> ClassificationJob:
    """Create a new classification job"""
    job = ClassificationJob(
        id=job_id,
        document_id=document_id,
        filename=filename,
        status="pending",
        job_metadata=metadata or {}
    )
    db.add(job)
    await db.flush()
    return job


async def store_classification(db: AsyncSession, job_id: str, document_id: str,
                              primary_class: str, confidence: float,
                              class_scores: Dict[str, float],
                              metadata: Dict[str, Any],
                              tags: List[str]) -> DocumentClassification:
    """Store a classification result"""
    classification = DocumentClassification(
        job_id=job_id,
        document_id=document_id,
        primary_class=primary_class,
        confidence=confidence,
        class_scores=class_scores,
        metadata=metadata,
        tags=tags
    )
    db.add(classification)
    await db.flush()
    return classification


async def update_job_status(db: AsyncSession, job_id: str, status: str) -> Optional[ClassificationJob]:
    """Update job status"""
    q = select(ClassificationJob).where(ClassificationJob.id == job_id)
    res = await db.execute(q)
    job = res.scalar_one_or_none()
    if job:
        job.status = status
        if status == "completed":
            from datetime import datetime
            job.completed_at = datetime.utcnow()
        await db.flush()
    return job


async def get_classification(db: AsyncSession, job_id: str) -> Optional[Dict[str, Any]]:
    """Get classification result for a job"""
    q = select(ClassificationJob).where(ClassificationJob.id == job_id)
    res = await db.execute(q)
    job = res.scalar_one_or_none()
    if not job:
        return None
    
    # Get classifications for this job
    class_q = select(DocumentClassification).where(DocumentClassification.job_id == job_id)
    class_res = await db.execute(class_q)
    classifications = class_res.scalars().all()
    
    return {
        "job": {
            "id": job.id,
            "document_id": job.document_id,
            "filename": job.filename,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        },
        "classifications": [
            {
                "id": c.id,
                "document_id": c.document_id,
                "primary_class": c.primary_class,
                "confidence": c.confidence,
                "class_scores": c.class_scores,
                "metadata": c.metadata,
                "tags": c.tags,
                "classified_at": c.classified_at.isoformat() if c.classified_at else None,
            }
            for c in classifications
        ]
    }


async def get_classifications_by_class(db: AsyncSession, doc_class: str, 
                                      limit: int = 100) -> List[DocumentClassification]:
    """Get recent classifications for a specific class"""
    q = select(DocumentClassification)\
        .where(DocumentClassification.primary_class == doc_class)\
        .order_by(desc(DocumentClassification.classified_at))\
        .limit(limit)
    res = await db.execute(q)
    return res.scalars().all()


async def get_classifications_by_document(db: AsyncSession, document_id: str) -> List[DocumentClassification]:
    """Get all classifications for a document"""
    q = select(DocumentClassification)\
        .where(DocumentClassification.document_id == document_id)\
        .order_by(desc(DocumentClassification.classified_at))
    res = await db.execute(q)
    return res.scalars().all()


async def add_feedback(db: AsyncSession, classification_id: int, suggested_class: Optional[str],
                      feedback_text: Optional[str], is_useful: Optional[int], created_by: str) -> ClassificationFeedback:
    """Add feedback for a classification"""
    feedback = ClassificationFeedback(
        classification_id=classification_id,
        suggested_class=suggested_class,
        feedback_text=feedback_text,
        is_useful=is_useful,
        created_by=created_by
    )
    db.add(feedback)
    await db.flush()
    return feedback


async def get_classification_stats(db: AsyncSession) -> Dict[str, Any]:
    """Get classification statistics"""
    # Total classifications
    total_q = select(DocumentClassification)
    total_res = await db.execute(total_q)
    total = len(total_res.scalars().all())
    
    # By class
    class_q = select(DocumentClassification.primary_class).distinct()
    class_res = await db.execute(class_q)
    classes = class_res.scalars().all()
    
    by_class = {}
    for doc_class in classes:
        q = select(DocumentClassification).where(DocumentClassification.primary_class == doc_class)
        res = await db.execute(q)
        by_class[doc_class] = len(res.scalars().all())
    
    return {
        "total_classifications": total,
        "by_class": by_class,
        "confidence_stats": {
            "high": len([c for c in total_res.scalars().all() if c.confidence > 0.8]),
            "medium": len([c for c in total_res.scalars().all() if 0.5 < c.confidence <= 0.8]),
            "low": len([c for c in total_res.scalars().all() if c.confidence <= 0.5]),
        }
    }
