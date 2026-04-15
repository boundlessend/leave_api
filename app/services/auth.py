from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import AppException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.db.models import User
from app.schemas.auth import TokenPairResponse


class AuthService:
    """содержит базовую auth логику"""

    def __init__(self, db: Session, redis: Redis):
        self.db = db
        self.redis = redis

    def login(self, email: str, password: str) -> TokenPairResponse:
        """проверяет логин и выдает пару токенов"""
        user = self.db.scalar(select(User).where(User.email == email))
        if user is None or not verify_password(password, user.hashed_password):
            raise AppException(
                401, "invalid_credentials", "неверный email или пароль"
            )
        if not user.is_active:
            raise AppException(
                403, "inactive_user", "пользователь деактивирован"
            )

        access_token, access_data, access_ttl = create_access_token(user.id)
        refresh_token, refresh_data, refresh_ttl = create_refresh_token(
            user.id
        )
        self.redis.setex(f"access:{access_data.jti}", access_ttl, str(user.id))
        self.redis.setex(
            f"refresh:{refresh_data.jti}", refresh_ttl, str(user.id)
        )
        return TokenPairResponse(
            access_token=access_token, refresh_token=refresh_token
        )

    def refresh(self, refresh_token: str) -> TokenPairResponse:
        """обновляет пару токенов по refresh token"""
        token_data = decode_token(refresh_token, expected_type="refresh")
        redis_key = f"refresh:{token_data.jti}"
        if not self.redis.get(redis_key):
            raise AppException(401, "invalid_token", "невалидный токен")

        user = self.db.get(User, token_data.user_id)
        if user is None or not user.is_active:
            raise AppException(401, "invalid_token", "невалидный токен")

        self.redis.delete(redis_key)
        access_token, access_data, access_ttl = create_access_token(user.id)
        new_refresh_token, refresh_data, refresh_ttl = create_refresh_token(
            user.id
        )
        self.redis.setex(f"access:{access_data.jti}", access_ttl, str(user.id))
        self.redis.setex(
            f"refresh:{refresh_data.jti}", refresh_ttl, str(user.id)
        )
        return TokenPairResponse(
            access_token=access_token, refresh_token=new_refresh_token
        )

    def logout_access_token(self, access_token: str) -> None:
        """удаляет access token из redis"""
        token_data = decode_token(access_token, expected_type="access")
        removed = self.redis.delete(f"access:{token_data.jti}")
        if removed == 0:
            raise AppException(401, "invalid_token", "невалидный токен")
