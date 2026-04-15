from __future__ import annotations

from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db, get_redis
from app.core.security import hash_password
from app.db.models import Base, LeaveRequest, User
from app.main import app


class FakeRedis:
    """минимальная in memory замена redis для тестов"""

    def __init__(self):
        self.storage: dict[str, str] = {}

    def setex(self, key: str, _: int, value: str) -> bool:
        self.storage[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self.storage.get(key)

    def delete(self, key: str) -> int:
        existed = key in self.storage
        self.storage.pop(key, None)
        return int(existed)


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture()
def client(
    session: Session, fake_redis: FakeRedis
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield session

    def override_get_redis() -> FakeRedis:
        return fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_user(session: Session) -> User:
    user = User(
        email="admin@example.com",
        username="admin",
        hashed_password=hash_password("admin123"),
        is_active=True,
        is_admin=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture()
def regular_user(session: Session) -> User:
    user = User(
        email="user@example.com",
        username="user",
        hashed_password=hash_password("user123"),
        is_active=True,
        is_admin=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture()
def another_user(session: Session) -> User:
    user = User(
        email="other@example.com",
        username="other",
        hashed_password=hash_password("other123"),
        is_active=True,
        is_admin=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture()
def approved_request(
    session: Session, regular_user: User, admin_user: User
) -> LeaveRequest:
    leave_request = LeaveRequest(
        user_id=regular_user.id,
        start_date=date(2026, 5, 10),
        end_date=date(2026, 5, 12),
        reason="trip",
        status="approved",
        processed_by_id=admin_user.id,
    )
    session.add(leave_request)
    session.commit()
    session.refresh(leave_request)
    return leave_request


def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/jwt/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()

