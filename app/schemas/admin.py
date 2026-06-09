from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None

class AdminUserResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True

class AdminUserListResponse(BaseModel):
    total: int
    users: List[AdminUserResponse]

class AdminDocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    user_id: int
    uploaded_at: datetime
    owner_email: Optional[str] = None

    class Config:
        from_attributes = True

class AdminDocumentListResponse(BaseModel):
    total: int
    documents: List[AdminDocumentResponse]

class SystemAnalytics(BaseModel):
    total_users: int
    total_documents: int
    total_conversations: int
    total_messages: int
    avg_messages_per_conversation: float
    total_document_size_bytes: int

class AdminMessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class AdminConversationResponse(BaseModel):
    id: int
    title: str
    user_id: int
    owner_email: Optional[str] = None
    message_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
