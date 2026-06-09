import logging
from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, RoleChecker
from app.core.rate_limit import limiter
from app.schemas.auth import (
    UserCreate,
    UserResponse,
    TokenResponse,
    TokenRefreshRequest,
    TokenRefreshResponse
)
from app.services.auth import AuthService
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user and returns user info."
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user_in: UserCreate, 
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Registering user: {user_in.email}")
    auth_service = AuthService(db)
    return await auth_service.register_user(user_in.model_dump())

@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="User Login",
    description="Authenticates credentials and returns access and refresh tokens."
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Login request received for user: {form_data.username}")
    auth_service = AuthService(db)
    return await auth_service.authenticate_user(form_data.username, form_data.password)

@router.post(
    "/auth/refresh",
    response_model=TokenRefreshResponse,
    summary="Refresh Access Token",
    description="Validates a refresh token and generates a new access token."
)
async def refresh(
    refresh_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)
    return await auth_service.refresh_access_token(refresh_data.refresh_token)

@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="User Logout",
    description="Revokes the specified refresh token."
)
async def logout(
    logout_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)
    await auth_service.logout_user(logout_data.refresh_token)

# --- Role-Based Access Control Examples ---

@router.get(
    "/users/me",
    response_model=UserResponse,
    summary="Get current user details",
    description="Retrieves profile of the authenticated user."
)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get(
    "/admin/dashboard",
    summary="Admin only area",
    description="Secured endpoint demonstrating role-based authentication restriction."
)
async def admin_dashboard(
    current_admin: User = Depends(RoleChecker(allowed_roles=["admin"]))
):
    return {
        "message": "Welcome to the Admin Dashboard",
        "admin_email": current_admin.email
    }
