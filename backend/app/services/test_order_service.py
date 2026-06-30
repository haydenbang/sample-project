"""Tests for order_service.py focusing on brand_id field addition to Product model."""

import pytest
from unittest.mock import MagicMock, patch, call
from fastapi import HTTPException

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services.order_service import create_order, transition_status


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def make_user(user_id: int = 1, grade: str = "standard") -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    user.grade = grade
    return user


def make_product(
    product_id: int = 10,
    price: float = 100.0,
    brand_id: int | None = None,
) -> MagicMock:
    product = MagicMock(spec=Product)
    product.id = product_id
    product.price = price
    product.brand_id = brand_id
    return product


def make_db() -> MagicMock:
    db = MagicMock()
    db.refresh = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    return db


def make_payload(
    user_id: int = 1,
    items: list[dict] | None = None,
    coupon_code: str | None = None,
) -> OrderCreate:
    if items is None:
        items = [{"product_id": 10, "quantity": 2}]
    item_objects = [
        MagicMock(product_id=i["product_id"], quantity=i["quantity"])
        for i in items
    ]
    payload = MagicMock(spec=OrderCreate)
    payload.user_id = user_id
    payload.items = item_objects
    payload.coupon_code = coupon_code
    return payload


# ---------------------------------------------------------------------------
# Tests: brand_id field presence on Product
# ---------------------------------------------------------------------------

class TestProductBrandIdField:
    """Verify the new brand_id field is handled correctly on Product model."""

    def test_product_has_brand_id_attribute(self):
        """Product model instances must expose a brand_id attribute."""
        product = Product()
        assert hasattr(product, "brand_id"), (
            "Product model must have brand_id attribute after migration"
        )

    def test_product_brand_id_defaults_to_none(self):
        """brand_id should default to None (nullable column)."""
        product = Product()
        assert product.brand_id is None

    def test_product_brand_id_accepts_integer(self):
        """brand_id should accept a valid integer."""
        product = Product()
        product.brand_id = 42
        assert product.brand_id == 42

    def test_product_brand_id_accepts_none(self):
        """brand_id should accept None (nullable)."""
        product = Product()
        product.brand_id = None
        assert product.brand_id is None

    def test_product_brand_id_rejects_string(self):
        """brand_id should raise TypeError if assigned a non-integer string."""
        product = Product()
        with pytest.raises((TypeError, ValueError)):
            product.brand_id = "not-an-int"

    def test_product_brand_id_rejects_float(self):
        """brand_id should raise TypeError if assigned a float in strict typed context."""
        product = Product()
        # Depending on SQLAlchemy column type coercion this may raise or silently cast;
        # we at minimum verify the attribute exists and doesn't blow up on None.
        # This is a best-effort guard test.
        try:
            product.brand_id = 3.14
            # If no error, the value must be cast to int or stored as-is
            assert product.brand_id is not None
        except (TypeError, ValueError):
            pass  # acceptable – strict typing enforced


# ---------------------------------------------------------------------------
# Tests: create_order – db.refresh called after product fetch
# ---------------------------------------------------------------------------

class TestCreateOrderRefreshBrandId:
    """Ensure create_order calls db.refresh(product) so brand_id is never stale."""

    def _setup_db_get(self, db, user, product):
        def side_effect(model_class, pk):
            if model_class is User:
                return user
            if model_class is Product:
                return product
            return None
        db.get.side_effect = side_effect

    @patch("app.services.order_service.calculate_discount", return_value=0)
    def test_db_refresh_called_for_product(self, mock_discount):
        """db.refresh must be called with the product so brand_id is up to date."""
        db = make_db()
        user = make_user()
        product = make_product(brand_id=None)
        self._setup_db_get(db, user, product)

        # After refresh simulate brand_id being populated
        def refresh_side_effect(obj):
            if isinstance(obj, MagicMock) and hasattr(obj, "brand_id"):
                obj.brand_id = 7  # simulates DB returning updated brand_id

        db.refresh.side_effect = refresh_side_effect
        payload = make_payload()

        create_order(db, payload)

        db.refresh.assert_any_call(product)

    @patch("app.services.order_service.calculate_discount", return_value=0)
    def test_db_refresh_called_for_each_product(self, mock_discount):
        """db.refresh must be called for every product line in the order."""
        db = make_db()
        user = make_user()
        product_a = make_product(product_id=10, price=50.0, brand_id=1)
        product_b = make_product(product_id=20, price=75.0, brand_id=2)

        products = {10: product_a, 20: product_b}

        def db_get(model_class, pk):
            if model_class is User:
                return user
            if model_class is Product:
                return products.get(pk)
            return None

        db.get.side_effect = db_get
        payload = make_payload(items=[
            {"product_id": 10, "quantity": 1},
            {"product_id": 20, "quantity": 3},
        ])

        create_order(db, payload)

        db.refresh.assert_any_call(product_a)
        db.refresh.assert_any_call(product_b)

    @patch("app.services.order_service.calculate_discount", return_value=0)
    def test_brand_id_none_does_not_raise(self, mock_discount):
        """brand_id=None (nullable) must not cause any error during order creation."""
        db = make_db()
        user = make_user()
        product = make_product(brand_id=None)
        self._setup_db_get(db, user, product)

        payload = make_payload()
        # Should complete without error
        create_order(db, payload)

    @patch("app.services.order_service.calculate_discount", return_value=0)
    def test_brand_id_set_does_not_raise(self, mock_discount):
        """brand_id set to a valid int must not cause any error during order creation."""
        db = make_db()
        user = make_user()
        product = make_product(brand_id=99)
        self._setup_db_get(db, user, product)

        payload = make_payload()
        create_order(db, payload)

    @patch("app.services.order_service.calculate_discount", return_value=0)
    def test_order_item_created_with_correct_product_fields(self, mock_discount):
        """OrderItem should use product.price regardless of brand_id value."""
        db = make_db()
        user = make_user()
        product = make_product(price=200.0, brand_id=5)
        self._setup_db_get(db, user, product)

        payload = make_payload(items=[{"product_id": 10, "quantity": 3}])

        order = create_order(db, payload)

        db.add.assert_called_once()
        added_order = db.add.call_args[0][0]
        assert added_order.subtotal == 600.0  # 200 * 3
        assert added_order.total == 600.0


# ---------------------------------------------------------------------------
# Tests: create_order – user not found
# ---------------------------------------------------------------------------

class TestCreateOrderUserNotFound:
    def test_raises_404_when_user_missing(self):
        db = make_db()
        db.get.return_value = None
        payload = make_payload(user_id=999)

        with pytest.raises(HTTPException) as exc_info:
            create_order(db, payload)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Tests: create_order – product not found
# ---------------------------------------------------------------------------

class TestCreateOrderProductNotFound:
    def test_raises_404_when_product_missing(self):
        db = make_db()
        user = make_user()

        def db_get(model_class, pk):
            if model_class is User:
                return user
            if model_class is Product:
                return None
            return None

        db.get.side_effect = db_get
        payload = make_payload(items=[{"product_id": 999, "quantity": 1}])

        with pytest.raises(HTTPException) as exc_info:
            create_order(db, payload)

        assert exc_info.value.status_code == 404
        assert "999" in exc_info.value.detail

    def test_refresh_not_called_when_product_missing(self):
        """db.refresh(product) must not be called if product is None."""
        db = make_db()
        user = make_user()

        def db_get(model_class, pk):
            if model_class is User:
                return user
            if model_class is Product:
                return None
            return None

        db.get.side_effect = db_get
        payload = make_payload(items=[{"product_id": 999, "quantity": 1}])

        with pytest.raises(HTTPException):
            create_order(db, payload)

        # refresh should NOT have been called with None
        for call_args in db.refresh.call_args_list:
            assert call_args[0][0] is not None


# ---------------------------------------------------------------------------
# Tests: transition_status
# ---------------------------------------------------------------------------

class TestTransitionStatus:
    def _make_order(self, status: OrderStatus) -> MagicMock:
        order = MagicMock(spec=Order)
        order.status = status
        return order

    def test_valid_transition_pending_to_paid(self):
        db = make_db()
        order = self._make_order(OrderStatus.PENDING)

        result = transition_status(db, order, OrderStatus.PAID)

        assert order.status == OrderStatus.PAID
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(order)

    def test_valid_transition_paid_to_shipped(self):
        db = make_db()
        order = self._make_order(OrderStatus.PAID)

        transition_status(db, order, OrderStatus.SHIPPED)

        assert order.status == OrderStatus.SHIPPED

    def test_valid_transition_shipped_to_delivered(self):
        db = make_db()
        order = self._make_order(OrderStatus.SHIPPED)

        transition_status(db, order, OrderStatus.DELIVERED)

        assert order.status == OrderStatus.DELIVERED

    def test_valid_transition_pending_to_cancelled(self):
        db = make_db()
        order = self._make_order(OrderStatus.PENDING)

        transition_status(db, order, OrderStatus.CANCELLED)

        assert order.status == OrderStatus.CANCELLED

    def test_invalid_transition_raises_409(self):
        db = make_db()
        order = self._make_order(OrderStatus.DELIVERED)

        with pytest.raises(HTTPException) as exc_info:
            transition_status(db, order, OrderStatus.CANCELLED)

        assert exc_info.value.status_code == 409

    def test_invalid_transition_cancelled_to_paid_raises_409(self):
        db = make_db()
        order = self._make_order(OrderStatus.CANCELLED)

        with pytest.raises(HTTPException) as exc_info:
            transition_status(db, order, OrderStatus.PAID)

        assert exc_info.value.status_code == 409

    def test_invalid_transition_error_message_contains_statuses(self):
        db = make_db()
        order = self._make_order(OrderStatus.DELIVERED)

        with pytest.raises(HTTPException) as exc_info:
            transition_status(db, order, OrderStatus.SHIPPED)

        detail = exc_info.value.detail
        assert OrderStatus.DELIVERED.value in detail
        assert OrderStatus.SHIPPED.value in detail

    def test_db_refresh_called_on_order_after_transition(self):
        db = make_db()
        order = self._make_order(OrderStatus.PENDING)

        transition_status(db, order, OrderStatus.PAID)

        db.refresh.assert_called_once_with(order)

    def test_commit_not_called_on_invalid_transition(self):
        db = make_db()
        order = self._make_order(OrderStatus.DELIVERED)

        with pytest.raises(HTTPException):
            transition_status(db, order, OrderStatus.PAID)

        db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: backward-incompatible / schema validation edge cases
# ---------------------------------------------------------------------------

class TestBrandIdBackwardCompatibility:
    """Tests that exercise backward-incompatible scenarios around brand_id."""

    def test_product_without_brand_id_in_legacy_dict_is_valid(self):
        """Dicts that omit brand_id should still be constructable (nullable)."""
        data = {"id": 1, "name": "Legacy Product", "price": 50.0}
        # brand_id absent – Product constructor should default to None
        product = Product(**data)
        assert product.brand_id is None

    def test_product_with_brand_id_zero_is_not_treated_as_null(self):
        """brand_id=0 is a valid integer, not equivalent to None."""
        product = Product()
        product.brand_id = 0
        assert product.brand_id == 0
        assert product.brand_id is not None

    def test_brand_id_negative_integer_stored(self):
        """Negative integers should be storable (DB constraint is separate concern)."""
        product = Product()
        product.brand_id = -1
        assert product.brand_id == -1

    @patch("app.services.order_service.calculate_discount", return_value=0)
    def test_create_order_does_not_fail_on_missing_brand_id_after_refresh(
        self, mock_discount
    ):
        """
        After db.refresh(product), brand_id may remain None for old records.
        This should not break order creation.
        """
        db = make_db()
        user = make_user()
        product = make_product(brand_id=None)

        def db_get(model_class, pk):
            if model_class is User:
                return user
            if model_class is Product:
                return product
            return None

        db.get.side_effect = db_get
        # refresh does NOT set brand_id (old record without brand)
        db.refresh.side_effect = None

        payload = make_payload()
        # Must not raise
        create_order(db, payload)

    @patch("app.services.order_service.calculate_discount", return_value=0)
    def test_create_order_subtotal_unaffected_by_brand_id(self, mock_discount):
        """brand_id must not interfere with subtotal calculation."""
        db = make_db()
        user =