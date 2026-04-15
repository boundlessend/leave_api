from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt
from jwt import InvalidTokenError

from app.api.errors import AppException
from app.core.config import settings


@dataclass(slots=True)
class TokenData:
    user_id: int
    jti: str
    token_type: str
    exp: int


def hash_password(password: str) -> str:
    """хеширует пароль через bcrypt"""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """проверяет пароль против bcrypt хеша"""
    return bcrypt.checkpw(
        password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def _build_token(
    user_id: int, ttl_seconds: int, token_type: str
) -> tuple[str, TokenData, int]:
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    payload = {
        "sub": str(user_id),
        "jti": str(uuid4()),
        "type": token_type,
        "exp": expires_at,
    }
    token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    token_data = TokenData(
        user_id=user_id,
        jti=payload["jti"],
        token_type=token_type,
        exp=int(expires_at.timestamp()),
    )
    return token, token_data, ttl_seconds


def create_access_token(user_id: int) -> tuple[str, TokenData, int]:
    """создает access token"""
    return _build_token(
        user_id=user_id,
        ttl_seconds=settings.access_token_ttl_seconds,
        token_type="access",
    )


def create_refresh_token(user_id: int) -> tuple[str, TokenData, int]:
    """создает refresh token"""
    return _build_token(
        user_id=user_id,
        ttl_seconds=settings.refresh_token_ttl_seconds,
        token_type="refresh",
    )


def decode_token(token: str, expected_type: str) -> TokenData:
    """декодирует jwt и валидирует тип токена"""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except InvalidTokenError as exc:
        raise AppException(
            status_code=401,
            code="invalid_token",
            message="невалидный токен",
        ) from exc

    token_type = payload.get("type")
    if token_type != expected_type:
        raise AppException(
            status_code=401,
            code="invalid_token_type",
            message="неверный тип токена",
        )

    sub = payload.get("sub")
    jti = payload.get("jti")
    exp = payload.get("exp")
    if sub is None or jti is None or exp is None:
        raise AppException(
            status_code=401,
            code="invalid_token",
            message="невалидный токен",
        )

    return TokenData(
        user_id=int(sub),
        jti=str(jti),
        token_type=str(token_type),
        exp=int(exp),
    )
