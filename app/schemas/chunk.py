from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel

class ChunkResponse(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    meta_data: Optional[dict[str, Any]] = None
    chunk_type: Optional[str] = None
    chunking_strategy_used: Optional[str] = None
    parent_document_id: Optional[int] = None
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChunkListResponse(BaseModel):
    document_id: int
    total: int
    chunks: list[ChunkResponse]

class ChunkCreateRequest(BaseModel):
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
