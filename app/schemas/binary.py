from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class BinaryExtractResponse(BaseModel):
    job_id: str
    files_count: int
    metadata: Dict[str, Any]


class BinaryFileSchema(BaseModel):
    path: str
    size: int
    sha256: str
    mime_type: Optional[str]
    extra: Optional[Dict[str, Any]]


class BinaryJobDetails(BaseModel):
    job: Dict[str, Any]
    files: List[BinaryFileSchema]
    relationships: List[Dict[str, Any]]
