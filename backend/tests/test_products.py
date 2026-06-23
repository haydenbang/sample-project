"""상품 API 단위 테스트."""

from tests.conftest import auth_header


def test_list_products(client, seed_basic):
    res = client.get("/api/products")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_filter_by_category(client, seed_basic):
    res = client.get("/api/products", params={"category": "주변기기"})
    assert res.status_code == 200
    assert res.json()["total"] == 2


def test_create_product_as_admin(client, seed_basic):
    headers = auth_header(client, "admin@shopadmin.io", "admin1234")
    res = client.post(
        "/api/products",
        headers=headers,
        json={"name": "USB 허브", "category": "주변기기", "price": 15000, "stock": 5},
    )
    assert res.status_code == 201
    assert res.json()["status"] == "ACTIVE"


def test_update_to_zero_stock_marks_sold_out(client, seed_basic):
    headers = auth_header(client, "admin@shopadmin.io", "admin1234")
    pid = seed_basic["keyboard"].id
    res = client.put(f"/api/products/{pid}", headers=headers, json={"stock": 0})
    assert res.status_code == 200
    assert res.json()["status"] == "SOLD_OUT"


def test_create_low_stock_product_marks_low_stock(client, seed_basic):
    """재고 3개 이하로 생성하면 LOW_STOCK 상태가 된다 (요구사항 FR-PRODUCT-05)."""
    headers = auth_header(client, "admin@shopadmin.io", "admin1234")
    res = client.post(
        "/api/products",
        headers=headers,
        json={"name": "마우스 패드", "category": "주변기기", "price": 8000, "stock": 3},
    )
    assert res.status_code == 201
    assert res.json()["status"] == "LOW_STOCK"
