from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal


def _create_user_if_missing(
    email: str, username: str, password: str, is_admin: bool
) -> None:
    """создает пользователя если его еще нет"""
    with SessionLocal() as db:
        exists = db.scalar(select(User).where(User.email == email))
        if exists is not None:
            return
        user = User(
            email=email,
            username=username,
            hashed_password=hash_password(password),
            is_active=True,
            is_admin=is_admin,
        )
        db.add(user)
        db.commit()


def main() -> None:
    """создает demo пользователей"""
    _create_user_if_missing(
        email=settings.demo_admin_email,
        username=settings.demo_admin_username,
        password=settings.demo_admin_password,
        is_admin=True,
    )
    _create_user_if_missing(
        email=settings.demo_user_email,
        username=settings.demo_user_username,
        password=settings.demo_user_password,
        is_admin=False,
    )


if __name__ == "__main__":
    main()
