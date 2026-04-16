import json

from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import AppException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_session_id,
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

        session_id = create_session_id()
        return self._issue_token_pair(user, session_id=session_id)

    def refresh(self, refresh_token: str) -> TokenPairResponse:
        """обновляет пару токенов по refresh token"""
        token_data = decode_token(refresh_token, expected_type="refresh")
        session = self._get_session(token_data.session_id)
        if session is None or session["refresh_jti"] != token_data.jti:
            raise AppException(401, "invalid_token", "невалидный токен")

        user = self.db.get(User, token_data.user_id)
        if user is None or not user.is_active:
            raise AppException(401, "invalid_token", "невалидный токен")

        self._delete_session_tokens(session)
        self.redis.delete(self._session_key(token_data.session_id))
        return self._issue_token_pair(user, session_id=token_data.session_id)

    def logout_access_token(self, access_token: str) -> None:
        """завершает текущую сессию и удаляет связанные токены"""
        token_data = decode_token(access_token, expected_type="access")
        session = self._get_session(token_data.session_id)
        if session is None or session["access_jti"] != token_data.jti:
            raise AppException(401, "invalid_token", "невалидный токен")

        self._delete_session_tokens(session)
        self.redis.delete(self._session_key(token_data.session_id))

    def _issue_token_pair(
        self, user: User, session_id: str
    ) -> TokenPairResponse:
        """выпускает пару токенов и сохраняет сессию"""
        access_token, access_data, access_ttl = create_access_token(
            user.id, session_id=session_id
        )
        refresh_token, refresh_data, refresh_ttl = create_refresh_token(
            user.id, session_id=session_id
        )
        session_ttl = max(access_ttl, refresh_ttl)
        session = {
            "session_id": session_id,
            "user_id": str(user.id),
            "access_jti": access_data.jti,
            "refresh_jti": refresh_data.jti,
        }
        self.redis.setex(
            self._access_key(access_data.jti),
            access_ttl,
            access_data.session_id,
        )
        self.redis.setex(
            self._refresh_key(refresh_data.jti),
            refresh_ttl,
            refresh_data.session_id,
        )
        self.redis.setex(
            self._session_key(session_id), session_ttl, json.dumps(session)
        )
        return TokenPairResponse(
            access_token=access_token, refresh_token=refresh_token
        )

    def _get_session(self, session_id: str) -> dict[str, str] | None:
        """читает сессию из redis"""
        raw_session = self.redis.get(self._session_key(session_id))
        if raw_session is None:
            return None
        if isinstance(raw_session, bytes):
            raw_session = raw_session.decode("utf-8")
        return json.loads(raw_session)

    def _delete_session_tokens(self, session: dict[str, str]) -> None:
        """удаляет токены сессии из redis"""
        self.redis.delete(self._access_key(session["access_jti"]))
        self.redis.delete(self._refresh_key(session["refresh_jti"]))

    @staticmethod
    def _access_key(jti: str) -> str:
        """строит ключ access token"""
        return f"access:{jti}"

    @staticmethod
    def _refresh_key(jti: str) -> str:
        """строит ключ refresh token"""
        return f"refresh:{jti}"

    @staticmethod
    def _session_key(session_id: str) -> str:
        """строит ключ сессии"""
        return f"session:{session_id}"
