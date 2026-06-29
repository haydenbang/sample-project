"""Tests for order_service.py — verifies correct handling of the
calculate_discount signature change where `coupon_code` moved from a
positional parameter to a keyword-only parameter."""

import inspect
import types
import unittest.mock as mock
from unittest.mock import MagicMock, patch, call

import pytest
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Helpers to build lightweight fakes so we don't need a real DB / models
# ---------------------------------------------------------------------------

def _make_user(user_id=1, grade="gold"):
    user = MagicMock()
    user.id = user_id
    user.grade = grade
    return user


def _make_product(product_id=10, price=1000):
    product = MagicMock()
    product.id = product_id
    product.price = price
    return product


def _make_payload(user_id=1, coupon_code=None, items=None):
    payload = MagicMock()
    payload.user_id = user_id
    payload.coupon_code = coupon_code
    if items is None:
        line = MagicMock()
        line.product_id = 10
        line.quantity = 2
        payload.items = [line]
    else:
        payload.items = items
    return payload


def _make_db(user=None, product=None):
    db = MagicMock()
    db.get = MagicMock(side_effect=lambda model, pk: user if "User" in str(model) else product)
    return db


# ---------------------------------------------------------------------------
# Import the module under test — we mock heavy dependencies first
# ---------------------------------------------------------------------------

import sys, importlib

# We need app.models.* and app.schemas.* to import cleanly.
# Provide minimal stubs so the real service module can be imported.

def _create_stub_modules():
    for mod_name in [
        "app",
        "app.models",
        "app.models.order",
        "app.models.product",
        "app.models.user",
        "app.schemas",
        "app.schemas.order",
        "app.services",
        "app.services.discount",
        "sqlalchemy",
        "sqlalchemy.orm",
        "fastapi",
    ]:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)

    import enum

    class OrderStatus(str, enum.Enum):
        PENDING = "pending"
        PAID = "paid"
        SHIPPED = "shipped"
        DELIVERED = "delivered"
        CANCELLED = "cancelled"

    order_mod = sys.modules["app.models.order"]
    order_mod.OrderStatus = OrderStatus
    order_mod.Order = MagicMock
    order_mod.OrderItem = MagicMock

    product_mod = sys.modules["app.models.product"]
    product_mod.Product = MagicMock

    user_mod = sys.modules["app.models.user"]
    user_mod.User = MagicMock

    schemas_order = sys.modules["app.schemas.order"]
    schemas_order.OrderCreate = MagicMock

    discount_mod = sys.modules["app.services.discount"]
    discount_mod.calculate_discount = MagicMock(return_value=0)

    sqlalchemy_orm = sys.modules["sqlalchemy.orm"]
    sqlalchemy_orm.Session = MagicMock

    fastapi_mod = sys.modules["fastapi"]
    fastapi_mod.HTTPException = HTTPException

    import http
    status_mod = types.ModuleType("fastapi.status")
    status_mod.HTTP_404_NOT_FOUND = 404
    status_mod.HTTP_409_CONFLICT = 409
    sys.modules["fastapi.status"] = status_mod
    fastapi_mod.status = status_mod

    return OrderStatus


_ORDER_STATUS = _create_stub_modules()

# Now import the service
from app.services import order_service  # noqa: E402  (after stub setup)
from app.services.order_service import create_order, transition_status, ALLOWED_TRANSITIONS  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture: reset the discount mock before each test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_discount_mock():
    discount_mock = sys.modules["app.services.discount"].calculate_discount
    discount_mock.reset_mock()
    discount_mock.return_value = 0
    yield discount_mock


# ===========================================================================
# 1. Signature of calculate_discount call — coupon_code must be keyword-only
# ===========================================================================

class TestCalculateDiscountCalledWithKeywordCouponCode:
    """The service must call calculate_discount with coupon_code as a
    keyword argument (not positional) after the signature change."""

    def _run_create_order(self, coupon_code=None, discount_return=100):
        discount_mock = sys.modules["app.services.discount"].calculate_discount
        discount_mock.return_value = discount_return

        user = _make_user()
        product = _make_product(price=500)
        payload = _make_payload(coupon_code=coupon_code)

        db = MagicMock()
        db.get = MagicMock(side_effect=lambda model, pk: (
            user if "User" in repr(model) else product
        ))

        create_order(db, payload)
        return discount_mock

    def test_coupon_code_passed_as_keyword(self):
        """coupon_code must appear in kwargs, not args."""
        discount_mock = self._run_create_order(coupon_code="SAVE10")
        _, kwargs = discount_mock.call_args
        assert "coupon_code" in kwargs, (
            "calculate_discount must be called with coupon_code as a keyword argument"
        )

    def test_coupon_code_not_passed_as_third_positional_arg(self):
        """coupon_code must NOT be the third positional argument."""
        discount_mock = self._run_create_order(coupon_code="SAVE10")
        args, _ = discount_mock.call_args
        assert len(args) < 3, (
            "coupon_code should not be passed as a positional argument; "
            f"got args={args}"
        )

    def test_coupon_code_none_passed_as_keyword(self):
        """When coupon_code is None it must still be passed as a keyword arg."""
        discount_mock = self._run_create_order(coupon_code=None)
        _, kwargs = discount_mock.call_args
        assert "coupon_code" in kwargs

    def test_coupon_code_keyword_value_matches_payload(self):
        """The keyword value for coupon_code must equal payload.coupon_code."""
        discount_mock = self._run_create_order(coupon_code="HALF50")
        _, kwargs = discount_mock.call_args
        assert kwargs["coupon_code"] == "HALF50"

    def test_coupon_code_none_keyword_value_is_none(self):
        discount_mock = self._run_create_order(coupon_code=None)
        _, kwargs = discount_mock.call_args
        assert kwargs["coupon_code"] is None


# ===========================================================================
# 2. Positional-only call raises TypeError (backward-incompatible check)
# ===========================================================================

class TestPositionalCouponCodeRaisesError:
    """Directly verify that the new calculate_discount signature rejects
    positional use of coupon_code.  We construct a function with the
    *new* signature and ensure calling it positionally raises TypeError."""

    def _make_new_signature_func(self):
        """Return a function with the *new* signature (coupon_code is kwonly)."""
        from app.models.user import User  # just a stub

        def calculate_discount(subtotal: int, grade, *, coupon_code=None) -> int:  # kwonly
            return 0

        return calculate_discount

    def test_positional_coupon_code_raises_type_error(self):
        func = self._make_new_signature_func()
        with pytest.raises(TypeError):
            func(1000, "gold", "SAVE10")  # third positional → should fail

    def test_keyword_coupon_code_does_not_raise(self):
        func = self._make_new_signature_func()
        result = func(1000, "gold", coupon_code="SAVE10")
        assert result == 0

    def test_keyword_coupon_code_none_does_not_raise(self):
        func = self._make_new_signature_func()
        result = func(1000, "gold", coupon_code=None)
        assert result == 0

    def test_old_positional_signature_accepted_coupon_code_positionally(self):
        """Show that the OLD signature accepted positional coupon_code."""
        def old_calculate_discount(subtotal: int, grade, coupon_code=None) -> int:
            return 0

        # Should NOT raise with the old signature
        result = old_calculate_discount(1000, "gold", "SAVE10")
        assert result == 0


# ===========================================================================
# 3. create_order — core business logic tests
# ===========================================================================

class TestCreateOrder:

    def _db_get(self, user, product):
        """Return a db.get side_effect that returns user for User lookups."""
        from app.models.user import User as UserModel
        from app.models.product import Product as ProductModel

        def _get(model, pk):
            # Check by identity of the stub class registered in sys.modules
            if model is sys.modules["app.models.user"].User:
                return user
            if model is sys.modules["app.models.product"].Product:
                return product
            return None

        return _get

    def test_returns_order_object(self):
        user = _make_user()
        product = _make_product(price=200)
        payload = _make_payload(coupon_code=None)

        db = MagicMock()
        db.get.side_effect = self._db_get(user, product)

        order = create_order(db, payload)
        assert order is not None

    def test_discount_applied_to_total(self):
        discount_mock = sys.modules["app.services.discount"].calculate_discount
        discount_mock.return_value = 50

        user = _make_user()
        product = _make_product(price=300)
        payload = _make_payload(coupon_code="DISC50")

        db = MagicMock()
        db.get.side_effect = self._db_get(user, product)

        create_order(db, payload)
        discount_mock.assert_called_once()

    def test_calculate_discount_receives_correct_subtotal(self):
        """subtotal = price * quantity; must be passed as first positional arg."""
        discount_mock = sys.modules["app.services.discount"].calculate_discount
        discount_mock.return_value = 0

        user = _make_user()
        product = _make_product(price=400)
        line = MagicMock()
        line.product_id = product.id
        line.quantity = 3  # subtotal = 400 * 3 = 1200
        payload = _make_payload(coupon_code=None, items=[line])

        db = MagicMock()
        db.get.side_effect = self._db_get(user, product)

        create_order(db, payload)
        args, _ = discount_mock.call_args
        assert args[0] == 1200

    def test_calculate_discount_receives_user_grade_as_second_arg(self):
        discount_mock = sys.modules["app.services.discount"].calculate_discount
        discount_mock.return_value = 0

        user = _make_user(grade="platinum")
        product = _make_product()
        payload = _make_payload()

        db = MagicMock()
        db.get.side_effect = self._db_get(user, product)

        create_order(db, payload)
        args, _ = discount_mock.call_args
        assert args[1] == "platinum"

    def test_user_not_found_raises_404(self):
        db = MagicMock()
        db.get.return_value = None  # user not found
        payload = _make_payload()

        with pytest.raises(HTTPException) as exc_info:
            create_order(db, payload)
        assert exc_info.value.status_code == 404

    def test_product_not_found_raises_404(self):
        user = _make_user()

        def _get(model, pk):
            if model is sys.modules["app.models.user"].User:
                return user
            return None  # product not found

        db = MagicMock()
        db.get.side_effect = _get
        payload = _make_payload()

        with pytest.raises(HTTPException) as exc_info:
            create_order(db, payload)
        assert exc_info.value.status_code == 404

    def test_db_commit_called(self):
        user = _make_user()
        product = _make_product()
        payload = _make_payload()

        db = MagicMock()
        db.get.side_effect = self._db_get(user, product)

        create_order(db, payload)
        db.commit.assert_called_once()

    def test_db_refresh_called(self):
        user = _make_user()
        product = _make_product()
        payload = _make_payload()

        db = MagicMock()
        db.get.side_effect = self._db_get(user, product)

        create_order(db, payload)
        db.refresh.assert_called_once()


# ===========================================================================
# 4. transition_status tests
# ===========================================================================

class TestTransitionStatus:
    OrderStatus = _ORDER_STATUS

    def _make_order(self, status):
        order = MagicMock()
        order.status = status
        return order

    def test_valid_transition_pending_to_paid(self):
        order = self._make_order(self.OrderStatus.PENDING)
        db = MagicMock()
        result = transition_status(db, order, self.OrderStatus.PAID)
        assert order.status == self.OrderStatus.PAID

    def test_valid_transition_pending_to_cancelled(self):
        order = self._make_order(self.OrderStatus.PENDING)
        db = MagicMock()
        transition_status(db, order, self.OrderStatus.CANCELLED)
        assert order.status == self.OrderStatus.CANCELLED

    def test_valid_transition_paid_to_shipped(self):
        order = self._make_order(self.OrderStatus.PAID)
        db = MagicMock()
        transition_status(db, order, self.OrderStatus.SHIPPED)
        assert order.status == self.OrderStatus.SHIPPED

    def test_valid_transition_shipped_to_delivered(self):
        order = self._make_order(self.OrderStatus.SHIPPED)
        db = MagicMock()
        transition_status(db, order, self.OrderStatus.DELIVERED)
        assert order.status == self.OrderStatus.DELIVERED

    def test_invalid_transition_pending_to_delivered_raises_409(self):
        order = self._make_order(self.OrderStatus.PENDING)
        db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            transition_status(db, order, self.OrderStatus.DELIVERED)
        assert exc_info.value.status_code == 409

    def test_invalid_transition_delivered_to_cancelled_raises_409(self):
        order = self._make_order(self.OrderStatus.DELIVERED)
        db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            transition_status(db, order, self.OrderStatus.CANCELLED)
        assert exc_info.value.status_code == 409

    def test_invalid_transition_cancelled_to_paid_raises_409(self):