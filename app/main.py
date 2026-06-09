import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.controllers.health import router as health_router
# Lazy imports to avoid heavy dependency issues
from app.controllers.auth import router as auth_router
from app.controllers.document import router as document_router
from app.controllers.conversation import router as conversation_router
# from app.controllers.admin import router as admin_router
# from app.controllers.ocr import router as ocr_router
# from app.controllers.binary import router as binary_router

from app.models import Base  # imports User, UserToken via models/__init__.py
from app.core.database import engine

# SlowAPI Rate Limiting setup
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter

# Sentry Setup (optional)
# if settings.SENTRY_DSN:
#     import sentry_sdk
#     from sentry_sdk.integrations.fastapi import FastApiIntegration
#     sentry_sdk.init(
#         dsn=settings.SENTRY_DSN,
#         integrations=[FastApiIntegration()],
#         traces_sample_rate=1.0,
#         profiles_sample_rate=1.0,
#     )

# Setup logging immediately on module import
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info("Starting up FastAPI MVC Application...")
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully.")
    yield
    # Shutdown tasks
    logger.info("Shutting down FastAPI MVC Application...")

# Initialize FastAPI App
app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade FastAPI Backend structure using MVC architecture and Repository Pattern",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan
)

# SlowAPI State & Handler configuration
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Custom Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        f"HTTP Request | Method: {request.method} | Path: {request.url.path} | "
        f"Status: {response.status_code} | Duration: {duration:.4f}s"
    )
    return response

# Prometheus Instrumentation Setup (optional)
# from prometheus_fastapi_instrumentator import Instrumentator
# Instrumentator().instrument(app).expose(app)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(health_router, prefix="", tags=["System"])
app.include_router(auth_router, prefix=settings.API_V1_STR, tags=["Authentication & Access"])
app.include_router(document_router, prefix=settings.API_V1_STR, tags=["Documents"])
app.include_router(conversation_router, prefix=settings.API_V1_STR, tags=["Chat"])
# app.include_router(admin_router, prefix=settings.API_V1_STR, tags=["Admin Dashboard"])
# app.include_router(ocr_router, prefix=settings.API_V1_STR, tags=["OCR Processing"])
# app.include_router(binary_router, prefix=settings.API_V1_STR, tags=["Binary Processing"])

@app.get("/", tags=["Root"])
async def root_endpoint():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs_url": "/docs",
        "status": "running"
    }

