from datetime import datetime
from typing import List
from pydantic import BaseModel

class DocumentResponse(BaseModel):
    id: int
    original_filename: str
    file_type: str
    file_size: int
    user_id: int
    uploaded_at: datetime

    class Config:
        from_attributes = True

class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentResponse]
