# Schemas package
from app.schemas.health import HealthCheck
from app.schemas.auth import UserCreate, UserResponse, TokenResponse, TokenRefreshRequest, TokenRefreshResponse
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.schemas.embedding import EmbedDocumentRequest, EmbeddingStatusResponse, EmbeddingResponse
from app.schemas.ocr import (
    OCRRequestSchema,
    OCRResultSchema,
    OCRStatusSchema,
    OCRBatchRequestSchema,
    OCRBatchStatusSchema,
    TextRegionSchema,
    TableSchema,
)

__all__ = [
    "HealthCheck",
    "UserCreate",
    "UserResponse",
    "TokenResponse",
    "TokenRefreshRequest",
    "TokenRefreshResponse",
    "DocumentResponse",
    "DocumentListResponse",
    "EmbedDocumentRequest",
    "EmbeddingStatusResponse",
    "EmbeddingResponse",
    "OCRRequestSchema",
    "OCRResultSchema",
    "OCRStatusSchema",
    "OCRBatchRequestSchema",
    "OCRBatchStatusSchema",
    "TextRegionSchema",
    "TableSchema",
]
from app.schemas.binary import BinaryExtractResponse, BinaryFileSchema, BinaryJobDetails

__all__.extend([
    "BinaryExtractResponse",
    "BinaryFileSchema",
    "BinaryJobDetails",
])
