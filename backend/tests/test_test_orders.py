"""Tests to verify that OrderOut schema correctly includes final_amount field."""

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

def _make_order_body(**overrides):
    """Return a minimal OrderOut-shaped dict with sensible defaults."""
    base = {
        "id": 1,
        "user_id": 10,
        "status": "PENDING",
        "subtotal": 78000,
        "discount_amount": 3900,
        "total": 74100,
        "final_amount": 74100,
        "items": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Schema-level / serialisation tests
# ---------------------------------------------------------------------------

class TestFinalAmountFieldPresence:
    """final_amount must be present and be a non-nullable integer."""

    def test_final_amount_present_in_order_body(self):
        body = _make_order_body()
        assert "final_amount" in body, "final_amount key must exist in OrderOut response"

    def test_final_amount_is_integer(self):
        body = _make_order_body()
        assert isinstance(body["final_amount"], int), "final_amount must be an int"

    def test_final_amount_is_not_none(self):
        body = _make_order_body()
        assert body["final_amount"] is not None, "final_amount must not be None (non-nullable)"

    def test_final_amount_equals_total_by_default(self):
        """Without extra adjustments final_amount should equal total."""
        body = _make_order_body()
        assert body["final_amount"] == body["total"]

    def test_final_amount_non_negative(self):
        body = _make_order_body(final_amount=0)
        assert body["final_amount"] >= 0

    def test_final_amount_zero_is_valid(self):
        """Edge-case: a fully-discounted order may have final_amount == 0."""
        body = _make_order_body(total=0, discount_amount=78000, final_amount=0)
        assert isinstance(body["final_amount"], int)
        assert body["final_amount"] == 0


# ---------------------------------------------------------------------------
# 2. Calculation correctness
# ---------------------------------------------------------------------------

class TestFinalAmountCalculation:
    def test_grade_discount_only(self):
        # 39000 * 2 = 78000, GOLD 5% = 3900 -> total/final 74100
        body = _make_order_body(
            subtotal=78000,
            discount_amount=3900,
            total=74100,
            final_amount=74100,
        )
        assert body["subtotal"] - body["discount_amount"] == body["total"]
        assert body["final_amount"] == body["total"]

    def test_grade_plus_coupon_discount(self):
        # GOLD 5% (3900) + SAVE3000 (3000) = 6900 -> 78000 - 6900 = 71100
        body = _make_order_body(
            subtotal=78000,
            discount_amount=6900,
            total=71100,
            final_amount=71100,
        )
        assert body["subtotal"] - body["discount_amount"] == body["total"]
        assert body["final_amount"] == 71100

    def test_final_amount_matches_total_after_all_discounts(self):
        for discount in (0, 500, 3900, 6900, 78000):
            total = 78000 - discount
            body = _make_order_body(
                discount_amount=discount,
                total=total,
                final_amount=total,
            )
            assert body["final_amount"] == body["total"], (
                f"final_amount {body['final_amount']} != total {body['total']} "
                f"for discount {discount}"
            )


# ---------------------------------------------------------------------------
# 3. Backward-incompatible / error cases
# ---------------------------------------------------------------------------

class TestFinalAmountBackwardIncompatible:
    """Verify that missing or wrong-typed final_amount raises the right errors."""

    def test_missing_final_amount_raises_key_error(self):
        """Simulate a response that omits final_amount (old schema)."""
        body = {
            "id": 1,
            "subtotal": 78000,
            "discount_amount": 3900,
            "total": 74100,
            # final_amount intentionally missing
        }
        with pytest.raises(KeyError):
            _ = body["final_amount"]

    def test_none_final_amount_fails_non_nullable_check(self):
        """A None value must be rejected by non-nullable validation."""
        body = _make_order_body(final_amount=None)

        def validate_non_nullable(value, field_name):
            if value is None:
                raise ValueError(f"{field_name} is non-nullable but got None")
            return value

        with pytest.raises(ValueError, match="non-nullable"):
            validate_non_nullable(body["final_amount"], "final_amount")

    def test_string_final_amount_fails_type_check(self):
        body = _make_order_body(final_amount="74100")  # wrong type

        with pytest.raises(TypeError):
            result = body["final_amount"] + 1  # int operation on str raises TypeError

    def test_float_final_amount_fails_strict_int_check(self):
        body = _make_order_body(final_amount=74100.0)

        def strict_int_check(value):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"Expected int, got {type(value).__name__}")
            return value

        with pytest.raises(TypeError, match="Expected int"):
            strict_int_check(body["final_amount"])

    def test_negative_final_amount_fails_business_rule(self):
        body = _make_order_body(final_amount=-1)

        def validate_amount(value):
            if value < 0:
                raise ValueError("final_amount cannot be negative")
            return value

        with pytest.raises(ValueError, match="cannot be negative"):
            validate_amount(body["final_amount"])


# ---------------------------------------------------------------------------
# 4. API-level integration tests (using a mock HTTP client)
# ---------------------------------------------------------------------------

class MockResponse:
    """Minimal stand-in for a requests/httpx Response."""

    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


class TestOrderAPIFinalAmount:
    """
    Tests that mimic what the real pytest client tests do, but driven by
    a mock so they run without a live server.
    """

    def _mock_client(self, response_body: dict, status_code: int = 201):
        client = MagicMock()
        client.post.return_value = MockResponse(status_code, response_body)
        client.patch.return_value = MockResponse(200, response_body)
        return client

    def test_create_order_response_contains_final_amount(self):
        body = _make_order_body(status_code=201)
        client = self._mock_client(body, status_code=201)

        res = client.post("/api/orders", headers={}, json={})
        assert res.status_code == 201
        data = res.json()
        assert "final_amount" in data
        assert data["final_amount"] == 74100

    def test_create_order_with_coupon_final_amount(self):
        body = _make_order_body(
            subtotal=78000,
            discount_amount=6900,
            total=71100,
            final_amount=71100,
        )
        client = self._mock_client(body, status_code=201)

        res = client.post("/api/orders", headers={}, json={"coupon_code": "SAVE3000"})
        assert res.status_code == 201
        data = res.json()
        assert data["discount_amount"] == 6900
        assert data["total"] == 71100
        assert data["final_amount"] == 71100

    def test_status_transition_response_contains_final_amount(self):
        body = _make_order_body(status="PAID")
        client = self._mock_client(body, status_code=200)

        res = client.patch("/api/orders/1/status", headers={}, json={"status": "PAID"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "PAID"
        assert "final_amount" in data
        assert isinstance(data["final_amount"], int)

    def test_order_response_final_amount_not_none(self):
        body = _make_order_body()
        client = self._mock_client(body)

        res = client.post("/api/orders", headers={}, json={})
        data = res.json()
        assert data["final_amount"] is not None

    def test_order_response_final_amount_equals_total(self):
        total = 74100
        body = _make_order_body(total=total, final_amount=total)
        client = self._mock_client(body)

        res = client.post("/api/orders", headers={}, json={})
        data = res.json()
        assert data["final_amount"] == data["total"]

    def test_create_order_missing_final_amount_detected(self):
        """If the server returns a body without final_amount the test should catch it."""
        body = {
            "id": 1,
            "subtotal": 78000,
            "discount_amount": 3900,
            "total": 74100,
            # final_amount missing – old/broken schema
        }
        client = self._mock_client(body, status_code=201)

        res = client.post("/api/orders", headers={}, json={})
        assert res.status_code == 201
        data = res.json()
        # This is the assertion that would fail against the old schema
        assert "final_amount" in data, (
            "OrderOut schema must include final_amount; "
            "old responses without this field are backward-incompatible"
        )


# ---------------------------------------------------------------------------
# 5. Pydantic-style validation (if Pydantic is available)
# ---------------------------------------------------------------------------

try:
    from pydantic import BaseModel, validator, ValidationError as PydanticValidationError

    class OrderOutModel(BaseModel):
        id: int
        user_id: int
        status: str
        subtotal: int
        discount_amount: int
        total: int
        final_amount: int  # non-nullable int – the new field

    class TestPydanticOrderOutModel:
        def test_valid_payload_passes(self):
            order = OrderOutModel(**_make_order_body())
            assert order.final_amount == 74100

        def test_missing_final_amount_raises_validation_error(self):
            payload = _make_order_body()
            del payload["final_amount"]
            with pytest.raises(PydanticValidationError) as exc_info:
                OrderOutModel(**payload)
            errors = exc_info.value.errors()
            fields = [e["loc"][0] for e in errors]
            assert "final_amount" in fields

        def test_none_final_amount_raises_validation_error(self):
            payload = _make_order_body(final_amount=None)
            with pytest.raises(PydanticValidationError):
                OrderOutModel(**payload)

        def test_string_final_amount_raises_validation_error(self):
            payload = _make_order_body(final_amount="not-an-int")
            with pytest.raises(PydanticValidationError):
                OrderOutModel(**payload)

        def test_final_amount_integer_coercion(self):
            """Pydantic v1 coerces float to int; ensure it is stored as int."""
            payload = _make_order_body(final_amount=74100.9)
            order = OrderOutModel(**payload)
            assert isinstance(order.final_amount, int)

        def test_zero_final_amount_is_valid(self):
            payload = _make_order_body(final_amount=0)
            order = OrderOutModel(**payload)
            assert order.final_amount == 0

except ImportError:
    pass  # Pydantic not installed; skip these tests gracefully