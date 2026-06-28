Looking at the change event, `final_amount` has been added to `OrderOut` as a non-nullable int field. The tests need to be updated to:

1. Assert on `final_amount` in response bodies where applicable
2. Ensure existing assertions still work

Based on the business logic visible in the tests (subtotal, discount_amount, total), `final_amount` likely equals `total` (the final amount after all discounts). I'll add assertions for `final_amount` in the relevant tests.

```python
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
    assert body["final_amount"] == 74100


def test_create_order_with_coupon(client, seed_basic):
    headers = auth_header(client, "admin@shopadmin.io", "admin1234")
    res = _create_order(client, headers, seed_basic, coupon="SAVE3000")
    body = res.json()
    # GOLD 5% (3900) + SAVE3000 (3000) = 6900
    assert body["discount_amount"] == 6900
    assert body["total"] == 71100
    assert body["final_amount"] == 71100


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
    assert "final_amount" in res.json()
```