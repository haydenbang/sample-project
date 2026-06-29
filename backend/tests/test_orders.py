Looking at the change event, `final_amount` is being added as a non-nullable integer field to `OrderOut`. The tests that assert on the response body need to include `final_amount` in their assertions to remain consistent, and any test that checks the full response body structure won't fail due to unexpected fields (Pydantic v2 handles extra fields differently), but the main risk is that if `final_amount` is required and the API response now includes it, the assertions should account for it.

The key fix here is ensuring the test assertions cover the new `final_amount` field where appropriate, so the tests properly validate the complete response and don't have mismatches.

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

**Key changes made:**

1. **`test_create_order_calculates_total_with_grade_discount`** — Added `assert body["final_amount"] == 74100` since `final_amount` should equal `total` (74100) after all discounts are applied.

2. **`test_create_order_with_coupon`** — Added `assert body["final_amount"] == 71100` since `final_amount` should equal `total` (71100) after grade + coupon discounts.

3. **`test_valid_status_transition`** — Added `assert "final_amount" in res.json()` to verify the field is present in the status update response, without over-constraining the value (since the status change itself doesn't alter the amount).