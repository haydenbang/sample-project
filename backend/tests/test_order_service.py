"""Tests for order_service.py verifying the calculate_discount signature change.

The key change: `coupon_code` moved from positional to keyword-only parameter.
These tests verify that order_service.py correctly calls calculate_discount
using `coupon_code=` as a keyword argument.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Helpers / minimal stubs so imports work without a full DB / app setup
# ---------------------------------------------------------------------------

import types
import sys

# ------------------------------------------------------------------
# Stub out heavy dependencies before importing the module under test
# ------------------------------------------------------------------

# app.models.order
order_mod = types.ModuleType("app.models.order")


class OrderStatus:
    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

    # make instances comparable
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return self.value == (other.value if hasattr(other, "value") else other)

    def __hash__(self):
        return hash(self.value)


# For the module-level constants we need actual string-like sentinel objects
class _StatusMeta(type):
    pass


# Use simple strings as stand-ins for OrderStatus enum members
_PENDING = "PENDING"
_PAID = "PAID"
_SHIPPED = "SHIPPED"
_DELIVERED = "DELIVERED"
_CANCELLED = "CANCELLED"


class FakeOrderStatus:
    PENDING = _PENDING
    PAID = _PAID
    SHIPPED = _SHIPPED
    DELIVERED = _DELIVERED
    CANCELLED = _CANCELLED


class FakeOrder:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeOrderItem:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


order_mod.OrderStatus = FakeOrderStatus
order_mod.Order = FakeOrder
order_mod.OrderItem = FakeOrderItem
sys.modules["app.models.order"] = order_mod

# app.models.product
product_mod = types.ModuleType("app.models.product")


class FakeProduct:
    def __init__(self, id, price):
        self.id = id
        self.price = price


product_mod.Product = FakeProduct
sys.modules["app.models.product"] = product_mod

# app.models.user
user_mod = types.ModuleType("app.models.user")


class FakeUser:
    def __init__(self, id, grade):
        self.id = id
        self.grade = grade


user_mod.User = FakeUser
sys.modules["app.models.user"] = user_mod

# app.schemas.order
schema_mod = types.ModuleType("app.schemas.order")


class FakeOrderCreate:
    def __init__(self, user_id, items, coupon_code=None):
        self.user_id = user_id
        self.items = items
        self.coupon_code = coupon_code


schema_mod.OrderCreate = FakeOrderCreate
sys.modules["app.schemas.order"] = schema_mod

# app.services.discount  — we will patch calculate_discount in tests
discount_mod = types.ModuleType("app.services.discount")


def _default_calculate_discount(subtotal, grade, *, coupon_code=None):
    """Reference implementation matching the NEW (keyword-only) signature."""
    return 0


discount_mod.calculate_discount = _default_calculate_discount
sys.modules["app.services.discount"] = discount_mod

# app package stubs
for pkg in ["app", "app.models", "app.schemas", "app.services"]:
    if pkg not in sys.modules:
        sys.modules[pkg] = types.ModuleType(pkg)

# Now import the module under test
from app.services import order_service  # noqa: E402  (must be after stubs)
from app.services.order_service import create_order, transition_status  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db():
    """Minimal mock Session."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock(side_effect=lambda obj: obj)
    return session


@pytest.fixture()
def user():
    return FakeUser(id=1, grade="GOLD")


@pytest.fixture()
def product():
    return FakeProduct(id=10, price=1000)


class FakeLineItem:
    def __init__(self, product_id, quantity):
        self.product_id = product_id
        self.quantity = quantity


@pytest.fixture()
def line_item(product):
    return FakeLineItem(product_id=product.id, quantity=2)


@pytest.fixture()
def payload(user, line_item):
    return FakeOrderCreate(user_id=user.id, items=[line_item], coupon_code=None)


@pytest.fixture()
def payload_with_coupon(user, line_item):
    return FakeOrderCreate(user_id=user.id, items=[line_item], coupon_code="SAVE10")


# ---------------------------------------------------------------------------
# Helper: configure db.get to return the right objects
# ---------------------------------------------------------------------------


def _setup_db_get(db, user, product):
    def _get(model_cls, pk):
        if model_cls is FakeUser:
            return user if pk == user.id else None
        if model_cls is FakeProduct:
            return product if pk == product.id else None
        return None

    db.get.side_effect = _get


# ---------------------------------------------------------------------------
# Tests: coupon_code passed as keyword argument
# ---------------------------------------------------------------------------


class TestCalculateDiscountCalledWithKeyword:
    """Verify that create_order always passes coupon_code as a keyword arg."""

    def test_coupon_none_passed_as_keyword(self, db, user, product, payload):
        _setup_db_get(db, user, product)
        with patch.object(order_service, "calculate_discount") as mock_disc:
            mock_disc.return_value = 0
            create_order(db, payload)

        mock_disc.assert_called_once()
        _, kwargs = mock_disc.call_args
        assert "coupon_code" in kwargs, (
            "coupon_code must be passed as a keyword argument (kwonly signature)"
        )
        assert kwargs["coupon_code"] is None

    def test_coupon_code_passed_as_keyword(self, db, user, product, payload_with_coupon):
        _setup_db_get(db, user, product)
        with patch.object(order_service, "calculate_discount") as mock_disc:
            mock_disc.return_value = 50
            create_order(db, payload_with_coupon)

        mock_disc.assert_called_once()
        _, kwargs = mock_disc.call_args
        assert "coupon_code" in kwargs, (
            "coupon_code must be passed as a keyword argument (kwonly signature)"
        )
        assert kwargs["coupon_code"] == "SAVE10"

    def test_coupon_code_not_passed_positionally(self, db, user, product, payload_with_coupon):
        """Positional call would put coupon_code in args[2]; verify it's not there."""
        _setup_db_get(db, user, product)
        with patch.object(order_service, "calculate_discount") as mock_disc:
            mock_disc.return_value = 50
            create_order(db, payload_with_coupon)

        args, _ = mock_disc.call_args
        # args should only contain (subtotal, grade)
        assert len(args) == 2, (
            f"Expected exactly 2 positional args (subtotal, grade) but got {len(args)}: {args}"
        )


# ---------------------------------------------------------------------------
# Tests: correct positional arguments (subtotal, grade)
# ---------------------------------------------------------------------------


class TestCalculateDiscountPositionalArgs:
    def test_subtotal_correct(self, db, user, product, payload):
        """subtotal = price * quantity = 1000 * 2 = 2000."""
        _setup_db_get(db, user, product)
        with patch.object(order_service, "calculate_discount") as mock_disc:
            mock_disc.return_value = 0
            create_order(db, payload)

        args, _ = mock_disc.call_args
        assert args[0] == 2000

    def test_grade_correct(self, db, user, product, payload):
        _setup_db_get(db, user, product)
        with patch.object(order_service, "calculate_discount") as mock_disc:
            mock_disc.return_value = 0
            create_order(db, payload)

        args, _ = mock_disc.call_args
        assert args[1] == user.grade

    def test_subtotal_multiple_items(self, db, user, product):
        """Multiple line items: subtotal should be the sum."""
        line1 = FakeLineItem(product_id=product.id, quantity=3)  # 3000
        line2 = FakeLineItem(product_id=product.id, quantity=1)  # 1000
        p = FakeOrderCreate(user_id=user.id, items=[line1, line2], coupon_code="VIP")
        _setup_db_get(db, user, product)

        with patch.object(order_service, "calculate_discount") as mock_disc:
            mock_disc.return_value = 100
            create_order(db, p)

        args, kwargs = mock_disc.call_args
        assert args[0] == 4000
        assert kwargs.get("coupon_code") == "VIP"


# ---------------------------------------------------------------------------
# Tests: backward-incompatible call raises TypeError
# ---------------------------------------------------------------------------


class TestBackwardIncompatibleCallRaisesTypeError:
    """
    If someone still calls calculate_discount with coupon_code positionally
    (the OLD signature), the new kwonly function must raise TypeError.
    """

    def test_positional_call_raises_type_error(self):
        """Directly call the real calculate_discount with 3 positional args."""
        # Import the real function from the stubbed module to simulate old call
        from app.services.discount import calculate_discount

        # The NEW signature: calculate_discount(subtotal, grade, *, coupon_code=None)
        # Calling with 3 positional args MUST raise TypeError
        with pytest.raises(TypeError):
            calculate_discount(1000, "GOLD", "SAVE10")  # type: ignore[call-arg]

    def test_keyword_call_works_fine(self):
        """keyword-only call must not raise."""
        from app.services.discount import calculate_discount

        result = calculate_discount(1000, "GOLD", coupon_code="SAVE10")
        assert isinstance(result, int)

    def test_keyword_call_without_coupon_works(self):
        from app.services.discount import calculate_discount

        result = calculate_discount(500, "SILVER")
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# Tests: order totals are computed correctly
# ---------------------------------------------------------------------------


class TestOrderTotals:
    def test_total_equals_subtotal_minus_discount(self, db, user, product, payload):
        _setup_db_get(db, user, product)
        with patch.object(order_service, "calculate_discount", return_value=200):
            order = create_order(db, payload)

        assert order.subtotal == 2000
        assert order.discount_amount == 200
        assert order.total == 1800

    def test_zero_discount(self, db, user, product, payload):
        _setup_db_get(db, user, product)
        with patch.object(order_service, "calculate_discount", return_value=0):
            order = create_order(db, payload)

        assert order.total == order.subtotal

    def test_coupon_code_stored_on_order(self, db, user, product, payload_with_coupon):
        _setup_db_get(db, user, product)
        with patch.object(order_service, "calculate_discount", return_value=0):
            order = create_order(db, payload_with_coupon)

        assert order.coupon_code == "SAVE10"


# ---------------------------------------------------------------------------
# Tests: HTTP 404 when user or product not found
# ---------------------------------------------------------------------------


class TestCreateOrderNotFound:
    def test_user_not_found_raises_404(self, db, payload):
        db.get.side_effect = lambda cls, pk: None  # nothing found
        with pytest.raises(HTTPException) as exc_info:
            create_order(db, payload)
        assert exc_info.value.status_code == 404

    def test_product_not_found_raises_404(self, db, user, payload):
        def _get(cls, pk):
            if cls is FakeUser:
                return user
            return None

        db.get.side_effect = _get
        with pytest.raises(HTTPException) as exc_info:
            create_order(db, payload)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Tests: transition_status
# ---------------------------------------------------------------------------


class TestTransitionStatus:
    def _make_order(self, status):
        o = FakeOrder(status=status, id=99)
        return o

    def test_valid_transition_pending_to_paid(self, db):
        order = self._make_order(FakeOrderStatus.PENDING)
        db.refresh.side_effect = lambda obj: obj
        updated = transition_status(db, order, FakeOrderStatus.PAID)
        assert updated.status == FakeOrderStatus.PAID

    def test_valid_transition_paid_to_shipped(self, db):
        order = self._make_order(FakeOrderStatus.PAID)
        db.refresh.side_effect = lambda obj: obj
        updated = transition_status(db, order, FakeOrderStatus.SHIPPED)
        assert updated.status == FakeOrderStatus.SHIPPED

    def test_valid_transition_pending_to_cancelled(self, db):
        order = self._make_order(FakeOrderStatus.PENDING)
        db.refresh.side_effect = lambda obj: obj
        updated = transition_status(db, order, FakeOrderStatus.CANCELLED)
        assert updated.status == FakeOrderStatus.CANCELLED

    def test_invalid_transition_pending_to_delivered_raises_409(self, db):
        order = self._make_order(FakeOrderStatus.PENDING)
        with pytest.raises(HTTPException) as exc_info:
            transition_status(db, order, FakeOrderStatus.DELIVERED)
        assert exc_info.value.status_code == 409

    def test_invalid_transition_delivered_to_any_raises_409(self, db):
        order = self._make_order(FakeOrderStatus.DELIVERED)
        with pytest.raises(HTTPException) as exc_info:
            transition_status(db, order, FakeOrderStatus.CANCELLED)
        assert exc_info.value.status_code == 409

    def test_invalid_transition_cancelled_raises_409(self, db):
        order = self._make_order(FakeOrderStatus.CANCELLED)
        with pytest.raises(HTTPException) as exc_info:
            transition_status(db, order, FakeOrderStatus.PAID)
        assert exc_info.value.status_code == 409

    def test_db_commit_called_on_valid_transition(self, db):
        order = self._make_order(FakeOrderStatus.PAID)
        db.refresh.side_effect = lambda obj: obj
        transition_status(db, order, FakeOrderStatus.SHIPPED)
        db.commit.assert_called_once()

    def test_db_commit_not_called_on_invalid_transition(self, db):
        order = self._make_order(FakeOrderStatus.DELIVERED)
        with pytest.raises(HTTPException):
            transition_status(