import os
from typing import Any, Dict, Optional
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "fastapi-mvc-app"
    APP_ENV: str = "local"
    DEBUG: bool = True
    PORT: int = 8000
    API_V1_STR: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # PostgreSQL Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "chatbot_db"
    
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    SQLALCHEMY_DATABASE_URI_ASYNC: Optional[str] = None

    # JWT Authentication settings
    JWT_SECRET_KEY: str = "secret-super-key-change-in-production-1234567"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # RAG Chunker settings
    DEFAULT_CHUNK_SIZE: int = 1200
    DEFAULT_CHUNK_OVERLAP: int = 300

    # Document Upload Settings
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_FILE_TYPES: set[str] = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # DOCX
        "text/plain",
        "text/csv",
        "text/markdown",
        "application/octet-stream", # some OS might detect md as this
        "image/png",
        "image/jpeg",
        "image/jpg",
        "application/msword", # DOC
        "application/vnd.ms-excel", # XLS
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", # XLSX
        "application/zip",
        "application/x-zip-compressed"
    }

    # Embedding Settings
    EMBEDDING_PROVIDER: str = "gemini" # 'gemini' or 'huggingface'
    EMBEDDING_DIMENSION: int = 768
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"
    HF_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Vector Database settings
    VECTOR_DB_PROVIDER: str = "chroma"
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"

    # Redis Config
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # Celery Config
    CELERY_BROKER_URL: str = "redis://127.0.0.1:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://127.0.0.1:6379/1"

    # Rate Limiting
    RATE_LIMIT_CHAT: str = "20/minute"

    # Sentry Configuration
    SENTRY_DSN: Optional[str] = None

    # Hybrid Search and Reranker Settings
    RERANKER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    HYBRID_SEARCH_TOP_N: int = 20

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            clean_v = v.strip().strip("'").strip('"')
            return [i.strip().strip("'").strip('"') for i in clean_v.split(",")]
        elif isinstance(v, list):
            return [str(i).strip().strip("'").strip('"') for i in v]
        elif isinstance(v, str):
            return [v.strip().strip("'").strip('"')]
        return v

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: Any) -> Any:
        if isinstance(v, str) and v:
            return v
        
        values = info.data
        server = values.get("POSTGRES_SERVER")
        port = values.get("POSTGRES_PORT")
        user = values.get("POSTGRES_USER")
        password = values.get("POSTGRES_PASSWORD")
        db = values.get("POSTGRES_DB")
        
        return f"postgresql://{user}:{password}@{server}:{port}/{db}"

    @field_validator("SQLALCHEMY_DATABASE_URI_ASYNC", mode="before")
    @classmethod
    def assemble_async_db_connection(cls, v: Optional[str], info: Any) -> Any:
        if isinstance(v, str) and v:
            return v
        
        values = info.data
        server = values.get("POSTGRES_SERVER")
        port = values.get("POSTGRES_PORT")
        user = values.get("POSTGRES_USER")
        password = values.get("POSTGRES_PASSWORD")
        db = values.get("POSTGRES_DB")
        
        return f"postgresql+asyncpg://{user}:{password}@{server}:{port}/{db}"

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
