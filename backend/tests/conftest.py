"""pytest 공통 픽스처: 인메모리 DB와 TestClient."""

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
    platinum_customer = User(
        email="platinum@shopadmin.io",
        hashed_password=hash_password("platinum1234"),
        full_name="플래티넘회원",
        role=UserRole.VIEWER,
        grade=UserGrade.PLATINUM,
    )
    keyboard = Product(
        name="무선 키보드", category="주변기기", price=39000, stock=12, status=ProductStatus.ACTIVE
    )
    mouse = Product(
        name="무선 마우스", category="주변기기", price=25000, stock=30, status=ProductStatus.ACTIVE
    )
    db_session.add_all([admin, customer, platinum_customer, keyboard, mouse])
    db_session.commit()
    return {"admin": admin, "customer": customer, "platinum_customer": platinum_customer, "keyboard": keyboard, "mouse": mouse}


def auth_header(client, email: str, password: str) -> dict[str, str]:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
