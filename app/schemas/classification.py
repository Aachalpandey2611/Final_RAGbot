"""
Pydantic schemas for classification API
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class ClassifyDocumentRequest(BaseModel):
    """Request to classify a document"""
    text: str = Field(..., min_length=10, description="Document text to classify")
    document_id: Optional[str] = Field(None, description="Optional document identifier")
    filename: Optional[str] = Field(None, description="Optional filename for metadata")


class ClassificationScoreDetail(BaseModel):
    """Score for a single classification class"""
    class_name: str
    score: float = Field(..., ge=0.0, le=1.0)


class ClassificationResponse(BaseModel):
    """Classification result for a document"""
    document_id: str
    primary_class: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    class_scores: Dict[str, float]
    metadata: Dict[str, Any]
    tags: List[str]
    timestamp: str


class ClassificationJobResponse(BaseModel):
    """Response for a classification job"""
    job_id: str
    document_id: str
    status: str
    files_count: int
    metadata: Dict[str, Any]


class DocumentClassificationDetail(BaseModel):
    """Detailed classification information"""
    id: int
    document_id: str
    primary_class: str
    confidence: float
    class_scores: Dict[str, float]
    metadata: Dict[str, Any]
    tags: List[str]
    classified_at: str


class ClassificationJobDetails(BaseModel):
    """Full job details with classifications"""
    job: Dict[str, Any]
    classifications: List[DocumentClassificationDetail]


class ClassificationFeedbackRequest(BaseModel):
    """Feedback on a classification"""
    suggested_class: Optional[str] = Field(None, description="If classification was wrong, suggest correct class")
    feedback_text: Optional[str] = Field(None, description="Free-form feedback text")
    is_useful: Optional[int] = Field(None, description="1 = useful, 0 = not useful")


class ClassificationStatsResponse(BaseModel):
    """Classification statistics"""
    total_classifications: int
    by_class: Dict[str, int]
    confidence_stats: Dict[str, int]
