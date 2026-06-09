"""
API endpoints for document classification
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.services.classification import DocumentClassifier, DocumentClass
from app.schemas.classification import (
    ClassifyDocumentRequest,
    ClassificationResponse,
    ClassificationJobResponse,
    ClassificationJobDetails,
    ClassificationFeedbackRequest,
    ClassificationStatsResponse,
)
from app.core.deps import get_db
from app.repositories import classification as classification_repo

router = APIRouter()

# Initialize classifier (would be better in a service container)
classifier = DocumentClassifier(use_embeddings=True)


@router.post("/api/v1/classify", response_model=ClassificationResponse)
async def classify_document(request: ClassifyDocumentRequest, db: AsyncSession = Depends(get_db)):
    """
    Classify a document text.
    
    Returns the primary classification, confidence score, and detailed scores for all classes.
    """
    # Classify
    result = classifier.classify(request.text, request.document_id)
    
    # Create job
    job_id = str(uuid.uuid4())
    await classification_repo.create_classification_job(
        db,
        job_id,
        result.document_id,
        request.filename,
        {"text_length": len(request.text)}
    )
    
    # Store classification
    await classification_repo.store_classification(
        db,
        job_id,
        result.document_id,
        result.primary_class.value,
        result.confidence,
        {k.value: v for k, v in result.class_scores.items()},
        result.metadata,
        result.tags
    )
    
    # Update job status
    await classification_repo.update_job_status(db, job_id, "completed")
    await db.commit()
    
    return ClassificationResponse(
        document_id=result.document_id,
        primary_class=result.primary_class.value,
        confidence=result.confidence,
        class_scores={k.value: v for k, v in result.class_scores.items()},
        metadata=result.metadata,
        tags=result.tags,
        timestamp=result.timestamp
    )


@router.post("/api/v1/classify/batch", response_model=ClassificationJobResponse)
async def classify_batch(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """
    Classify multiple documents from a file.
    
    Expects a text file with one document per line (or multiple documents separated by ---)
    """
    job_id = str(uuid.uuid4())
    content = await file.read()
    text = content.decode('utf-8')
    
    # Split documents
    documents = text.split('---')
    documents = [doc.strip() for doc in documents if doc.strip()]
    
    if not documents:
        raise HTTPException(status_code=400, detail="No documents found in file")
    
    # Create job
    await classification_repo.create_classification_job(
        db,
        job_id,
        f"batch_{uuid.uuid4()}",
        file.filename,
        {"document_count": len(documents)}
    )
    
    # Classify each document
    results = []
    for i, doc_text in enumerate(documents):
        doc_id = f"{job_id}_doc_{i}"
        result = classifier.classify(doc_text, doc_id)
        
        await classification_repo.store_classification(
            db,
            job_id,
            result.document_id,
            result.primary_class.value,
            result.confidence,
            {k.value: v for k, v in result.class_scores.items()},
            result.metadata,
            result.tags
        )
        results.append(result)
    
    # Update job status
    await classification_repo.update_job_status(db, job_id, "completed")
    await db.commit()
    
    return ClassificationJobResponse(
        job_id=job_id,
        document_id=f"batch_{uuid.uuid4()}",
        status="completed",
        files_count=len(results),
        metadata={"classified_documents": len(documents)}
    )


@router.get("/api/v1/classify/job/{job_id}", response_model=ClassificationJobDetails)
async def get_classification_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get classification results for a job"""
    details = await classification_repo.get_classification(db, job_id)
    if not details:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return ClassificationJobDetails(
        job=details["job"],
        classifications=[
            {
                **c,
                "classified_at": c["classified_at"]
            }
            for c in details["classifications"]
        ]
    )


@router.get("/api/v1/classify/class/{doc_class}", response_model=List[DocumentClassificationDetail])
async def get_classifications_by_class(doc_class: str, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get recent classifications for a specific class"""
    # Validate class name
    try:
        doc_class_enum = DocumentClass[doc_class.upper().replace(" ", "_")]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid document class: {doc_class}")
    
    classifications = await classification_repo.get_classifications_by_class(db, doc_class_enum.value, limit)
    
    return [
        {
            "id": c.id,
            "document_id": c.document_id,
            "primary_class": c.primary_class,
            "confidence": c.confidence,
            "class_scores": c.class_scores or {},
            "metadata": c.metadata or {},
            "tags": c.tags or [],
            "classified_at": c.classified_at.isoformat() if c.classified_at else None,
        }
        for c in classifications
    ]


@router.post("/api/v1/classify/job/{job_id}/feedback")
async def submit_feedback(job_id: str, feedback: ClassificationFeedbackRequest, 
                         user_id: str = "system", db: AsyncSession = Depends(get_db)):
    """Submit feedback on a classification"""
    # Get classification
    q = select(DocumentClassification).where(DocumentClassification.id == job_id)
    res = await db.execute(q)
    classification = res.scalar_one_or_none()
    
    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")
    
    # Add feedback
    feedback_obj = await classification_repo.add_feedback(
        db,
        classification.id,
        feedback.suggested_class,
        feedback.feedback_text,
        feedback.is_useful,
        user_id
    )
    
    await db.commit()
    
    return {"status": "feedback_recorded", "feedback_id": feedback_obj.id}


@router.get("/api/v1/classify/stats", response_model=ClassificationStatsResponse)
async def get_statistics(db: AsyncSession = Depends(get_db)):
    """Get classification statistics"""
    stats = await classification_repo.get_classification_stats(db)
    return stats


@router.get("/api/v1/classify/classes")
async def list_classes():
    """List all supported document classes"""
    return {
        "classes": [
            {
                "name": doc_class.value,
                "keywords": classifier.get_class_info(doc_class)["keywords"][:5],
                "characteristics": classifier.get_class_info(doc_class)["characteristics"],
            }
            for doc_class in DocumentClass
        ]
    }


# Import here to avoid circular imports
from sqlalchemy import select
from app.models.classification import DocumentClassification
