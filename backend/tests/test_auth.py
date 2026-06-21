"""인증/인가 단위 테스트."""

from tests.conftest import auth_header


def test_login_success(client, seed_basic):
    res = client.post("/api/auth/login", json={"email": "admin@shopadmin.io", "password": "admin1234"})
    assert res.status_code == 200
    body = res.json()
    assert body["role"] == "ADMIN"
    assert body["access_token"]


def test_login_wrong_password(client, seed_basic):
    res = client.post("/api/auth/login", json={"email": "admin@shopadmin.io", "password": "wrong"})
    assert res.status_code == 401


def test_me_requires_token(client, seed_basic):
    assert client.get("/api/auth/me").status_code == 401  # 토큰 없으면 인증 실패


def test_me_returns_current_user(client, seed_basic):
    headers = auth_header(client, "admin@shopadmin.io", "admin1234")
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["email"] == "admin@shopadmin.io"


def test_viewer_cannot_create_product(client, seed_basic):
    headers = auth_header(client, "user@shopadmin.io", "user1234")
    res = client.post(
        "/api/products",
        headers=headers,
        json={"name": "X", "category": "주변기기", "price": 1000, "stock": 1},
    )
    assert res.status_code == 403
