"""
OCR Service Configuration Guide

This file shows the recommended configuration for the OCR service in different scenarios.
"""

# ============================================================================

# 1. BASIC CONFIGURATION (Single Machine, CPU)

# ============================================================================

# In app/core/config.py or .env

OCR_DEFAULT_PROVIDER=paddle # Fast default provider
OCR_DEFAULT_LANGUAGES=en # Primary language
OCR_USE_GPU=false # CPU-only mode
OCR_CACHE_RETENTION_DAYS=90 # Keep cache for 90 days
OCR_JOB_RETENTION_DAYS=30 # Keep jobs for 30 days

# Celery configuration for single worker

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# ============================================================================

# 2. HIGH-PERFORMANCE CONFIGURATION (GPU-Accelerated)

# ============================================================================

OCR_DEFAULT_PROVIDER=paddle
OCR_DEFAULT_LANGUAGES=en,es,fr,ch # Multiple languages
OCR_USE_GPU=true # Enable GPU
OCR_CACHE_RETENTION_DAYS=180 # Longer cache retention
OCR_JOB_RETENTION_DAYS=60

# Celery with multiple workers

CELERY_BROKER_URL=redis://redis-cluster:6379/0
CELERY_RESULT_BACKEND=redis://redis-cluster:6379/0

# ============================================================================

# 3. DOCUMENT-FOCUSED CONFIGURATION (Tables, PDFs)

# ============================================================================

OCR_DEFAULT_PROVIDER=doctr # DocTR for tables
OCR_DEFAULT_LANGUAGES=en,fr,de # European languages
OCR_USE_GPU=true # Needed for DocTR
OCR_CACHE_RETENTION_DAYS=180 # Keep results longer

# ============================================================================

# 4. MULTILINGUAL CONFIGURATION (Global Deployment)

# ============================================================================

OCR_DEFAULT_PROVIDER=paddle
OCR_DEFAULT_LANGUAGES=en,es,fr,de,ch,ja,ko,ru,ar,hi,pt,it,vi,th
OCR_USE_GPU=true
OCR_CACHE_RETENTION_DAYS=180

# ============================================================================

# 5. LOW-RESOURCE CONFIGURATION (Cost-Optimized)

# ============================================================================

OCR_DEFAULT_PROVIDER=tesseract # Low memory usage
OCR_DEFAULT_LANGUAGES=en
OCR_USE_GPU=false
OCR_CACHE_RETENTION_DAYS=30 # Shorter retention

# Single Celery worker

CELERY_BROKER_URL=redis://localhost:6379/0

# ============================================================================

# PYTHON CONFIGURATION CLASSES

# ============================================================================

# Option 1: Using Pydantic Settings in config.py

from pydantic_settings import BaseSettings
from typing import List

class OCRSettings(BaseSettings): # Provider configuration
OCR_DEFAULT_PROVIDER: str = "paddle"
OCR_DEFAULT_LANGUAGES: List[str] = ["en"]
OCR_USE_GPU: bool = False

    # Retention policies
    OCR_CACHE_RETENTION_DAYS: int = 90
    OCR_JOB_RETENTION_DAYS: int = 30

    # Performance tuning
    OCR_PREPROCESS_DEFAULT: bool = True
    OCR_CONFIDENCE_THRESHOLD: float = 0.3
    OCR_MAX_BATCH_SIZE: int = 100

    # Resource limits
    OCR_MAX_FILE_SIZE_MB: int = 100
    OCR_MAX_IMAGE_DIMENSION: int = 4096
    OCR_TIMEOUT_SECONDS: int = 300

    class Config:
        env_file = ".env"
        case_sensitive = True

# Usage

ocr_settings = OCRSettings()

# ============================================================================

# CELERY CONFIGURATION FOR OCR TASKS

# ============================================================================

from celery import Celery
from kombu import Exchange, Queue

# In app/core/celery_app.py

celery_app = Celery("ocr_app")

# Task routing

celery*app.conf.task_routes = {
"ocr.process_single_file": {"queue": "ocr_single"},
"ocr.process_batch": {"queue": "ocr_batch"},
"ocr.cleanup*\*": {"queue": "cleanup"},
}

# Task configuration

celery_app.conf.task_time_limit = 300 # 5 minutes hard limit
celery_app.conf.task_soft_time_limit = 280 # 4.7 minutes warning

# Queue configuration

celery_app.conf.queues = (
Queue("ocr_single", Exchange("ocr_single"), routing_key="ocr_single"),
Queue("ocr_batch", Exchange("ocr_batch"), routing_key="ocr_batch"),
Queue("cleanup", Exchange("cleanup"), routing_key="cleanup"),
)

# Worker configuration

celery_app.conf.worker_prefetch_multiplier = 4
celery_app.conf.worker_max_tasks_per_child = 1000

# ============================================================================

# STARTUP CONFIGURATION EXAMPLE

# ============================================================================

# In app/main.py or initialization script

from app.services.ocr_service import OCRService
from app.core.config import settings

# Initialize OCR service at startup

ocr_service = OCRService(
default_provider=settings.OCR_DEFAULT_PROVIDER,
languages=settings.OCR_DEFAULT_LANGUAGES,
use_gpu=settings.OCR_USE_GPU,
)

# Pre-initialize providers for faster first request

@app.on_event("startup")
async def startup_ocr():
"""Pre-initialize OCR providers"""
try: # Pre-load default provider
ocr_service.get_provider(settings.OCR_DEFAULT_PROVIDER)
logger.info("OCR service initialized")
except Exception as e:
logger.error(f"Failed to initialize OCR: {str(e)}")

# ============================================================================

# SCHEDULING CLEANUP TASKS (APScheduler)

# ============================================================================

# In app/core/config.py or scheduler setup

from apscheduler.schedulers.background import BackgroundScheduler
from app.tasks_ocr import cleanup_old_ocr_jobs, cleanup_ocr_cache

scheduler = BackgroundScheduler()

# Daily cleanup at 2 AM

scheduler.add_job(
func=cleanup_old_ocr_jobs.delay,
trigger="cron",
hour=2,
minute=0,
args=(30,), # Delete jobs older than 30 days
id="cleanup_ocr_jobs",
)

# Weekly cache cleanup

scheduler.add_job(
func=cleanup_ocr_cache.delay,
trigger="cron",
day_of_week=0, # Sunday
hour=3,
minute=0,
args=(90,), # Delete cache older than 90 days
id="cleanup_ocr_cache",
)

scheduler.start()

# ============================================================================

# DATABASE INITIALIZATION

# ============================================================================

# Ensure OCR models are created during database initialization

# In app/main.py lifespan

from app.models.ocr import OCRJob, OCRBatch, OCRCache

@asynccontextmanager
async def lifespan(app: FastAPI):
async with engine.begin() as conn: # Create all tables including OCR models
await conn.run_sync(Base.metadata.create_all)
yield

# ============================================================================

# LOGGING CONFIGURATION FOR OCR

# ============================================================================

# In app/core/logging.py

LOGGING_CONFIG = {
"version": 1,
"disable_existing_loggers": False,
"formatters": {
"standard": {
"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
},
},
"handlers": {
"ocr": {
"class": "logging.handlers.RotatingFileHandler",
"filename": "logs/ocr.log",
"maxBytes": 10485760, # 10MB
"backupCount": 10,
"formatter": "standard",
},
},
"loggers": {
"app.services.ocr": {
"handlers": ["ocr"],
"level": "INFO",
"propagate": False,
},
},
}

# ============================================================================

# DOCKER COMPOSE CONFIGURATION

# ============================================================================

# In docker-compose.yml

version: '3.8'

services:

# OCR Service API

ocr-api:
build: .
ports: - "8000:8000"
environment: - OCR_DEFAULT_PROVIDER=paddle - OCR_USE_GPU=false - CELERY_BROKER_URL=redis://redis:6379/0
depends_on: - redis - postgres

# OCR Worker (Process single files)

ocr-worker-single:
build: .
command: celery -A app.core.celery_app worker -l info -Q ocr_single
environment: - OCR_DEFAULT_PROVIDER=paddle - OCR_USE_GPU=true
depends_on: - redis - postgres
deploy:
resources:
reservations:
devices: - driver: nvidia
count: 1
capabilities: [gpu]

# OCR Worker (Process batches)

ocr-worker-batch:
build: .
command: celery -A app.core.celery_app worker -l info -Q ocr_batch
environment: - OCR_DEFAULT_PROVIDER=paddle - OCR_USE_GPU=false
depends_on: - redis - postgres
deploy:
replicas: 2

# Redis for Celery

redis:
image: redis:7-alpine
ports: - "6379:6379"

# Celery Flower for monitoring

flower:
image: mher/flower
command: celery -A app.core.celery_app flower
ports: - "5555:5555"
depends_on: - redis

# ============================================================================

# PROVIDER-SPECIFIC CONFIGURATION

# ============================================================================

# PaddleOCR Settings

PADDLE_OCR_VERSION=2.7.0
PADDLE_USE_GPU=true
PADDLE_USE_MKL=true # For CPU optimization

# Tesseract Settings

TESSERACT_CMD=/usr/bin/tesseract # Path to tesseract binary

# DocTR Settings

DOCTR_USE_GPU=true
DOCTR_MODEL_VERSION=doctr_mobilenet_v3_large

# ============================================================================

# PERFORMANCE TUNING

# ============================================================================

# Connection Pooling

SQLALCHEMY_POOL_SIZE=20
SQLALCHEMY_MAX_OVERFLOW=40

# Caching

REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_KEEPALIVE=true

# FastAPI

WORKERS=4 # Number of uvicorn workers
WORKER_CONNECTIONS=100

# Celery

CELERYD_PREFETCH_MULTIPLIER=4
CELERY_TASK_ACKS_LATE=true
CELERY_WORKER_PREFETCH_MULTIPLIER=4

# ============================================================================

# MONITORING & METRICS

# ============================================================================

# Prometheus metrics (if using prometheus-client)

OCR_METRICS_ENABLED=true

# Sentry error tracking

SENTRY_DSN=https://key@sentry.io/project

# ============================================================================

# TESTING CONFIGURATION

# ============================================================================

# Test database

TEST_DATABASE_URL=postgresql://user:pass@localhost/test_db

# Disable Celery for tests (use synchronous mode)

CELERY_ALWAYS_EAGER=true
CELERY_EAGER_PROPAGATES_EXCEPTIONS=true

# Test file locations

TEST_IMAGE_PATH=tests/fixtures/images
TEST_PDF_PATH=tests/fixtures/pdfs

# ============================================================================

# RECOMMENDED DEPLOYMENT CONFIGURATIONS

# ============================================================================

"""

1. SINGLE MACHINE (CPU)
   - Provider: Tesseract (low memory)
   - Workers: 1
   - Preprocessing: Minimal
   - Best for: Development, testing

2. SINGLE MACHINE (GPU)
   - Provider: PaddleOCR
   - Workers: 2-3
   - Preprocessing: Full
   - Best for: Production, single server

3. DISTRIBUTED (Multiple GPU Servers)
   - Provider: PaddleOCR + DocTR
   - Worker Pools: Separate GPU/CPU workers
   - Load Balancing: Router queues by type
   - Best for: High-volume production

4. CLOUD (AWS/GCP/Azure)
   - Provider: PaddleOCR
   - Auto-scaling: Based on queue depth
   - Storage: Cloud object storage (S3/GCS)
   - Database: Managed PostgreSQL
   - Caching: Managed Redis (ElastiCache)
   - Best for: Enterprise deployment
     """

# ============================================================================

# HEALTH CHECK CONFIGURATION

# ============================================================================

# In app/controllers/health.py

@app.get("/health/ocr")
async def ocr_health():
"""Check OCR service health"""
try: # Test OCR service availability
provider = ocr_service.get_provider()

        # Check database connectivity
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()

        return {
            "status": "healthy",
            "ocr_provider": provider.provider_name,
            "gpu_enabled": settings.OCR_USE_GPU,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
