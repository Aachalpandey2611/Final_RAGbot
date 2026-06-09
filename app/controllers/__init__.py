# Controllers package
from app.controllers.health import router as health_router
from app.controllers.auth import router as auth_router

__all__ = ["health_router", "auth_router"]
