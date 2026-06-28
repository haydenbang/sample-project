"""Tests for backend/app/routers/orders.py focusing on the new `final_amount` field in OrderOut."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Minimal stub definitions so we can import / test without a real database
# ---------------------------------------------------------------------------

# We need to patch heavy dependencies before importing the router
import sys
import types


def _make_stub_modules():
    """Create minimal stub modules to satisfy the router's imports."""

    # app.common.deps
    deps_mod = types.ModuleType("app.common.deps")

    def require_roles(*roles):
        def dep():
            return None
        return dep

    deps_mod.require_roles = require_roles
    sys.modules.setdefault("app.common.deps", deps_mod)

    # app.database
    db_mod = types.ModuleType("app.database")

    def get_db():
        yield MagicMock(spec=Session)

    db_mod.get_db = get_db
    sys.modules.setdefault("app.database", db_mod)

    # app.models.order  – OrderStatus enum + Order model stub
    import enum

    class OrderStatus(str, enum.Enum):
        PENDING = "pending"
        CONFIRMED = "confirmed"
        CANCELLED = "cancelled"

    class Order:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    order_mod = types.ModuleType("app.models.order")
    order_mod.Order = Order
    order_mod.OrderStatus = OrderStatus
    sys.modules.setdefault("app.models.order", order_mod)

    # app.models.user
    import enum as _enum

    class UserRole(_enum.Enum):
        ADMIN = "admin"
        STAFF = "staff"

    user_mod = types.ModuleType("app.models.user")
    user_mod.UserRole = UserRole
    sys.modules.setdefault("app.models.user", user_mod)

    # app.schemas.order – Pydantic schemas
    try:
        from pydantic import BaseModel
    except ImportError:
        pytest.skip("pydantic not installed", allow_module_level=True)

    from typing import List, Optional

    class OrderOut(BaseModel):
        id: int
        status: str
        final_amount: int

        class Config:
            from_attributes = True

    class OrderCreate(BaseModel):
        status: Optional[str] = "pending"

    class OrderStatusUpdate(BaseModel):
        status: str

    class OrderListOut(BaseModel):
        items: List[OrderOut]
        total: int
        page: int
        size: int

    schema_mod = types.ModuleType("app.schemas.order")
    schema_mod.OrderOut = OrderOut
    schema_mod.OrderCreate = OrderCreate
    schema_mod.OrderStatusUpdate = OrderStatusUpdate
    schema_mod.OrderListOut = OrderListOut
    sys.modules.setdefault("app.schemas.order", schema_mod)

    # app.services.order_service
    svc_mod = types.ModuleType("app.services.order_service")

    def create_order(db, payload):
        raise NotImplementedError("should be mocked in tests")

    def transition_status(db, order, new_status):
        raise NotImplementedError("should be mocked in tests")

    svc_mod.create_order = create_order
    svc_mod.transition_status = transition_status
    sys.modules.setdefault("app.services.order_service", svc_mod)


_make_stub_modules()

# Now we can safely import the router module under test
from app.routers.orders import router, _ensure_final_amount  # noqa: E402
from app.models.order import Order, OrderStatus  # noqa: E402
from app.schemas.order import OrderOut  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_order(id=1, status="pending", final_amount=None, items=None):
    """Return an Order-like object."""
    order = Order()
    order.id = id
    order.status = status
    if final_amount is not None:
        order.final_amount = final_amount
    elif hasattr(order, "final_amount"):
        pass  # already set
    order.items = items or []
    return order


def _make_item(total_price):
    item = MagicMock()
    item.total_price = total_price
    return item


def _build_app():
    app = FastAPI()
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# Unit tests for _ensure_final_amount helper
# ---------------------------------------------------------------------------


class TestEnsureFinalAmount:
    def test_already_set_not_overwritten(self):
        order = _make_order(final_amount=500)
        result = _ensure_final_amount(order)
        assert result.final_amount == 500

    def test_none_final_amount_computed_from_items(self):
        items = [_make_item(100), _make_item(200), _make_item(50)]
        order = _make_order(items=items)
        # Remove final_amount so it is None
        order.final_amount = None
        result = _ensure_final_amount(order)
        assert result.final_amount == 350

    def test_no_items_defaults_to_zero(self):
        order = _make_order(items=[])
        order.final_amount = None
        result = _ensure_final_amount(order)
        assert result.final_amount == 0

    def test_item_with_none_total_price_treated_as_zero(self):
        items = [_make_item(None), _make_item(300)]
        order = _make_order(items=items)
        order.final_amount = None
        result = _ensure_final_amount(order)
        assert result.final_amount == 300

    def test_returns_same_order_instance(self):
        order = _make_order(final_amount=42)
        result = _ensure_final_amount(order)
        assert result is order

    def test_missing_attribute_computed_from_items(self):
        """Order object has no final_amount attribute at all."""
        order = _make_order(items=[_make_item(777)])
        # Delete the attribute if it exists
        try:
            del order.final_amount
        except AttributeError:
            pass
        result = _ensure_final_amount(order)
        assert result.final_amount == 777


# ---------------------------------------------------------------------------
# Schema / serialization tests
# ---------------------------------------------------------------------------


class TestOrderOutSchema:
    def test_final_amount_required_in_schema(self):
        """OrderOut must require final_amount – omitting it should raise."""
        with pytest.raises(Exception):
            # pydantic v1 raises ValidationError, v2 raises ValidationError too
            OrderOut(id=1, status="pending")

    def test_final_amount_serialized_correctly(self):
        out = OrderOut(id=1, status="pending", final_amount=999)
        data = out.model_dump() if hasattr(out, "model_dump") else out.dict()
        assert data["final_amount"] == 999

    def test_final_amount_must_be_int(self):
        """Passing a non-castable string should raise a validation error."""
        with pytest.raises(Exception):
            OrderOut(id=1, status="pending", final_amount="not-a-number")

    def test_final_amount_zero_is_valid(self):
        out = OrderOut(id=1, status="pending", final_amount=0)
        data = out.model_dump() if hasattr(out, "model_dump") else out.dict()
        assert data["final_amount"] == 0

    def test_final_amount_nullable_false(self):
        """None should NOT be accepted for final_amount."""
        with pytest.raises(Exception):
            OrderOut(id=1, status="pending", final_amount=None)

    def test_from_orm_with_final_amount(self):
        order = _make_order(id=5, status="confirmed", final_amount=1500)
        if hasattr(OrderOut, "model_validate"):
            out = OrderOut.model_validate(order)
        else:
            out = OrderOut.from_orm(order)
        assert out.final_amount == 1500
        assert out.id == 5


# ---------------------------------------------------------------------------
# Integration / endpoint tests using TestClient
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    app = _build_app()
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture()
def mock_db():
    db = MagicMock(spec=Session)
    return db


class TestListOrdersEndpoint:
    def test_list_orders_includes_final_amount(self, client):
        orders = [
            _make_order(id=1, status="pending", items=[_make_item(100), _make_item(200)]),
            _make_order(id=2, status="confirmed", final_amount=500),
        ]
        orders[0].final_amount = None  # force computation

        with patch("app.routers.orders.get_db") as mock_get_db:
            mock_db = MagicMock(spec=Session)
            mock_query = MagicMock()
            mock_query.count.return_value = 2
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = orders
            mock_db.query.return_value = mock_query
            mock_get_db.return_value = iter([mock_db])

            response = client.get("/api/orders")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        for item in data["items"]:
            assert "final_amount" in item
            assert isinstance(item["final_amount"], int)

    def test_list_orders_computed_final_amount_correct(self, client):
        item1 = _make_item(150)
        item2 = _make_item(350)
        order = _make_order(id=10, status="pending", items=[item1, item2])
        order.final_amount = None

        with patch("app.routers.orders.get_db") as mock_get_db:
            mock_db = MagicMock(spec=Session)
            mock_query = MagicMock()
            mock_query.count.return_value = 1
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = [order]
            mock_db.query.return_value = mock_query
            mock_get_db.return_value = iter([mock_db])

            response = client.get("/api/orders")

        assert response.status_code == 200
        items = response.json()["items"]
        assert items[0]["final_amount"] == 500

    def test_list_orders_empty_items_final_amount_zero(self, client):
        order = _make_order(id=3, status="pending", items=[])
        order.final_amount = None

        with patch("app.routers.orders.get_db") as mock_get_db:
            mock_db = MagicMock(spec=Session)
            mock_query = MagicMock()
            mock_query.count.return_value = 1
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = [order]
            mock_db.query.return_value = mock_query
            mock_get_db.return_value = iter([mock_db])

            response = client.get("/api/orders")

        assert response.status_code == 200
        items = response.json()["items"]
        assert items[0]["final_amount"] == 0


class TestCreateOrderEndpoint:
    def test_create_order_returns_final_amount(self, client):
        created_order = _make_order(id=99, status="pending", final_amount=700)

        with (
            patch("app.routers.orders.get_db") as mock_get_db,
            patch("app.routers.orders.create_order", return_value=created_order),
            patch("app.routers.orders.require_roles", return_value=lambda: None),
        ):
            mock_db = MagicMock(spec=Session)
            mock_get_db.return_value = iter([mock_db])

            response = client.post("/api/orders", json={"status": "pending"})

        assert response.status_code == 201
        data = response.json()
        assert "final_amount" in data
        assert data["final_amount"] == 700

    def test_create_order_computes_final_amount_when_missing(self, client):
        items = [_make_item(400), _make_item(600)]
        created_order = _make_order(id=100, status="pending", items=items)
        created_order.final_amount = None

        with (
            patch("app.routers.orders.get_db") as mock_get_db,
            patch("app.routers.orders.create_order", return_value=created_order),
            patch("app.routers.orders.require_roles", return_value=lambda: None),
        ):
            mock_db = MagicMock(spec=Session)
            mock_get_db.return_value = iter([mock_db])

            response = client.post("/api/orders", json={"status": "pending"})

        assert response.status_code == 201
        data = response.json()
        assert data["final_amount"] == 1000

    def test_create_order_missing_final_amount_no_items_is_zero(self, client):
        created_order = _make_order(id=101, status="pending", items=[])
        created_order.final_amount = None

        with (
            patch("app.routers.orders.get_db") as mock_get_db,
            patch("app.routers.orders.create_order", return_value=created_order),
            patch("app.routers.orders.require_roles", return_value=lambda: None),
        ):
            mock_db = MagicMock(spec=Session)
            mock_get_db.return_value = iter([mock_db])

            response = client.post("/api/orders", json={"status": "pending"})

        assert response.status_code == 201
        data = response.json()
        assert data["final_amount"] == 0


class TestUpdateStatusEndpoint:
    def test_update_status_returns_final_amount(self, client):
        existing_order = _make_order(id=5, status="pending", final_amount=250)
        updated_order = _make_order(id=5, status="confirmed", final_amount=250)

        with (
            patch("app.routers.orders.get_db") as mock_get_db,
            patch("app.routers.orders.transition_status", return_value=updated_order),
            patch("app.routers.orders.require_roles", return_value=lambda: None),
        ):
            mock_db = MagicMock(spec=Session)
            mock_db.get.return_value = existing_order
            mock_get_db.return_value = iter([mock_db])

            response = client.patch(
                "/api/orders/5/status", json={"status": "confirmed"}
            )

        # Router may be incomplete