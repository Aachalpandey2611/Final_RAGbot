import logging
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from typing import List, Dict, Any

from app.core.database import get_db
from app.core.deps import RoleChecker
from app.models.user import User
from app.models.document import Document
from app.models.conversation import Conversation, Message
from app.schemas.admin import (
    UserUpdate,
    AdminUserResponse,
    AdminUserListResponse,
    AdminDocumentResponse,
    AdminDocumentListResponse,
    SystemAnalytics,
    AdminConversationResponse,
    AdminMessageResponse
)
from app.services.document import DocumentService

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(RoleChecker(["admin"]))]
)

# ==================== User Management ====================

@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List all users",
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(User).offset(skip).limit(limit)
    result = await db.execute(query)
    users = list(result.scalars().all())

    count_query = select(func.count(User.id))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    return {"total": total, "users": users}

@router.put(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Update user details",
)
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    updates = {}
    if body.role is not None:
        updates["role"] = body.role
    if body.is_active is not None:
        updates["is_active"] = body.is_active

    if updates:
        for k, v in updates.items():
            setattr(user, k, v)
        await db.commit()
        await db.refresh(user)

    return user

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    await db.delete(user)
    await db.commit()

# ==================== Document Management ====================

@router.get(
    "/documents",
    response_model=AdminDocumentListResponse,
    summary="List all documents system-wide",
)
async def list_all_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Document, User.email.label("owner_email"))
        .join(User, Document.user_id == User.id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    documents_with_emails = []
    
    for row in result.all():
        doc = row[0]
        email = row[1]
        # Dynamically set owner_email attribute for schema conversion
        setattr(doc, "owner_email", email)
        documents_with_emails.append(doc)

    count_query = select(func.count(Document.id))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    return {"total": total, "documents": documents_with_emails}

@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete any document",
)
async def delete_any_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    query = select(Document).where(Document.id == document_id)
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    doc_service = DocumentService(db)
    # Reuses the exact same document service logic (deletes embeddings, DB entries, and disk files)
    await doc_service.delete_document(document_id=document_id, user_id=document.user_id)

# ==================== Analytics ====================

@router.get(
    "/analytics",
    response_model=SystemAnalytics,
    summary="Get system analytics",
)
async def get_system_analytics(db: AsyncSession = Depends(get_db)):
    users_count = await db.execute(select(func.count(User.id)))
    docs_count = await db.execute(select(func.count(Document.id)))
    convs_count = await db.execute(select(func.count(Conversation.id)))
    msgs_count = await db.execute(select(func.count(Message.id)))
    
    total_size_query = select(func.coalesce(func.sum(Document.file_size), 0))
    total_size_result = await db.execute(total_size_query)
    total_size = total_size_result.scalar_one()

    total_convs = convs_count.scalar_one()
    total_msgs = msgs_count.scalar_one()
    
    avg_msgs = 0.0
    if total_convs > 0:
        avg_msgs = round(total_msgs / total_convs, 2)

    return {
        "total_users": users_count.scalar_one(),
        "total_documents": docs_count.scalar_one(),
        "total_conversations": total_convs,
        "total_messages": total_msgs,
        "avg_messages_per_conversation": avg_msgs,
        "total_document_size_bytes": total_size
    }

# ==================== Chat Logs ====================

@router.get(
    "/chat-logs/conversations",
    response_model=List[AdminConversationResponse],
    summary="Get all conversations with message count",
)
async def get_all_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(
            Conversation,
            User.email.label("owner_email"),
            func.count(Message.id).label("message_count")
        )
        .join(User, Conversation.user_id == User.id)
        .outerjoin(Message, Conversation.id == Message.conversation_id)
        .group_by(Conversation.id, User.email)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    conversations = []
    
    for row in result.all():
        conv = row[0]
        email = row[1]
        msg_count = row[2]
        setattr(conv, "owner_email", email)
        setattr(conv, "message_count", msg_count)
        conversations.append(conv)

    return conversations

@router.get(
    "/chat-logs/conversations/{conversation_id}/messages",
    response_model=List[AdminMessageResponse],
    summary="Get messages for a conversation",
)
async def get_conversation_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())
