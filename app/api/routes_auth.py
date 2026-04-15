from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    DbSession,
    RedisClient,
    get_access_token,
    get_current_user,
)
from app.db.models import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenPairResponse,
    UserRead,
)
from app.schemas.common import MessageResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/jwt/login",
    response_model=TokenPairResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    payload: LoginRequest, db: DbSession, redis: RedisClient
) -> TokenPairResponse:
    """логинит пользователя по email и паролю"""
    return AuthService(db, redis).login(payload.email, payload.password)


@router.post(
    "/jwt/refresh",
    response_model=TokenPairResponse,
    status_code=status.HTTP_200_OK,
)
def refresh_tokens(
    payload: RefreshRequest, db: DbSession, redis: RedisClient
) -> TokenPairResponse:
    """обновляет access и refresh токены"""
    return AuthService(db, redis).refresh(payload.refresh_token)


@router.post(
    "/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
def logout(
    access_token: Annotated[str, Depends(get_access_token)],
    _: Annotated[User, Depends(get_current_user)],
    db: DbSession,
    redis: RedisClient,
) -> MessageResponse:
    """разлогинивает пользователя по текущему access token"""
    AuthService(db, redis).logout_access_token(access_token)
    return MessageResponse(message="ok")


@router.get(
    "/users/me", response_model=UserRead, status_code=status.HTTP_200_OK
)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    """возвращает профиль текущего пользователя"""
    return current_user
