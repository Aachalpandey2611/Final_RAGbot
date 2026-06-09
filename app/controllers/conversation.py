import logging
from fastapi import APIRouter, Depends, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListResponse,
    ConversationDetailResponse,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
    ChatRequest,
)
from app.services.conversation import ConversationService
from app.services.rag.rag_service import RAGService

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Conversation Endpoints ====================

@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
    description="Creates a new chat conversation for the authenticated user.",
)
async def create_conversation(
    body: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"User {current_user.id} creating conversation")
    service = ConversationService(db)
    return await service.create_conversation(
        user_id=current_user.id, title=body.title
    )


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List user conversations",
    description="Returns all conversations for the authenticated user with pagination.",
)
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    return await service.list_conversations(current_user.id, skip, limit)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation with messages",
    description="Returns a conversation along with all its messages.",
)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    return await service.get_conversation_detail(conversation_id, current_user.id)


@router.put(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Update conversation title",
    description="Updates the title of an existing conversation.",
)
async def update_conversation(
    conversation_id: int,
    body: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    return await service.update_conversation(
        conversation_id, current_user.id, body.title
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
    description="Deletes a conversation and all its messages.",
)
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    await service.delete_conversation(conversation_id, current_user.id)


# ==================== Message Endpoints ====================

@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a message to a conversation",
    description="Adds a new message to the specified conversation.",
)
async def create_message(
    conversation_id: int,
    body: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    return await service.add_message(
        conversation_id, current_user.id, body.role, body.content
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
    summary="List messages in a conversation",
    description="Returns all messages in a conversation with pagination.",
)
async def list_messages(
    conversation_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    return await service.list_messages(
        conversation_id, current_user.id, skip, limit
    )

@router.post(
    "/conversations/{conversation_id}/chat",
    summary="Chat with the RAG assistant (Streaming)",
    description="Streams the AI response using Server-Sent Events (SSE).",
)
@limiter.limit("20/minute")
async def chat_stream(
    request: Request,
    conversation_id: int,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rag_service = RAGService(db)
    return StreamingResponse(
        rag_service.stream_answer(body.query, conversation_id, current_user.id, response_mode=body.response_mode, response_length=body.response_length),
        media_type="text/event-stream"
    )
