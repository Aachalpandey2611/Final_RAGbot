import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings
from app.schemas.health import HealthCheck

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get(
    "/health",
    response_model=HealthCheck,
    status_code=status.HTTP_200_OK,
    summary="Perform a Health Check",
    description="Tests application and database connectivity."
)
async def perform_health_check(db: AsyncSession = Depends(get_db)):
    db_status = "online"
    
    try:
        # Perform simple query to verify db connection is working
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "offline"
        
    health_status = "healthy" if db_status == "online" else "unhealthy"
    
    response = HealthCheck(
        status=health_status,
        environment=settings.APP_ENV,
        services={
            "database": db_status
        }
    )
    
    if health_status != "healthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.model_dump()
        )
        
    return response
