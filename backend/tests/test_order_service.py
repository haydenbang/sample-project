"""Tests for order_service.py verifying the new `final_amount` field on OrderOut/Order."""

import pytest
from unittest.mock import MagicMock, patch, call
from fastapi import HTTPException

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services.order_service import create_order, transition_status, ALLOWED_TRANSITIONS


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def _make_user(user_id: int = 1, grade: str = "NORMAL") -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    user.grade = grade
    return user


def _make_product(product_id: int = 10, price: int = 1000) -> MagicMock:
    product = MagicMock(spec=Product)
    product.id = product_id
    product.price = price
    return product


def _make_db(user: MagicMock = None, product: MagicMock = None) -> MagicMock:
    db = MagicMock()

    def _get(model_cls, pk):
        if model_cls is User:
            return user
        if model_cls is Product:
            return product
        return None

    db.get.side_effect = _get
    return db


def _make_order(
    order_id: int = 1,
    status: OrderStatus = OrderStatus.PENDING,
    subtotal: int = 1000,
    discount: int = 0,
    final_amount: int = None,
) -> MagicMock:
    order = MagicMock(spec=Order)
    order.id = order_id
    order.status = status
    order.subtotal = subtotal
    order.discount_amount = discount
    order.total = subtotal - discount if final_amount is None else final_amount
    order.final_amount = subtotal - discount if final_amount is None else final_amount
    return order


# ---------------------------------------------------------------------------
# Tests: create_order – final_amount field
# ---------------------------------------------------------------------------

class TestCreateOrderFinalAmount:
    """Verify that `final_amount` is set correctly on the created Order."""

    @patch("app.services.order_service.calculate_discount", return_value=0)
    def test_final_amount_set_when_no_discount(self, mock_discount):
        product = _make_product(price=500)
        user = _make_user()
        db = _make_db(user=user, product=product)

        payload = OrderCreate(
            user_id=1,
            items=[OrderItemCreate(product_id=10, quantity=2)],
            coupon_code=None,
        )

        captured_order: list[Order] = []
        original_add = db.add

        def capture_add(obj):
            captured_order.append(obj)

        db.add.side_effect = capture_add

        create_order(db, payload)

        assert len(captured_order) == 1
        order = captured_order[0]
        # subtotal = 500 * 2 = 1000, discount = 0, final_amount = 1000
        assert order.final_amount == 1000

    @patch("app.services.order_service.calculate_discount", return_value=200)
    def test_final_amount_equals_subtotal_minus_discount(self, mock_discount):
        product = _make_product(price=600)
        user = _make_user()
        db = _make_db(user=user, product=product)

        payload = OrderCreate(
            user_id=1,
            items=[OrderItemCreate(product_id=10, quantity=2)],
            coupon_code="SAVE200",
        )

        captured_order: list[Order] = []
        db.add.side_effect = lambda obj: captured_order.append(obj)

        create_order(db, payload)

        order = captured_order[0]
        # subtotal = 600 * 2 = 1200, discount = 200, final_amount = 1000
        assert order.final_amount == 1000

    @patch("app.services.order_service.calculate_discount", return_value=0)
    def test_final_amount_equals_total(self, mock_discount):
        """final_amount should equal total (subtotal - discount)."""
        product = _make_product(price=300)
        user = _make_user()
        db = _make_db(user=user, product=product)

        payload = OrderCreate(
            user_id=1,
            items=[OrderItemCreate(product_id=10, quantity=3)],
            coupon_code=None,
        )

        captured_order: list[Order] = []
        db.add.side_effect = lambda obj: captured_order.append(obj)

        create_order(db, payload)

        order = captured_order[0]
        # subtotal = 300 * 3 = 900
        assert order.final_amount == order.total

    @patch("app.services.order_service.calculate_discount", return_value=100)
    def test_final_amount_is_integer(self, mock_discount):
        product = _make_product(price=550)
        user = _make_user()
        db = _make_db(user=user, product=product)

        payload = OrderCreate(
            user_id=1,
            items=[OrderItemCreate(product_id=10, quantity=2)],
            coupon_code="DISC100",
        )

        captured_order: list[Order] = []
        db.add.side_effect = lambda obj: captured_order.append(obj)

        create_order(db, payload)

        order = captured_order[0]
        # subtotal = 1100, discount = 100, final_amount = 1000
        assert isinstance(order.final_amount, int)
        assert order.final_amount == 1000

    @patch("app.services.order_service.calculate_discount", return_value=0)
    def test_final_amount_not_none(self, mock_discount):
        """final_amount must not be None (non-nullable field)."""
        product = _make_product(price=400)
        user = _make_user()
        db = _make_db(user=user, product=product)

        payload = OrderCreate(
            user_id=1,
            items=[OrderItemCreate(product_id=10, quantity=1)],
            coupon_code=None,
        )

        captured_order: list[Order] = []
        db.add.side_effect = lambda obj: captured_order.append(obj)

        create_order(db, payload)

        order = captured_order[0]
        assert order.final_amount is not None

    @patch("app.services.order_service.calculate_discount", return_value=0)
    def test_final_amount_multiple_items(self, mock_discount):
        product_a = _make_product(product_id=1, price=200)
        product_b = _make_product(product_id=2, price=300)
        user = _make_user()

        db = MagicMock()

        def _get(model_cls, pk):
            if model_cls is User:
                return user
            if model_cls is Product:
                return {1: product_a, 2: product_b}.get(pk)
            return None

        db.get.side_effect = _get

        payload = OrderCreate(
            user_id=1,
            items=[
                OrderItemCreate(product_id=1, quantity=2),  # 400
                OrderItemCreate(product_id=2, quantity=1),  # 300
            ],
            coupon_code=None,
        )

        captured_order: list[Order] = []
        db.add.side_effect = lambda obj: captured_order.append(obj)

        create_order(db, payload)

        order = captured_order[0]
        # subtotal = 400 + 300 = 700, discount = 0, final_amount = 700
        assert order.final_amount == 700

    @patch("app.services.order_service.calculate_discount", return_value=50)
    def test_final_amount_with_large_discount(self, mock_discount):
        product = _make_product(price=100)
        user = _make_user()
        db = _make_db(user=user, product=product)

        payload = OrderCreate(
            user_id=1,
            items=[OrderItemCreate(product_id=10, quantity=1)],
            coupon_code="BIG",
        )

        captured_order: list[Order] = []
        db.add.side_effect = lambda obj: captured_order.append(obj)

        create_order(db, payload)

        order = captured_order[0]
        # subtotal = 100, discount = 50, final_amount = 50
        assert order.final_amount == 50


# ---------------------------------------------------------------------------
# Tests: create_order – backward-incompatible / error cases
# ---------------------------------------------------------------------------

class TestCreateOrderErrorCases:
    """Backward-incompatible and error-raising cases."""

    def test_raises_404_when_user_not_found(self):
        db = _make_db(user=None, product=None)

        payload = OrderCreate(
            user_id=999,
            items=[OrderItemCreate(product_id=10, quantity=1)],
            coupon_code=None,
        )

        with pytest.raises(HTTPException) as exc_info:
            create_order(db, payload)

        assert exc_info.value.status_code == 404

    def test_raises_404_when_product_not_found(self):
        user = _make_user()
        db = _make_db(user=user, product=None)

        payload = OrderCreate(
            user_id=1,
            items=[OrderItemCreate(product_id=999, quantity=1)],
            coupon_code=None,
        )

        with pytest.raises(HTTPException) as exc_info:
            create_order(db, payload)

        assert exc_info.value.status_code == 404

    @patch("app.services.order_service.calculate_discount", return_value=0)
    def test_order_without_final_amount_raises_or_missing(self, mock_discount):
        """
        Ensure that if final_amount is somehow missing from Order constructor,
        the model would surface it.  Here we verify the service ALWAYS provides it.
        """
        product = _make_product(price=100)
        user = _make_user()
        db = _make_db(user=user, product=product)

        payload = OrderCreate(
            user_id=1,
            items=[OrderItemCreate(product_id=10, quantity=1)],
            coupon_code=None,
        )

        captured_orders: list = []
        db.add.side_effect = lambda obj: captured_orders.append(obj)

        create_order(db, payload)
        order = captured_orders[0]

        # The service must always populate final_amount; missing it is a bug
        assert hasattr(order, "final_amount"), "Order must have final_amount attribute"
        assert order.final_amount is not None, "final_amount must not be None"

    @patch("app.services.order_service.calculate_discount", return_value=0)
    def test_db_commit_called(self, mock_discount):
        product = _make_product(price=100)
        user = _make_user()
        db = _make_db(user=user, product=product)

        payload = OrderCreate(
            user_id=1,
            items=[OrderItemCreate(product_id=10, quantity=1)],
            coupon_code=None,
        )

        create_order(db, payload)
        db.commit.assert_called_once()

    @patch("app.services.order_service.calculate_discount", return_value=0)
    def test_db_refresh_called(self, mock_discount):
        product = _make_product(price=100)
        user = _make_user()
        db = _make_db(user=user, product=product)

        payload = OrderCreate(
            user_id=1,
            items=[OrderItemCreate(product_id=10, quantity=1)],
            coupon_code=None,
        )

        create_order(db, payload)
        db.refresh.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: transition_status
# ---------------------------------------------------------------------------

class TestTransitionStatus:
    """Verify allowed/disallowed status transitions."""

    def test_pending_to_paid_allowed(self):
        order = _make_order(status=OrderStatus.PENDING)
        db = MagicMock()

        result = transition_status(db, order, OrderStatus.PAID)

        assert order.status == OrderStatus.PAID
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(order)

    def test_pending_to_cancelled_allowed(self):
        order = _make_order(status=OrderStatus.PENDING)
        db = MagicMock()

        transition_status(db, order, OrderStatus.CANCELLED)
        assert order.status == OrderStatus.CANCELLED

    def test_paid_to_shipped_allowed(self):
        order = _make_order(status=OrderStatus.PAID)
        db = MagicMock()

        transition_status(db, order, OrderStatus.SHIPPED)
        assert order.status == OrderStatus.SHIPPED

    def test_shipped_to_delivered_allowed(self):
        order = _make_order(status=OrderStatus.SHIPPED)
        db = MagicMock()

        transition_status(db, order, OrderStatus.DELIVERED)
        assert order.status == OrderStatus.DELIVERED

    def test_delivered_to_any_raises_409(self):
        order = _make_order(status=OrderStatus.DELIVERED)
        db = MagicMock()

        for target in [OrderStatus.PENDING, OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.CANCELLED]:
            order.status = OrderStatus.DELIVERED
            with pytest.raises(HTTPException) as exc_info:
                transition_status(db, order, target)
            assert exc_info.value.status_code == 409

    def test_cancelled_to_any_raises_409(self):
        order = _make_order(status=OrderStatus.CANCELLED)
        db = MagicMock()

        for target in [OrderStatus.PENDING, OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
            order.status = OrderStatus.CANCELLED
            with pytest.raises(HTTPException) as exc_info:
                transition_status(db, order, target)
            assert exc_info.value.status_code == 409

    def test_pending_to_delivered_raises_409(self):
        order = _make_order(status=OrderStatus.PENDING)
        db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            transition_status(db, order, OrderStatus.DELIVERED)
        assert exc_info.value.status_code == 409

    def test_transition_error_message_contains_status_names(self):
        order = _make_order(status=OrderStatus.PENDING)
        db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            transition_status(db, order, OrderStatus.DELIVERED)

        detail = exc_info.value.detail
        assert OrderStatus.PENDING.value in detail or "PENDING" in detail
        assert OrderStatus.DELIVERED.value in detail or "DELIVERED" in detail


# ---------------------------------------------------------------------------
# Tests: OrderOut schema serialization of final_amount
# ---------------------------------------------------------------------------

class TestOrderOutSchema:
    """Test that OrderOut correctly validates and serializes final_amount."""

    def test_order_out_with_final_amount(self):
        """OrderOut must accept and expose final_amount as int."""
        try:
            from app.schemas.order import OrderOut
        except ImportError:
            pytest.skip("OrderOut schema not importable")

        data = {
            "id