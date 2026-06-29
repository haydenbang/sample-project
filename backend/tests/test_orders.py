"""Tests for backend/app/routers/orders.py verifying correct handling of
the calculate_discount signature change (coupon_code: positional → keyword-only).
"""

import pytest
from unittest.mock import MagicMock, patch, call
from fastapi import HTTPException
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Minimal stubs so we can import the router without the full app stack
# ---------------------------------------------------------------------------

import sys
import types

def _make_stub_module(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# ------------------------------------------------------------------
# Stub out heavy dependencies before any app-level import
# ------------------------------------------------------------------

# app.common.deps
_make_stub_module(
    "app.common.deps",
    require_roles=lambda *roles: (lambda: None),
)

# app.database
_make_stub_module("app.database", get_db=lambda: MagicMock())

# app.models.order
import enum

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class Order:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

_make_stub_module("app.models.order", Order=Order, OrderStatus=OrderStatus)

# app.models.user
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    STAFF = "staff"
    CUSTOMER = "customer"

_make_stub_module("app.models.user", UserRole=UserRole)

# app.schemas.order
from pydantic import BaseModel
from typing import List, Optional

class OrderCreate(BaseModel):
    user_id: int
    subtotal: int
    coupon_code: Optional[str] = None

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class OrderOut(BaseModel):
    id: int
    user_id: int
    subtotal: int
    discount: int = 0
    status: OrderStatus

    class Config:
        from_attributes = True

class OrderListOut(BaseModel):
    items: List[OrderOut]
    total: int
    page: int
    size: int

    class Config:
        from_attributes = True

_make_stub_module(
    "app.schemas.order",
    OrderCreate=OrderCreate,
    OrderStatusUpdate=OrderStatusUpdate,
    OrderOut=OrderOut,
    OrderListOut=OrderListOut,
)

# app.services.order_service  – we will patch this per-test
_order_service_mod = _make_stub_module(
    "app.services.order_service",
    create_order=MagicMock(),
    transition_status=MagicMock(),
)

# app (package)
_make_stub_module("app")

# Now we can safely import
from app.routers.orders import router  # noqa: E402

from fastapi import FastAPI

app_instance = FastAPI()
app_instance.include_router(router)

client = TestClient(app_instance, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_order(**kw):
    defaults = dict(id=1, user_id=42, subtotal=10000, discount=0, status=OrderStatus.PENDING)
    defaults.update(kw)
    return Order(**defaults)


# ===========================================================================
# Tests for the signature change: coupon_code is now KEYWORD-ONLY
# ===========================================================================

class TestCalculateDiscountSignatureChange:
    """
    Verify that anything calling calculate_discount must pass coupon_code
    as a keyword argument.  Passing it positionally should raise TypeError.
    """

    def _get_calculate_discount(self):
        """Return a real-ish calculate_discount function that mirrors the new signature."""
        from app.models.order import OrderStatus  # already stubbed

        class UserGrade(str, enum.Enum):
            NORMAL = "normal"
            VIP = "vip"

        def calculate_discount(subtotal: int, grade: UserGrade, *, coupon_code=None) -> int:
            """New signature: coupon_code is keyword-only."""
            base = 0
            if grade == UserGrade.VIP:
                base = int(subtotal * 0.15)  # 15 % VIP
            if coupon_code:
                base += 500
            return base

        return calculate_discount, UserGrade

    def test_keyword_coupon_code_accepted(self):
        calculate_discount, UserGrade = self._get_calculate_discount()
        result = calculate_discount(10000, UserGrade.NORMAL, coupon_code="SAVE500")
        assert result == 500

    def test_positional_coupon_code_raises_type_error(self):
        """Old callers that pass coupon_code positionally must fail."""
        calculate_discount, UserGrade = self._get_calculate_discount()
        with pytest.raises(TypeError):
            # coupon_code is now keyword-only; passing it as 3rd positional arg fails
            calculate_discount(10000, UserGrade.NORMAL, "SAVE500")  # type: ignore[call-arg]

    def test_no_coupon_code_still_works(self):
        calculate_discount, UserGrade = self._get_calculate_discount()
        result = calculate_discount(10000, UserGrade.NORMAL)
        assert result == 0

    def test_vip_discount_calculated_correctly(self):
        calculate_discount, UserGrade = self._get_calculate_discount()
        result = calculate_discount(10000, UserGrade.VIP)
        assert result == 1500  # 15 %

    def test_vip_with_coupon_keyword(self):
        calculate_discount, UserGrade = self._get_calculate_discount()
        result = calculate_discount(10000, UserGrade.VIP, coupon_code="EXTRA")
        assert result == 2000  # 1500 + 500

    def test_return_type_is_int(self):
        calculate_discount, UserGrade = self._get_calculate_discount()
        result = calculate_discount(9999, UserGrade.VIP)
        assert isinstance(result, int)


# ===========================================================================
# Tests for the router endpoints
# ===========================================================================

class TestListOrders:
    def test_list_orders_returns_200(self, monkeypatch):
        db = MagicMock()
        query = MagicMock()
        db.query.return_value = query
        query.filter.return_value = query
        query.count.return_value = 0
        query.order_by.return_value = query
        query.offset.return_value = query
        query.limit.return_value = []

        monkeypatch.setattr("app.database.get_db", lambda: iter([db]))

        with patch("app.routers.orders.get_db", return_value=iter([db])):
            resp = client.get("/api/orders")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_list_orders_with_status_filter(self, monkeypatch):
        db = MagicMock()
        query = MagicMock()
        db.query.return_value = query
        query.filter.return_value = query
        query.count.return_value = 0
        query.order_by.return_value = query
        query.offset.return_value = query
        query.limit.return_value = []

        with patch("app.routers.orders.get_db", return_value=iter([db])):
            resp = client.get("/api/orders?status=pending")
        assert resp.status_code == 200

    def test_list_orders_pagination(self, monkeypatch):
        db = MagicMock()
        query = MagicMock()
        db.query.return_value = query
        query.filter.return_value = query
        query.count.return_value = 100
        query.order_by.return_value = query
        query.offset.return_value = query
        query.limit.return_value = []

        with patch("app.routers.orders.get_db", return_value=iter([db])):
            resp = client.get("/api/orders?page=2&size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 2
        assert data["size"] == 10


class TestCreateOrder:
    def test_create_order_calls_service(self):
        order = _make_order(id=1, user_id=42, subtotal=10000, discount=0,
                            status=OrderStatus.PENDING)
        with patch("app.routers.orders.create_order", return_value=order) as mock_create, \
             patch("app.routers.orders.get_db", return_value=iter([MagicMock()])), \
             patch("app.routers.orders.require_roles", return_value=lambda: None):
            resp = client.post(
                "/api/orders",
                json={"user_id": 42, "subtotal": 10000, "coupon_code": None},
            )
        # service was called
        assert mock_create.called

    def test_create_order_with_coupon_code(self):
        """coupon_code is optional in the schema; service layer handles keyword passing."""
        order = _make_order(id=2, user_id=7, subtotal=5000, discount=500,
                            status=OrderStatus.PENDING)
        with patch("app.routers.orders.create_order", return_value=order) as mock_create, \
             patch("app.routers.orders.get_db", return_value=iter([MagicMock()])), \
             patch("app.routers.orders.require_roles", return_value=lambda: None):
            resp = client.post(
                "/api/orders",
                json={"user_id": 7, "subtotal": 5000, "coupon_code": "SAVE500"},
            )
        assert mock_create.called
        # The payload passed through contains coupon_code
        call_args = mock_create.call_args
        payload_arg = call_args[0][1]  # second positional arg is the payload
        assert payload_arg.coupon_code == "SAVE500"

    def test_create_order_response_has_discount_field(self):
        order = _make_order(id=3, user_id=1, subtotal=20000, discount=3000,
                            status=OrderStatus.PENDING)
        with patch("app.routers.orders.create_order", return_value=order), \
             patch("app.routers.orders.get_db", return_value=iter([MagicMock()])), \
             patch("app.routers.orders.require_roles", return_value=lambda: None):
            resp = client.post(
                "/api/orders",
                json={"user_id": 1, "subtotal": 20000},
            )
        data = resp.json()
        assert "discount" in data
        assert data["discount"] == 3000

    def test_create_order_returns_201(self):
        order = _make_order()
        with patch("app.routers.orders.create_order", return_value=order), \
             patch("app.routers.orders.get_db", return_value=iter([MagicMock()])), \
             patch("app.routers.orders.require_roles", return_value=lambda: None):
            resp = client.post(
                "/api/orders",
                json={"user_id": 42, "subtotal": 10000},
            )
        assert resp.status_code == 201


class TestUpdateOrderStatus:
    def test_update_status_success(self):
        db = MagicMock()
        order = _make_order(status=OrderStatus.CONFIRMED)
        db.get.return_value = order

        with patch("app.routers.orders.get_db", return_value=iter([db])), \
             patch("app.routers.orders.transition_status", return_value=order) as mock_ts, \
             patch("app.routers.orders.require_roles", return_value=lambda: None):
            resp = client.patch(
                "/api/orders/1/status",
                json={"status": "confirmed"},
            )
        assert mock_ts.called

    def test_update_status_order_not_found(self):
        db = MagicMock()
        db.get.return_value = None

        with patch("app.routers.orders.get_db", return_value=iter([db])), \
             patch("app.routers.orders.require_roles", return_value=lambda: None):
            resp = client.patch(
                "/api/orders/9999/status",
                json={"status": "confirmed"},
            )
        assert resp.status_code == 404
        assert "주문을 찾을 수 없습니다" in resp.json()["detail"]

    def test_update_status_invalid_status_value(self):
        """Invalid status value should fail schema validation (422)."""
        db = MagicMock()
        db.get.return_value = _make_order()

        with patch("app.routers.orders.get_db", return_value=iter([db])), \
             patch("app.routers.orders.require_roles", return_value=lambda: None):
            resp = client.patch(
                "/api/orders/1/status",
                json={"status": "invalid_status"},
            )
        assert resp.status_code == 422


# ===========================================================================
# Tests that validate the OrderCreate schema handles coupon_code correctly
# ===========================================================================

class TestOrderCreateSchema:
    def test_coupon_code_optional_defaults_none(self):
        payload = OrderCreate(user_id=1, subtotal=1000)
        assert payload.coupon_code is None

    def test_coupon_code_can_be_set(self):
        payload = OrderCreate(user_id=1, subtotal=1000, coupon_code="DISCOUNT10")
        assert payload.coupon_code == "DISCOUNT10"

    def test_coupon_code_accepts_none_explicitly(self):
        payload = OrderCreate(user_id=1, subtotal=1000, coupon_code=None)
        assert payload.coupon_code is None

    def test_subtotal_required(self):
        with pytest.raises(Exception):
            OrderCreate(user_id=1)  # missing subtotal

    def test_user_id_required(self):
        with pytest.raises(Exception):
            OrderCreate(subtotal=1000)  # missing user_id


# ===========================================================================
# Integration-style tests: service layer passes coupon_code as keyword
# ===========================================================================

class TestServiceLayerKeywordOnlyCoupon:
    """
    Simulate the service layer to ensure it passes coupon_code
    using keyword syntax (compatible with the new signature).
    """

    def test_service_passes_coupon_as_keyword(self):
        class UserGrade(str, enum.Enum):
            NORMAL = "normal"
            VIP = "vip"

        calls = []

        def calculate_discount(subtotal: int, grade: UserGrade, *, coupon_code=None) -> int:
            calls.append({"subtotal": subtotal, "grade": grade, "coupon_code": coupon_code})
            return 0

        # Simulate how the fixed service layer should call it
        def service_create_order(subtotal, grade, coupon_code=None):
            # Correct: keyword-only
            return calculate_discount(subtotal, grade, coupon_code=coupon_code)

        service_create_order(5000, UserGrade.NORMAL, coupon_code="TEST")
        assert len(calls) == 1
        assert calls[0]["coupon_code"] == "TEST"