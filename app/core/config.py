from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_title: str = Field(default="leave requests api", alias="APP_TITLE")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    timezone_name: str = Field(
        default="Europe/Moscow", alias="TIMEZONE_NAME"
    )
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/leave_requests",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0", alias="REDIS_URL"
    )
    jwt_secret_key: str = Field(
        default="change-me-change-me-change-me-1234", alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_ttl_seconds: int = Field(
        default=900, alias="ACCESS_TOKEN_TTL_SECONDS"
    )
    refresh_token_ttl_seconds: int = Field(
        default=604800, alias="REFRESH_TOKEN_TTL_SECONDS"
    )
    demo_admin_email: str = Field(
        default="admin@example.com", alias="DEMO_ADMIN_EMAIL"
    )
    demo_admin_username: str = Field(
        default="admin", alias="DEMO_ADMIN_USERNAME"
    )
    demo_admin_password: str = Field(
        default="admin123", alias="DEMO_ADMIN_PASSWORD"
    )
    demo_user_email: str = Field(
        default="user@example.com", alias="DEMO_USER_EMAIL"
    )
    demo_user_username: str = Field(default="user", alias="DEMO_USER_USERNAME")
    demo_user_password: str = Field(
        default="user123", alias="DEMO_USER_PASSWORD"
    )


@lru_cache
def get_settings() -> Settings:
    """возвращает кэшированные настройки"""
    return Settings()


settings = get_settings()
