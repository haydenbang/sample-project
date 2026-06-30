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


def test_product_response_exposes_brand(client, seed_basic):
    """신규 brands 도메인 매핑(scenario/domain-mapping-brand) — 상품 응답에 brand_id 노출 필요.

    아직 ProductOut 스키마/라우터에 brand 가 전파되지 않아 실패한다(전파 대상).
    """
    res = client.get("/api/products")
    assert res.status_code == 200
    first = res.json()["items"][0]
    assert "brand_id" in first  # ProductOut 에 brand_id 추가 필요
