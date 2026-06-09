from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user import UserRepository, UserTokenRepository
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.core.config import settings
from app.models.user import User

class AuthService:
    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)
        self.token_repo = UserTokenRepository(db)

    async def register_user(self, user_data: Dict[str, Any]) -> User:
        """
        Registers a new user and hashes the password.
        """
        existing_user = await self.user_repo.get_by_email(user_data["email"])
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists."
            )
        
        # Hash password and structure user data
        hashed = get_password_hash(user_data["password"])
        new_user_payload = {
            "email": user_data["email"],
            "hashed_password": hashed,
            "role": user_data.get("role", "user"),
            "is_active": True
        }
        return await self.user_repo.create(new_user_payload)

    async def authenticate_user(self, email: str, plain_password: str) -> Dict[str, Any]:
        """
        Authenticates a user, generates access and refresh tokens, and registers the refresh token.
        """
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(plain_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user account"
            )
            
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)
        
        # Save refresh token in DB
        expiry_time = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.token_repo.create({
            "token": refresh_token,
            "user_id": user.id,
            "expires_at": expiry_time,
            "is_revoked": False
        })
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user
        }

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Validates refresh token and issues a new access token.
        """
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
            
        # Check token record in database
        db_token = await self.token_repo.get_active_token(refresh_token)
        if not db_token or db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired or revoked"
            )
            
        user_id = payload.get("sub")
        new_access_token = create_access_token(subject=user_id)
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }

    async def logout_user(self, refresh_token: str) -> None:
        """
        Revokes the given refresh token.
        """
        await self.token_repo.revoke_token(refresh_token)
