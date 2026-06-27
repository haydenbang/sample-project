"""pytest 공통 픽스처: 인메모리 DB와 TestClient."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models.product import Product, ProductStatus
from app.models.user import User, UserGrade, UserRole

# 테스트 환경에서 payment_api_key가 없으면 pydantic ValidationError가 발생하므로
# 더미 키를 환경변수로 주입한다.
os.environ.setdefault("PAYMENT_API_KEY", "test-dummy-payment-api-key")


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seed_basic(db_session):
    """관리자 1명, GOLD 회원 1명, 상품 2개를 시드한다."""
    admin = User(
        email="admin@shopadmin.io",
        hashed_password=hash_password("admin1234"),
        full_name="관리자",
        role=UserRole.ADMIN,
        grade=UserGrade.VIP,
    )
    customer = User(
        email="user@shopadmin.io",
        hashed_password=hash_password("user1234"),
        full_name="홍길동",
        role=UserRole.VIEWER,
        grade=UserGrade.GOLD,
    )
    keyboard = Product(
        name="무선 키보드", category="주변기기", price=39000, stock=12, status=ProductStatus.ACTIVE
    )
    mouse = Product(
        name="무선 마우스", category="주변기기", price=25000, stock=30, status=ProductStatus.ACTIVE
    )
    db_session.add_all([admin, customer, keyboard, mouse])
    db_session.commit()
    return {"admin": admin, "customer": customer, "keyboard": keyboard, "mouse": mouse}


def auth_header(client, email: str, password: str) -> dict[str, str]:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
