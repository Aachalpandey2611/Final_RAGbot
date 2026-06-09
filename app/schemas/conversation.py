from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ---------- Conversation Schemas ----------

class ConversationCreate(BaseModel):
    title: Optional[str] = Field("New Conversation", max_length=255, description="Conversation title")

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User's message to the chatbot")
    response_mode: Optional[str] = Field("normal", description="Response mode: 'simple', 'normal', or 'technical'")
    response_length: Optional[str] = Field("standard", description="Response length: 'quick', 'standard', or 'detailed'")


class ConversationUpdate(BaseModel):
    title: str = Field(..., max_length=255, description="Updated conversation title")


class ConversationResponse(BaseModel):
    id: int
    title: str
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    total: int
    conversations: List[ConversationResponse]


# ---------- Message Schemas ----------

class MessageCreate(BaseModel):
    role: str = Field("user", description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., min_length=1, description="Message content text")


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    total: int
    messages: List[MessageResponse]


# ---------- Conversation Detail (with messages) ----------

class ConversationDetailResponse(BaseModel):
    id: int
    title: str
    user_id: int
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True
