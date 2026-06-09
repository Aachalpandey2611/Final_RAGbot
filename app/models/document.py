from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, BigInteger, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from typing import Optional, Any
try:
    from pgvector.sqlalchemy import Vector
except Exception:
    # pgvector may not be installed in lightweight test environments.
    # Fall back to JSON-compatible storage for embeddings.
    from sqlalchemy import JSON as Vector

class Document(Base):
    """
    Represents an uploaded document's metadata.
    """
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        foreign_keys="[DocumentChunk.document_id]",
    )

class DocumentChunk(Base):
    """
    Represents a chunk of text extracted from a document.
    """
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("document.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    chunk_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    chunking_strategy_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    parent_document_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("document.id", ondelete="SET NULL"), nullable=True, index=True)
    section_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    embedding: Mapped[Optional[Any]] = mapped_column(Vector, nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    embedded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks", foreign_keys=[document_id])
