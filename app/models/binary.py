from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base


class BinaryJob(Base):
    __tablename__ = "binary_jobs"
    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    job_metadata = Column(JSON, nullable=True)
    files = relationship("BinaryFile", back_populates="job")


class BinaryFile(Base):
    __tablename__ = "binary_files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("binary_jobs.id"), nullable=False)
    path = Column(Text, nullable=False)
    size = Column(Integer)
    sha256 = Column(String(64))
    mime_type = Column(String)
    extra = Column(JSON, nullable=True)
    job = relationship("BinaryJob", back_populates="files")


class BinaryRelationship(Base):
    __tablename__ = "binary_relationships"
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("binary_jobs.id"), nullable=False)
    parent = Column(Text, nullable=False)
    child = Column(Text, nullable=False)
    relation_type = Column(String, default="contains")
