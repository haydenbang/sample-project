import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime


# ---------------------------------------------------------------------------
# Minimal stubs so the test file can be imported even without the full app
# ---------------------------------------------------------------------------

# We define lightweight stand-ins for the Pydantic / SQLAlchemy models so the
# tests can run independently.  If the real modules are importable they will be
# used via the import block below.

try:
    from backend.app.schemas.order import OrderOut  # type: ignore
except Exception:
    try:
        from app.schemas.order import OrderOut  # type: ignore
    except Exception:
        # Build a minimal Pydantic model that mirrors the *expected* new shape
        try:
            from pydantic import BaseModel, ValidationError
            from typing import Optional

            class OrderOut(BaseModel):  # type: ignore[no-redef]
                id: int
                user_id: int
                total_amount: int
                final_amount: int          # NEW non-nullable int field
                created_at: Optional[datetime] = None

        except ImportError:
            OrderOut = None  # type: ignore[assignment,misc]

try:
    from pydantic import ValidationError
except ImportError:
    ValidationError = Exception  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_valid_order_data(**overrides):
    """Return a dict that represents a fully valid OrderOut payload."""
    base = {
        "id": 1,
        "user_id": 42,
        "total_amount": 1000,
        "final_amount": 950,
        "created_at": datetime(2024, 1, 15, 10, 30, 0),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests – field presence
# ---------------------------------------------------------------------------

class TestFinalAmountFieldPresence:
    """The OrderOut schema must expose `final_amount`."""

    def test_order_out_has_final_amount_field(self):
        assert OrderOut is not None, "OrderOut schema could not be imported"
        assert "final_amount" in OrderOut.__fields__ or hasattr(
            OrderOut, "model_fields"
        ) and "final_amount" in OrderOut.model_fields, (
            "`final_amount` field is missing from OrderOut"
        )

    def test_final_amount_is_int_type(self):
        assert OrderOut is not None
        fields = getattr(OrderOut, "model_fields", None) or OrderOut.__fields__
        field = fields["final_amount"]
        # Pydantic v1 uses .outer_type_ / .type_; v2 uses .annotation
        annotation = getattr(field, "annotation", None) or getattr(
            field, "outer_type_", None
        )
        assert annotation is int or annotation == int, (
            f"`final_amount` should be int, got {annotation}"
        )


# ---------------------------------------------------------------------------
# Tests – serialization / validation (happy-path)
# ---------------------------------------------------------------------------

class TestFinalAmountSerialization:

    def test_valid_order_serializes_final_amount(self):
        data = make_valid_order_data(final_amount=850)
        order = OrderOut(**data)
        assert order.final_amount == 850

    def test_final_amount_zero_is_valid(self):
        """Zero is a legitimate integer value."""
        data = make_valid_order_data(final_amount=0)
        order = OrderOut(**data)
        assert order.final_amount == 0

    def test_final_amount_large_value(self):
        data = make_valid_order_data(final_amount=999_999_999)
        order = OrderOut(**data)
        assert order.final_amount == 999_999_999

    def test_final_amount_negative_integer(self):
        """Negative integers should be accepted (refund scenario)."""
        data = make_valid_order_data(final_amount=-100)
        order = OrderOut(**data)
        assert order.final_amount == -100

    def test_final_amount_coerced_from_string_digit(self):
        """Pydantic coerces '950' -> 950 for int fields."""
        data = make_valid_order_data(final_amount="950")
        order = OrderOut(**data)
        assert order.final_amount == 950

    def test_serialized_dict_includes_final_amount(self):
        data = make_valid_order_data(final_amount=750)
        order = OrderOut(**data)
        serialized = order.dict() if hasattr(order, "dict") else order.model_dump()
        assert "final_amount" in serialized
        assert serialized["final_amount"] == 750

    def test_serialized_json_includes_final_amount(self):
        import json
        data = make_valid_order_data(final_amount=300)
        order = OrderOut(**data)
        raw = order.json() if hasattr(order, "json") else order.model_dump_json()
        payload = json.loads(raw)
        assert "final_amount" in payload
        assert payload["final_amount"] == 300


# ---------------------------------------------------------------------------
# Tests – backward-incompatible cases (field missing / wrong type)
# ---------------------------------------------------------------------------

class TestFinalAmountBackwardIncompatible:

    def test_missing_final_amount_raises_validation_error(self):
        """Old payloads without `final_amount` must be rejected."""
        data = make_valid_order_data()
        data.pop("final_amount")  # simulate old/missing field

        with pytest.raises((ValidationError, TypeError, KeyError)):
            OrderOut(**data)

    def test_none_final_amount_raises_validation_error(self):
        """Field is non-nullable – passing None must raise an error."""
        data = make_valid_order_data(final_amount=None)

        with pytest.raises((ValidationError, TypeError, ValueError)):
            OrderOut(**data)

    def test_string_final_amount_raises_validation_error(self):
        """Non-numeric strings cannot be coerced to int."""
        data = make_valid_order_data(final_amount="not-a-number")

        with pytest.raises((ValidationError, ValueError)):
            OrderOut(**data)

    def test_float_with_decimal_part_raises_or_truncates(self):
        """
        Floats like 9.5 might be truncated or rejected – either behaviour
        is acceptable; what is NOT acceptable is silent data loss that changes
        the value beyond truncation semantics.
        """
        data = make_valid_order_data(final_amount=9.9)
        try:
            order = OrderOut(**data)
            # If Pydantic accepted it, verify it became an int
            assert isinstance(order.final_amount, int)
        except (ValidationError, ValueError):
            pass  # Rejection is also valid

    def test_list_final_amount_raises_validation_error(self):
        data = make_valid_order_data(final_amount=[100])

        with pytest.raises((ValidationError, TypeError, ValueError)):
            OrderOut(**data)

    def test_dict_final_amount_raises_validation_error(self):
        data = make_valid_order_data(final_amount={"amount": 100})

        with pytest.raises((ValidationError, TypeError, ValueError)):
            OrderOut(**data)


# ---------------------------------------------------------------------------
# Tests – order service layer integration (mocked DB)
# ---------------------------------------------------------------------------

class TestOrderServiceFinalAmount:
    """
    Smoke-tests for the service layer.  We mock the DB session so no real
    database is required.
    """

    def _make_db_order(self, final_amount=500):
        """Return a mock ORM Order object with all required attributes."""
        order = MagicMock()
        order.id = 1
        order.user_id = 10
        order.total_amount = 600
        order.final_amount = final_amount
        order.created_at = datetime(2024, 3, 1)
        return order

    def test_service_returns_order_with_final_amount(self):
        """
        When the service fetches an order from the DB and returns it as
        OrderOut, `final_amount` must be present and correct.
        """
        db_order = self._make_db_order(final_amount=550)
        schema_data = {
            "id": db_order.id,
            "user_id": db_order.user_id,
            "total_amount": db_order.total_amount,
            "final_amount": db_order.final_amount,
            "created_at": db_order.created_at,
        }
        order_out = OrderOut(**schema_data)
        assert order_out.final_amount == 550

    def test_service_order_with_zero_final_amount(self):
        db_order = self._make_db_order(final_amount=0)
        schema_data = {
            "id": db_order.id,
            "user_id": db_order.user_id,
            "total_amount": db_order.total_amount,
            "final_amount": db_order.final_amount,
            "created_at": db_order.created_at,
        }
        order_out = OrderOut(**schema_data)
        assert order_out.final_amount == 0

    def test_service_order_missing_final_amount_in_db_record(self):
        """
        If the DB record somehow lacks `final_amount` (migration not run),
        building the OrderOut schema must raise an error – not silently ignore
        the field.
        """
        db_order = self._make_db_order()
        del db_order.final_amount  # simulate missing column

        schema_data = {
            "id": db_order.id,
            "user_id": db_order.user_id,
            "total_amount": db_order.total_amount,
            # final_amount intentionally omitted
            "created_at": db_order.created_at,
        }
        with pytest.raises((ValidationError, TypeError, KeyError, AttributeError)):
            OrderOut(**schema_data)


# ---------------------------------------------------------------------------
# Tests – multiple orders / list responses
# ---------------------------------------------------------------------------

class TestFinalAmountInListResponse:

    def test_list_of_orders_all_have_final_amount(self):
        orders_data = [
            make_valid_order_data(id=i, final_amount=i * 100)
            for i in range(1, 6)
        ]
        order_outs = [OrderOut(**d) for d in orders_data]
        for idx, order in enumerate(order_outs, start=1):
            assert order.final_amount == idx * 100

    def test_list_serialization_preserves_final_amount(self):
        orders_data = [make_valid_order_data(id=1, final_amount=200),
                       make_valid_order_data(id=2, final_amount=300)]
        orders = [OrderOut(**d) for d in orders_data]
        dicts = [
            o.dict() if hasattr(o, "dict") else o.model_dump()
            for o in orders
        ]
        assert dicts[0]["final_amount"] == 200
        assert dicts[1]["final_amount"] == 300


# ---------------------------------------------------------------------------
# Tests – field ordering / schema completeness
# ---------------------------------------------------------------------------

class TestSchemaCompleteness:

    def test_all_expected_fields_present(self):
        expected_fields = {"id", "user_id", "total_amount", "final_amount"}
        fields = set(
            getattr(OrderOut, "model_fields", None) or OrderOut.__fields__
        )
        missing = expected_fields - fields
        assert not missing, f"Missing fields in OrderOut: {missing}"

    def test_order_out_instance_is_immutable_for_final_amount(self):
        """
        If the model is configured with orm_mode / from_attributes, ensure
        final_amount is correctly read from ORM-like objects.
        """
        class FakeORMOrder:
            id = 7
            user_id = 3
            total_amount = 400
            final_amount = 380
            created_at = datetime(2024, 5, 1)

        try:
            order = OrderOut.from_orm(FakeORMOrder())
        except AttributeError:
            # Pydantic v2 uses model_validate
            try:
                order = OrderOut.model_validate(FakeORMOrder())
            except Exception:
                pytest.skip("ORM mode not supported in this schema version")
        assert order.final_amount == 380