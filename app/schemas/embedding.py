from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class EmbedDocumentRequest(BaseModel):
    provider: Optional[str] = None

class EmbeddingStatusResponse(BaseModel):
    document_id: int
    total_chunks: int
    embedded_chunks: int
    embedding_model: Optional[str] = None
    is_complete: bool

class EmbeddingResponse(BaseModel):
    chunk_id: int
    embedding_model: str
    dimension: int
    embedded_at: datetime

    class Config:
        from_attributes = True
