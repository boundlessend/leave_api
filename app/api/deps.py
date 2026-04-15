from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis import Redis
from sqlalchemy.orm import Session

from app.api.errors import AppException
from app.core.redis_client import get_redis_client
from app.core.security import decode_token
from app.db.models import User
from app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def get_redis() -> Redis:
    """отдает redis клиент"""
    return get_redis_client()


RedisClient = Annotated[Redis, Depends(get_redis)]


def get_access_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> str:
    """достает access token из bearer заголовка"""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppException(
            401, "not_authenticated", "требуется bearer access token"
        )
    return credentials.credentials


def get_current_user(
    db: DbSession,
    redis: RedisClient,
    access_token: Annotated[str, Depends(get_access_token)],
) -> User:
    """возвращает текущего пользователя по access token"""
    token_data = decode_token(access_token, expected_type="access")
    if not redis.get(f"access:{token_data.jti}"):
        raise AppException(401, "invalid_token", "невалидный токен")

    user = db.get(User, token_data.user_id)
    if user is None or not user.is_active:
        raise AppException(401, "invalid_token", "невалидный токен")
    return user


def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """проверяет что текущий пользователь администратор"""
    if not current_user.is_admin:
        raise AppException(403, "forbidden", "недостаточно прав")
    return current_user
