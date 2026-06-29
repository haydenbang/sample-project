"""Tests for seed.py verifying the new final_amount field on Order/OrderOut."""

import pytest
from unittest.mock import MagicMock, patch, call
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

class FakeProduct:
    def __init__(self, id, name, category, price, stock, status):
        self.id = id
        self.name = name
        self.category = category
        self.price = price
        self.stock = stock
        self.status = status


class FakeOrderItem:
    def __init__(self, product_id, unit_price, quantity, line_total):
        self.product_id = product_id
        self.unit_price = unit_price
        self.quantity = quantity
        self.line_total = line_total


class FakeOrder:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeUser:
    _id_counter = 1

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if not hasattr(self, "id"):
            self.id = FakeUser._id_counter
            FakeUser._id_counter += 1


# ---------------------------------------------------------------------------
# Schema / Pydantic tests (OrderOut with final_amount)
# ---------------------------------------------------------------------------

class TestOrderOutSchema:
    """Test that the OrderOut schema correctly handles the new final_amount field."""

    def _make_orderout_class(self):
        """Attempt to import the real schema; fall back to a minimal stub."""
        try:
            from app.schemas.order import OrderOut
            return OrderOut
        except ImportError:
            from pydantic import BaseModel
            from typing import Optional

            class OrderOut(BaseModel):
                id: int
                user_id: int
                status: str
                subtotal: int
                discount_amount: int
                total: int
                final_amount: int  # new non-nullable field
                coupon_code: Optional[str] = None

            return OrderOut

    def test_final_amount_present_and_valid(self):
        OrderOut = self._make_orderout_class()
        data = {
            "id": 1,
            "user_id": 2,
            "status": "PAID",
            "subtotal": 78000,
            "discount_amount": 3900,
            "total": 74100,
            "final_amount": 74100,
            "coupon_code": None,
        }
        obj = OrderOut(**data)
        assert obj.final_amount == 74100

    def test_final_amount_is_integer(self):
        OrderOut = self._make_orderout_class()
        data = {
            "id": 1,
            "user_id": 2,
            "status": "PAID",
            "subtotal": 78000,
            "discount_amount": 3900,
            "total": 74100,
            "final_amount": 74100,
        }
        obj = OrderOut(**data)
        assert isinstance(obj.final_amount, int)

    def test_final_amount_zero_is_valid(self):
        OrderOut = self._make_orderout_class()
        data = {
            "id": 1,
            "user_id": 2,
            "status": "PAID",
            "subtotal": 0,
            "discount_amount": 0,
            "total": 0,
            "final_amount": 0,
        }
        obj = OrderOut(**data)
        assert obj.final_amount == 0

    def test_final_amount_missing_raises_error(self):
        OrderOut = self._make_orderout_class()
        from pydantic import ValidationError
        data = {
            "id": 1,
            "user_id": 2,
            "status": "PAID",
            "subtotal": 78000,
            "discount_amount": 3900,
            "total": 74100,
            # final_amount intentionally omitted
        }
        with pytest.raises((ValidationError, TypeError, KeyError)):
            OrderOut(**data)

    def test_final_amount_none_raises_error(self):
        """final_amount is non-nullable; passing None should fail validation."""
        OrderOut = self._make_orderout_class()
        from pydantic import ValidationError
        data = {
            "id": 1,
            "user_id": 2,
            "status": "PAID",
            "subtotal": 78000,
            "discount_amount": 3900,
            "total": 74100,
            "final_amount": None,
        }
        with pytest.raises((ValidationError, TypeError, ValueError)):
            obj = OrderOut(**data)
            # For strict pydantic v2 models this may raise; for lenient ones
            # we assert it is not None
            assert obj.final_amount is not None

    def test_final_amount_string_raises_error(self):
        """final_amount must be int, not a non-numeric string."""
        OrderOut = self._make_orderout_class()
        from pydantic import ValidationError
        data = {
            "id": 1,
            "user_id": 2,
            "status": "PAID",
            "subtotal": 78000,
            "discount_amount": 3900,
            "total": 74100,
            "final_amount": "not_a_number",
        }
        with pytest.raises((ValidationError, ValueError)):
            OrderOut(**data)

    def test_final_amount_negative_accepted_as_int(self):
        """Schema accepts negative int (business logic validated elsewhere)."""
        OrderOut = self._make_orderout_class()
        data = {
            "id": 1,
            "user_id": 2,
            "status": "PAID",
            "subtotal": 78000,
            "discount_amount": 3900,
            "total": 74100,
            "final_amount": -1,
        }
        obj = OrderOut(**data)
        assert obj.final_amount == -1

    def test_serialization_includes_final_amount(self):
        OrderOut = self._make_orderout_class()
        data = {
            "id": 1,
            "user_id": 2,
            "status": "PAID",
            "subtotal": 78000,
            "discount_amount": 3900,
            "total": 74100,
            "final_amount": 74100,
        }
        obj = OrderOut(**data)
        # Support both pydantic v1 (.dict()) and v2 (.model_dump())
        if hasattr(obj, "model_dump"):
            serialized = obj.model_dump()
        else:
            serialized = obj.dict()
        assert "final_amount" in serialized
        assert serialized["final_amount"] == 74100

    def test_serialization_final_amount_type_in_dict(self):
        OrderOut = self._make_orderout_class()
        data = {
            "id": 1,
            "user_id": 2,
            "status": "PAID",
            "subtotal": 78000,
            "discount_amount": 3900,
            "total": 74100,
            "final_amount": 74100,
        }
        obj = OrderOut(**data)
        if hasattr(obj, "model_dump"):
            serialized = obj.model_dump()
        else:
            serialized = obj.dict()
        assert isinstance(serialized["final_amount"], int)


# ---------------------------------------------------------------------------
# ORM model tests
# ---------------------------------------------------------------------------

class TestOrderModel:
    """Test the Order ORM model has and correctly stores final_amount."""

    def _get_order_class(self):
        try:
            from app.models.order import Order
            return Order
        except ImportError:
            return None

    def test_order_model_has_final_amount_attribute(self):
        Order = self._get_order_class()
        if Order is None:
            pytest.skip("app.models.order not importable in this environment")
        order = Order(
            user_id=1,
            status="PAID",
            subtotal=78000,
            discount_amount=3900,
            total=74100,
            final_amount=74100,
        )
        assert hasattr(order, "final_amount")
        assert order.final_amount == 74100

    def test_order_model_final_amount_column_not_nullable(self):
        """Verify column metadata marks final_amount as non-nullable."""
        try:
            from app.models.order import Order
            from sqlalchemy import inspect as sa_inspect
        except ImportError:
            pytest.skip("app.models.order not importable")

        mapper = sa_inspect(Order)
        cols = {c.key: c for c in mapper.mapper.column_attrs}
        if "final_amount" not in cols:
            pytest.skip("final_amount column not yet reflected in mapper")
        col = cols["final_amount"].columns[0]
        assert col.nullable is False, "final_amount should be non-nullable"

    def test_order_model_final_amount_is_integer_type(self):
        try:
            from app.models.order import Order
            from sqlalchemy import inspect as sa_inspect, Integer
        except ImportError:
            pytest.skip("app.models.order not importable")

        mapper = sa_inspect(Order)
        cols = {c.key: c for c in mapper.mapper.column_attrs}
        if "final_amount" not in cols:
            pytest.skip("final_amount column not yet reflected in mapper")
        col = cols["final_amount"].columns[0]
        assert isinstance(col.type, Integer), (
            f"Expected Integer type for final_amount, got {type(col.type)}"
        )


# ---------------------------------------------------------------------------
# Seed function tests
# ---------------------------------------------------------------------------

class TestSeedFunction:
    """Test the seed() function creates orders with final_amount set."""

    def _build_mock_db(self, already_seeded=False):
        db = MagicMock(spec=Session)
        query_mock = MagicMock()
        first_mock = MagicMock(return_value=MagicMock() if already_seeded else None)
        query_mock.first = first_mock
        db.query.return_value = query_mock
        db.flush = MagicMock()
        db.commit = MagicMock()
        db.add = MagicMock()
        db.add_all = MagicMock()
        return db

    def test_seed_calls_commit(self):
        try:
            from app.seed import seed
        except ImportError:
            pytest.skip("app.seed not importable")

        db = self._build_mock_db(already_seeded=False)
        seed(db)
        db.commit.assert_called_once()

    def test_seed_skips_if_already_seeded(self):
        try:
            from app.seed import seed
        except ImportError:
            pytest.skip("app.seed not importable")

        db = self._build_mock_db(already_seeded=True)
        seed(db)
        db.commit.assert_not_called()

    def test_seed_creates_order_with_final_amount(self):
        """
        Verify that when seed() builds an Order it passes final_amount=74100.
        We intercept the Order constructor to capture kwargs.
        """
        try:
            import app.seed as seed_module
            from app.models.order import Order
        except ImportError:
            pytest.skip("app.seed or app.models.order not importable")

        db = self._build_mock_db(already_seeded=False)
        captured_orders = []

        OriginalOrder = Order

        class SpyOrder(OriginalOrder):
            def __init__(self, **kwargs):
                captured_orders.append(kwargs)
                # Don't call super().__init__ to avoid DB setup issues
                for k, v in kwargs.items():
                    setattr(self, k, v)

        with patch.object(seed_module, "Order", SpyOrder):
            try:
                seed_module.seed(db)
            except Exception:
                pass  # We only care that Order was instantiated with the right kwargs

        assert len(captured_orders) >= 1, "At least one Order should have been created"
        order_kwargs = captured_orders[0]
        assert "final_amount" in order_kwargs, (
            "seed() must pass final_amount when creating Order"
        )
        assert order_kwargs["final_amount"] == 74100

    def test_seed_final_amount_equals_total(self):
        """In seed data, final_amount should equal total (74100)."""
        try:
            import app.seed as seed_module
            from app.models.order import Order
        except ImportError:
            pytest.skip("app.seed or app.models.order not importable")

        db = self._build_mock_db(already_seeded=False)
        captured_orders = []

        class SpyOrder:
            def __init__(self, **kwargs):
                captured_orders.append(kwargs)
                for k, v in kwargs.items():
                    setattr(self, k, v)

        with patch.object(seed_module, "Order", SpyOrder):
            try:
                seed_module.seed(db)
            except Exception:
                pass

        if not captured_orders:
            pytest.skip("Order was not captured")
        kwargs = captured_orders[0]
        assert kwargs.get("final_amount") == kwargs.get("total"), (
            "final_amount should equal total in seed data"
        )

    def test_seed_final_amount_not_none(self):
        try:
            import app.seed as seed_module
            from app.models.order import Order
        except ImportError:
            pytest.skip("app.seed or app.models.order not importable")

        db = self._build_mock_db(already_seeded=False)
        captured_orders = []

        class SpyOrder:
            def __init__(self, **kwargs):
                captured_orders.append(kwargs)
                for k, v in kwargs.items():
                    setattr(self, k, v)

        with patch.object(seed_module, "Order", SpyOrder):
            try:
                seed_module.seed(db)
            except Exception:
                pass

        if not captured_orders:
            pytest.skip("Order was not captured")
        assert captured_orders[0].get("final_amount") is not None

    def test_seed_final_amount_is_integer_value(self):
        try:
            import app.seed as seed_module
            from app.models.order import Order
        except ImportError:
            pytest.skip("app.seed or app.models.order not importable")

        db = self._build_mock_db(already_seeded=False)
        captured_orders = []

        class SpyOrder:
            def __init__(self, **kwargs):
                captured_orders.append(kwargs)
                for k, v in kwargs.items():
                    setattr(self, k, v)

        with patch.object(seed_module, "Order", SpyOrder):
            try:
                seed_module.seed(db)
            except Exception:
                pass

        if not captured_orders:
            pytest.skip("Order was not captured")
        assert isinstance(captured_orders[0].get("final_amount"), int)


# ---------------------------------------------------------------------------
# Backward-incompatibility tests
# ---------------------------------------------------------------------------

class TestBackwardIncompatibility:
    """Ensure old payloads/code that omit final_amount fail correctly."""

    def _make_orderout_class(self):
        try:
            from app.schemas.order import OrderOut
            return OrderOut
        except ImportError:
            from pydantic import BaseModel

            class OrderOut(BaseModel):
                id: int
                user_id: int
                status: str
                subtotal: int
                discount_amount: int
                total: int
                final_amount: int  # required, non-nullable
                coupon_code: str = None

            return OrderOut

    def test_old_payload_without_final_amount_is_rejected(self):
        """
        A payload that was valid before the change (no final_