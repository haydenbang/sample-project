"""주문 API / 주문 서비스 단위 테스트."""

from tests.conftest import auth_header


def _create_order(client, headers, seed_basic, coupon=None):
    payload = {
        "user_id": seed_basic["customer"].id,
        "items": [{"product_id": seed_basic["keyboard"].id, "quantity": 2}],
    }
    if coupon:
        payload["coupon_code"] = coupon
    return client.post("/api/orders", headers=headers, json=payload)


def test_create_order_calculates_total_with_grade_discount(client, seed_basic):
    headers = auth_header(client, "admin@shopadmin.io", "admin1234")
    res = _create_order(client, headers, seed_basic)
    assert res.status_code == 201
    body = res.json()
    # 39000 * 2 = 78000, GOLD 5% = 3900 -> total 74100
    assert body["subtotal"] == 78000
    assert body["discount_amount"] == 3900
    assert body["total"] == 74100


def test_create_order_with_coupon(client, seed_basic):
    headers = auth_header(client, "admin@shopadmin.io", "admin1234")
    res = _create_order(client, headers, seed_basic, coupon="SAVE3000")
    body = res.json()
    # GOLD 5% (3900) + SAVE3000 (3000) = 6900
    assert body["discount_amount"] == 6900
    assert body["total"] == 71100


def test_invalid_status_transition_returns_409(client, seed_basic):
    headers = auth_header(client, "admin@shopadmin.io", "admin1234")
    order_id = _create_order(client, headers, seed_basic).json()["id"]
    # PENDING -> SHIPPED 는 허용되지 않음
    res = client.patch(f"/api/orders/{order_id}/status", headers=headers, json={"status": "SHIPPED"})
    assert res.status_code == 409


def test_valid_status_transition(client, seed_basic):
    headers = auth_header(client, "admin@shopadmin.io", "admin1234")
    order_id = _create_order(client, headers, seed_basic).json()["id"]
    res = client.patch(f"/api/orders/{order_id}/status", headers=headers, json={"status": "PAID"})
    assert res.status_code == 200
    assert res.json()["status"] == "PAID"


def test_refund_after_cancel(client, seed_basic):
    """취소(CANCELLED)된 주문은 환불 완료(REFUNDED)로 전이할 수 있다.

    운영 incident 핫픽스: 결제 취소 건의 환불 완료를 표시할 상태가 없어 도입.
    order_service.ALLOWED_TRANSITIONS 에 전이 규칙이 반영되어야 통과한다.
    """
    headers = auth_header(client, "admin@shopadmin.io", "admin1234")
    order_id = _create_order(client, headers, seed_basic).json()["id"]
    client.patch(f"/api/orders/{order_id}/status", headers=headers, json={"status": "CANCELLED"})
    res = client.patch(f"/api/orders/{order_id}/status", headers=headers, json={"status": "REFUNDED"})
    assert res.status_code == 200
    assert res.json()["status"] == "REFUNDED"
