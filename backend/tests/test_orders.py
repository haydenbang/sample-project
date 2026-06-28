"""Tests for the orders router, verifying the new `final_amount` field in OrderOut."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Minimal stub setup so we can import the app without real DB / heavy deps
# ---------------------------------------------------------------------------

import sys
import types

# ── stub out app packages that may not exist in the test environment ────────

def _make_module(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


# app.database
db_mod = _make_module("app.database")
db_mod.get_db = lambda: None

# app.common.deps
deps_mod = _make_module("app.common.deps")
deps_mod.require_roles = lambda *a, **kw: (lambda f: f)

# app.models
models_pkg = _make_module("app.models")

# app.models.user
user_mod = _make_module("app.models.user")


class _UserRole:
    ADMIN = "admin"
    CUSTOMER = "customer"


user_mod.UserRole = _UserRole
sys.modules["app.models.user"] = user_mod

# app.models.order
order_mod = _make_module("app.models.order")


class _OrderStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class _Order:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if not hasattr(self, "items"):
            self.items = []
        if not hasattr(self, "final_amount"):
            self.final_amount = None


order_mod.OrderStatus = _OrderStatus
order_mod.Order = _Order
sys.modules["app.models.order"] = order_mod

# app.schemas.order
schemas_pkg = _make_module("app.schemas")
schemas_order_mod = _make_module("app.schemas.order")

from pydantic import BaseModel
from typing import List, Optional


class _OrderOut(BaseModel):
    id: int
    status: str
    final_amount: int  # non-nullable int (the new field)

    class Config:
        from_attributes = True


class _OrderListOut(BaseModel):
    items: List[_OrderOut]
    total: int
    page: int
    size: int


class _OrderCreate(BaseModel):
    items: List[dict] = []


class _OrderStatusUpdate(BaseModel):
    status: str


schemas_order_mod.OrderOut = _OrderOut
schemas_order_mod.OrderListOut = _OrderListOut
schemas_order_mod.OrderCreate = _OrderCreate
schemas_order_mod.OrderStatusUpdate = _OrderStatusUpdate
sys.modules["app.schemas.order"] = schemas_order_mod

# app.services.order_service
svc_mod = _make_module("app.services.order_service")
svc_mod.create_order = lambda db, payload: None
svc_mod.transition_status = lambda db, order_id, new_status: None
sys.modules["app.services.order_service"] = svc_mod

# ---------------------------------------------------------------------------
# Now we can safely import the router module under test
# ---------------------------------------------------------------------------
from app.routers.orders import _ensure_final_amount, router  # noqa: E402

from fastapi import FastAPI

app = FastAPI()
app.include_router(router)

client = TestClient(app, raise_server_exceptions=True)


# ===========================================================================
# Helper factories
# ===========================================================================

def make_order_item(unit_price: int, quantity: int):
    item = MagicMock()
    item.unit_price = unit_price
    item.quantity = quantity
    return item


def make_order(id: int = 1, status: str = "pending", final_amount=None, items=None):
    order = _Order(id=id, status=status, final_amount=final_amount)
    order.items = items if items is not None else []
    return order


# ===========================================================================
# Unit tests for _ensure_final_amount helper
# ===========================================================================

class TestEnsureFinalAmount:
    def test_returns_existing_final_amount_when_set(self):
        order = make_order(final_amount=500)
        result = _ensure_final_amount(order)
        assert result.final_amount == 500

    def test_computes_from_items_when_none(self):
        items = [make_order_item(100, 2), make_order_item(50, 3)]
        order = make_order(final_amount=None, items=items)
        result = _ensure_final_amount(order)
        # 100*2 + 50*3 = 200 + 150 = 350
        assert result.final_amount == 350

    def test_zero_when_no_items_and_none(self):
        order = make_order(final_amount=None, items=[])
        result = _ensure_final_amount(order)
        assert result.final_amount == 0

    def test_returns_same_order_object(self):
        order = make_order(final_amount=99)
        result = _ensure_final_amount(order)
        assert result is order

    def test_final_amount_is_int(self):
        items = [make_order_item(33, 3)]
        order = make_order(final_amount=None, items=items)
        result = _ensure_final_amount(order)
        assert isinstance(result.final_amount, int)

    def test_does_not_overwrite_zero_final_amount(self):
        """final_amount=0 is falsy but should not be overwritten (it is not None)."""
        items = [make_order_item(100, 1)]  # would compute 100 if overwritten
        order = make_order(final_amount=0, items=items)
        result = _ensure_final_amount(order)
        assert result.final_amount == 0

    def test_single_item(self):
        items = [make_order_item(250, 4)]
        order = make_order(final_amount=None, items=items)
        result = _ensure_final_amount(order)
        assert result.final_amount == 1000


# ===========================================================================
# Schema-level tests for OrderOut
# ===========================================================================

class TestOrderOutSchema:
    def test_valid_order_out_with_final_amount(self):
        data = {"id": 1, "status": "pending", "final_amount": 300}
        obj = _OrderOut(**data)
        assert obj.final_amount == 300
        assert obj.id == 1
        assert obj.status == "pending"

    def test_missing_final_amount_raises_validation_error(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _OrderOut(id=1, status="pending")  # final_amount missing

    def test_none_final_amount_raises_validation_error(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _OrderOut(id=1, status="pending", final_amount=None)

    def test_string_final_amount_raises_validation_error(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _OrderOut(id=1, status="pending", final_amount="not-an-int")

    def test_float_is_coerced_to_int(self):
        """Pydantic v2 coerces float to int for int fields."""
        obj = _OrderOut(id=1, status="pending", final_amount=150.9)
        assert isinstance(obj.final_amount, int)

    def test_zero_is_valid_final_amount(self):
        obj = _OrderOut(id=1, status="pending", final_amount=0)
        assert obj.final_amount == 0

    def test_negative_final_amount_is_accepted_as_int(self):
        """Pydantic does not restrict negative unless we add a validator."""
        obj = _OrderOut(id=1, status="pending", final_amount=-10)
        assert obj.final_amount == -10

    def test_serialization_includes_final_amount(self):
        obj = _OrderOut(id=2, status="confirmed", final_amount=500)
        dumped = obj.model_dump()
        assert "final_amount" in dumped
        assert dumped["final_amount"] == 500


# ===========================================================================
# Integration / router-level tests
# ===========================================================================

class TestListOrdersEndpoint:
    """GET /api/orders — verifies final_amount is present in response."""

    def _mock_db(self):
        db = MagicMock(spec=Session)
        return db

    def test_list_orders_includes_final_amount(self):
        order = make_order(id=1, status="pending", final_amount=400)
        db = self._mock_db()
        query_mock = MagicMock()
        query_mock.count.return_value = 1
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.offset.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.all.return_value = [order]
        db.query.return_value = query_mock

        with patch("app.routers.orders.get_db", return_value=db):
            with patch("app.database.get_db", return_value=db):
                response = client.get("/api/orders", params={})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["final_amount"] == 400

    def test_list_orders_computes_final_amount_when_none(self):
        items = [make_order_item(200, 1), make_order_item(50, 2)]
        order = make_order(id=2, status="pending", final_amount=None, items=items)

        db = self._mock_db()
        query_mock = MagicMock()
        query_mock.count.return_value = 1
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.offset.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.all.return_value = [order]
        db.query.return_value = query_mock

        with patch("app.routers.orders.get_db", return_value=db):
            with patch("app.database.get_db", return_value=db):
                response = client.get("/api/orders")
        assert response.status_code == 200
        data = response.json()
        # 200*1 + 50*2 = 300
        assert data["items"][0]["final_amount"] == 300

    def test_list_orders_final_amount_zero_when_no_items_and_none(self):
        order = make_order(id=3, status="pending", final_amount=None, items=[])

        db = self._mock_db()
        query_mock = MagicMock()
        query_mock.count.return_value = 1
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.offset.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.all.return_value = [order]
        db.query.return_value = query_mock

        with patch("app.routers.orders.get_db", return_value=db):
            with patch("app.database.get_db", return_value=db):
                response = client.get("/api/orders")
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["final_amount"] == 0

    def test_list_orders_multiple_orders_all_have_final_amount(self):
        o1 = make_order(id=1, status="pending", final_amount=100)
        o2 = make_order(id=2, status="confirmed", final_amount=200)
        o3 = make_order(id=3, status="pending", final_amount=None,
                        items=[make_order_item(50, 2)])

        db = self._mock_db()
        query_mock = MagicMock()
        query_mock.count.return_value = 3
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.offset.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.all.return_value = [o1, o2, o3]
        db.query.return_value = query_mock

        with patch("app.routers.orders.get_db", return_value=db):
            with patch("app.database.get_db", return_value=db):
                response = client.get("/api/orders")
        assert response.status_code == 200
        data = response.json()
        amounts = [i["final_amount"] for i in data["items"]]
        assert amounts == [100, 200, 100]  # 50*2=100 for o3


# ===========================================================================
# Backward-incompatibility / regression tests
# ===========================================================================

class TestBackwardIncompatibility:
    """These tests confirm that the OLD behaviour (no final_amount) now fails
    at the schema level, documenting the breaking change."""

    def test_old_order_without_final_amount_fails_schema(self):
        """Before the change, OrderOut had no final_amount; now it is required."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            _OrderOut(id=1, status="pending")
        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "final_amount" in field_names

    def test_order_dict_missing_final_amount_fails(self):
        from pydantic import ValidationError
        old_style_dict = {"id": 1, "status": "confirmed"}
        with pytest.raises(ValidationError):
            _OrderOut(**old_style_dict)

    def test_order_with_explicit_none_final_amount_fails(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _OrderOut(id=1, status="pending", final_amount=None)

    def test_order_list_out_with_missing_final_amount_fails(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _OrderListOut(
                items=[{"id": 1, "status": "pending"}],  # missing final_amount
                total=1,
                page=1,
                size=20,
            )

    def test_ensure_final_amount_called_prevents_schema_error(self):
        """Demonstrate that _ensure_final_amount fixes the None-field issue."""
        from pydantic import ValidationError

        order = make_order(id=1, status="pending", final_amount=None,
                           items=[make_order_item(100, 3)])
        # Without fix → would fail validation
        with pytest.raises(ValidationError):
            _OrderOut(id=order.id, status=order.status, final_amount=order.final_amount)

        # With fix → succeeds
        fixed = _ensure_final_amount(order)
        obj = _OrderOut(id=fixed.id, status=fixed.status, final_amount=fixed.final_amount)
        assert obj.final_amount == 300


# ===========================================================================
# Edge-case / boundary tests
# ===========================================================================

class TestEdgeCases:
    def test_large_final_amount(self):
        obj = _OrderOut(id=1, status="pending", final_amount=999_999_999)
        assert obj.final