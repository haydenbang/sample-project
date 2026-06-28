"""Tests for OrderOut schema with the new final_amount field."""

import pytest
from pydantic import ValidationError

from app.models.order import OrderItem, OrderItemOut, OrderOut, OrderStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_order_data(**overrides):
    """Return a dict that satisfies all required OrderOut fields."""
    base = {
        "id": 1,
        "user_id": 42,
        "status": OrderStatus.PENDING,
        "subtotal": 10000,
        "discount_amount": 500,
        "total": 9500,
        "final_amount": 9500,
        "coupon_code": None,
        "created_at": "2024-01-01T00:00:00",
    }
    base.update(overrides)
    return base


def _valid_order_item_data(**overrides):
    base = {
        "id": 1,
        "order_id": 1,
        "product_id": 10,
        "unit_price": 5000,
        "quantity": 2,
        "line_total": 10000,
    }
    base.update(overrides)
    return base


# ===========================================================================
# OrderOut – new field: final_amount
# ===========================================================================

class TestOrderOutFinalAmountPresent:
    """final_amount is accepted and round-trips correctly."""

    def test_valid_positive_final_amount(self):
        data = _valid_order_data(final_amount=9500)
        order = OrderOut(**data)
        assert order.final_amount == 9500

    def test_valid_zero_final_amount(self):
        """Zero is a valid integer (e.g. fully discounted order)."""
        data = _valid_order_data(final_amount=0)
        order = OrderOut(**data)
        assert order.final_amount == 0

    def test_final_amount_large_value(self):
        data = _valid_order_data(final_amount=9_999_999)
        order = OrderOut(**data)
        assert order.final_amount == 9_999_999

    def test_final_amount_type_is_int(self):
        data = _valid_order_data(final_amount=100)
        order = OrderOut(**data)
        assert isinstance(order.final_amount, int)

    def test_final_amount_coercion_from_string_int(self):
        """Pydantic v2 coerces '9500' → 9500 in lax mode by default."""
        data = _valid_order_data(final_amount="9500")
        order = OrderOut(**data)
        assert order.final_amount == 9500

    def test_serialization_includes_final_amount(self):
        data = _valid_order_data(final_amount=7777)
        order = OrderOut(**data)
        serialized = order.model_dump()
        assert "final_amount" in serialized
        assert serialized["final_amount"] == 7777

    def test_json_serialization_includes_final_amount(self):
        data = _valid_order_data(final_amount=3333)
        order = OrderOut(**data)
        json_str = order.model_dump_json()
        assert "final_amount" in json_str
        assert "3333" in json_str


# ===========================================================================
# Backward-incompatible cases – missing or invalid final_amount
# ===========================================================================

class TestOrderOutFinalAmountMissing:
    """Omitting final_amount must raise a ValidationError (non-nullable)."""

    def test_missing_final_amount_raises(self):
        data = _valid_order_data()
        del data["final_amount"]
        with pytest.raises(ValidationError) as exc_info:
            OrderOut(**data)
        errors = exc_info.value.errors()
        fields = [e["loc"][0] for e in errors]
        assert "final_amount" in fields

    def test_none_final_amount_raises(self):
        """None must be rejected because nullable=False."""
        data = _valid_order_data(final_amount=None)
        with pytest.raises(ValidationError) as exc_info:
            OrderOut(**data)
        errors = exc_info.value.errors()
        fields = [e["loc"][0] for e in errors]
        assert "final_amount" in fields


class TestOrderOutFinalAmountInvalidType:
    """Non-integer, non-coercible values must raise ValidationError."""

    def test_float_string_raises(self):
        data = _valid_order_data(final_amount="9.99")
        with pytest.raises(ValidationError):
            OrderOut(**data)

    def test_list_raises(self):
        data = _valid_order_data(final_amount=[100])
        with pytest.raises(ValidationError):
            OrderOut(**data)

    def test_dict_raises(self):
        data = _valid_order_data(final_amount={"amount": 100})
        with pytest.raises(ValidationError):
            OrderOut(**data)

    def test_boolean_true_coerces_to_1(self):
        """In Python bool is a subclass of int; Pydantic accepts True → 1."""
        data = _valid_order_data(final_amount=True)
        # This should NOT raise; True coerces to 1
        order = OrderOut(**data)
        assert order.final_amount == 1


# ===========================================================================
# OrderOut – other required fields still validated
# ===========================================================================

class TestOrderOutOtherFields:
    """Ensure the rest of the schema is intact after adding final_amount."""

    def test_all_required_fields_present(self):
        data = _valid_order_data()
        order = OrderOut(**data)
        assert order.id == data["id"]
        assert order.user_id == data["user_id"]
        assert order.status == OrderStatus.PENDING
        assert order.subtotal == data["subtotal"]
        assert order.discount_amount == data["discount_amount"]
        assert order.total == data["total"]

    def test_missing_id_raises(self):
        data = _valid_order_data()
        del data["id"]
        with pytest.raises(ValidationError) as exc_info:
            OrderOut(**data)
        fields = [e["loc"][0] for e in exc_info.value.errors()]
        assert "id" in fields

    def test_missing_user_id_raises(self):
        data = _valid_order_data()
        del data["user_id"]
        with pytest.raises(ValidationError) as exc_info:
            OrderOut(**data)
        fields = [e["loc"][0] for e in exc_info.value.errors()]
        assert "user_id" in fields

    def test_missing_subtotal_raises(self):
        data = _valid_order_data()
        del data["subtotal"]
        with pytest.raises(ValidationError) as exc_info:
            OrderOut(**data)
        fields = [e["loc"][0] for e in exc_info.value.errors()]
        assert "subtotal" in fields

    def test_coupon_code_optional(self):
        data = _valid_order_data(coupon_code=None)
        order = OrderOut(**data)
        assert order.coupon_code is None

    def test_coupon_code_string(self):
        data = _valid_order_data(coupon_code="SAVE10")
        order = OrderOut(**data)
        assert order.coupon_code == "SAVE10"

    def test_status_values(self):
        for status in OrderStatus:
            data = _valid_order_data(status=status)
            order = OrderOut(**data)
            assert order.status == status

    def test_invalid_status_raises(self):
        data = _valid_order_data(status="UNKNOWN_STATUS")
        with pytest.raises(ValidationError):
            OrderOut(**data)


# ===========================================================================
# OrderOut.from_attributes (ORM mode)
# ===========================================================================

class TestOrderOutFromAttributes:
    """Verify that from_attributes=True allows construction from ORM objects."""

    def test_model_config_from_attributes(self):
        assert OrderOut.model_config.get("from_attributes") is True

    def test_from_orm_like_object(self):
        """Simulate construction from an ORM-like namespace object."""
        from types import SimpleNamespace
        from datetime import datetime

        orm_obj = SimpleNamespace(
            id=5,
            user_id=10,
            status=OrderStatus.PAID,
            subtotal=20000,
            discount_amount=1000,
            total=19000,
            final_amount=19000,
            coupon_code="DISC5",
            created_at=datetime(2024, 6, 1, 12, 0, 0),
        )
        order = OrderOut.model_validate(orm_obj)
        assert order.final_amount == 19000
        assert order.id == 5
        assert order.status == OrderStatus.PAID


# ===========================================================================
# OrderItemOut – unrelated schema still works
# ===========================================================================

class TestOrderItemOut:
    """Ensure OrderItemOut is not broken by the change."""

    def test_valid_order_item(self):
        data = _valid_order_item_data()
        item = OrderItemOut(**data)
        assert item.id == 1
        assert item.line_total == 10000

    def test_missing_line_total_raises(self):
        data = _valid_order_item_data()
        del data["line_total"]
        with pytest.raises(ValidationError):
            OrderItemOut(**data)

    def test_model_config_from_attributes(self):
        assert OrderItemOut.model_config.get("from_attributes") is True


# ===========================================================================
# OrderOut field listing sanity check
# ===========================================================================

class TestOrderOutSchema:
    """Schema-level assertions."""

    def test_final_amount_in_model_fields(self):
        assert "final_amount" in OrderOut.model_fields

    def test_final_amount_field_is_required(self):
        field = OrderOut.model_fields["final_amount"]
        # Required fields have no default (default is PydanticUndefined)
        from pydantic_core import PydanticUndefinedType
        assert isinstance(field.default, PydanticUndefinedType) or field.is_required()

    def test_expected_fields_present(self):
        expected = {
            "id", "user_id", "status", "subtotal",
            "discount_amount", "total", "final_amount",
            "coupon_code", "created_at",
        }
        assert expected.issubset(set(OrderOut.model_fields.keys()))

    def test_json_schema_includes_final_amount(self):
        schema = OrderOut.model_json_schema()
        # final_amount should appear in properties
        props = schema.get("properties", {})
        assert "final_amount" in props

    def test_json_schema_final_amount_type_integer(self):
        schema = OrderOut.model_json_schema()
        props = schema.get("properties", {})
        final_amount_schema = props.get("final_amount", {})
        # Could be {"type": "integer"} directly or via anyOf
        schema_str = str(final_amount_schema)
        assert "integer" in schema_str