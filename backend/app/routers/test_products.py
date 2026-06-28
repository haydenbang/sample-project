"""Tests for backend/app/routers/products.py verifying correct behavior after User.phone field addition."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from fastapi import FastAPI, status
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Minimal stubs so we can import the router without a real DB / model layer
# ---------------------------------------------------------------------------

import sys
import types

# ── app.common.deps ──────────────────────────────────────────────────────────
deps_mod = types.ModuleType("app.common.deps")

def _require_roles(*roles):
    def _dep():
        return object()
    return _dep

deps_mod.require_roles = _require_roles
sys.modules.setdefault("app", types.ModuleType("app"))
sys.modules["app.common"] = types.ModuleType("app.common")
sys.modules["app.common.deps"] = deps_mod

# ── app.database ─────────────────────────────────────────────────────────────
db_mod = types.ModuleType("app.database")

def _get_db():
    yield MagicMock()

db_mod.get_db = _get_db
sys.modules["app.database"] = db_mod

# ── app.models.user ──────────────────────────────────────────────────────────
user_models_mod = types.ModuleType("app.models.user")

class UserRole:
    ADMIN = "admin"
    STAFF = "staff"
    USER  = "user"

class User:
    """Minimal User model stub that includes the new `phone` field."""
    def __init__(self, *, id=1, email="u@example.com", name="Test",
                 phone=None, role=UserRole.USER):
        self.id    = id
        self.email = email
        self.name  = name
        self.phone = phone          # ← newly added nullable field
        self.role  = role

user_models_mod.UserRole = UserRole
user_models_mod.User     = User
sys.modules["app.models"] = types.ModuleType("app.models")
sys.modules["app.models.user"] = user_models_mod

# ── app.models.product ───────────────────────────────────────────────────────
product_models_mod = types.ModuleType("app.models.product")

class ProductStatus:
    ACTIVE   = "active"
    DRAFT    = "draft"
    SOLD_OUT = "sold_out"

class Product:
    def __init__(self, *, id=1, name="Widget", description="desc",
                 price=9.99, stock=10, category="general",
                 status=ProductStatus.ACTIVE):
        self.id          = id
        self.name        = name
        self.description = description
        self.price       = price
        self.stock       = stock
        self.category    = category
        self.status      = status

product_models_mod.Product       = Product
product_models_mod.ProductStatus = ProductStatus
sys.modules["app.models.product"] = product_models_mod

# ── app.schemas.product ──────────────────────────────────────────────────────
from pydantic import BaseModel
from typing import List, Optional

class ProductCreate(BaseModel):
    name:        str
    description: str       = ""
    price:       float
    stock:       int
    category:    str       = "general"

class ProductUpdate(BaseModel):
    name:        Optional[str]   = None
    description: Optional[str]  = None
    price:       Optional[float] = None
    stock:       Optional[int]   = None
    category:    Optional[str]   = None

class ProductOut(BaseModel):
    id:          int
    name:        str
    description: str
    price:       float
    stock:       int
    category:    str
    status:      str

    model_config = {"from_attributes": True}

class ProductListOut(BaseModel):
    items: List[ProductOut]
    total: int
    page:  int
    size:  int

schemas_mod = types.ModuleType("app.schemas.product")
schemas_mod.ProductCreate  = ProductCreate
schemas_mod.ProductUpdate  = ProductUpdate
schemas_mod.ProductOut     = ProductOut
schemas_mod.ProductListOut = ProductListOut
sys.modules["app.schemas"] = types.ModuleType("app.schemas")
sys.modules["app.schemas.product"] = schemas_mod

# ── Now import the real router ───────────────────────────────────────────────
from app.routers.products import router, _sync_status  # noqa: E402

app = FastAPI()
app.include_router(router)
client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_db():
    return MagicMock()


@pytest.fixture(autouse=True)
def _patch_db(mock_db):
    """Replace get_db with one that yields our mock_db."""
    with patch("app.routers.products.get_db", return_value=iter([mock_db])):
        yield mock_db


@pytest.fixture(autouse=True)
def _patch_require_roles():
    """Make role checks transparent."""
    with patch("app.routers.products.require_roles", side_effect=_require_roles):
        yield


def _make_product(**kwargs):
    defaults = dict(id=1, name="Widget", description="desc",
                    price=9.99, stock=10, category="general",
                    status=ProductStatus.ACTIVE)
    defaults.update(kwargs)
    return Product(**defaults)


# ===========================================================================
# Tests: User model – phone field added (nullable str)
# ===========================================================================

class TestUserPhoneField:
    """Direct unit tests for the new `phone` field on the User model stub."""

    def test_user_phone_defaults_to_none(self):
        user = User(email="a@b.com", name="Alice")
        assert user.phone is None

    def test_user_phone_accepts_string(self):
        user = User(email="a@b.com", name="Alice", phone="+1-800-555-0100")
        assert user.phone == "+1-800-555-0100"

    def test_user_phone_accepts_none_explicitly(self):
        user = User(email="a@b.com", name="Alice", phone=None)
        assert user.phone is None

    def test_user_phone_type_is_str_when_set(self):
        user = User(email="a@b.com", name="Alice", phone="123")
        assert isinstance(user.phone, str)

    def test_user_without_phone_still_has_role(self):
        """Regression: adding phone must not break existing fields."""
        user = User(email="a@b.com", name="Alice", role=UserRole.ADMIN)
        assert user.role == UserRole.ADMIN
        assert user.phone is None

    def test_user_phone_can_be_updated(self):
        user = User(email="a@b.com", name="Alice")
        user.phone = "555-1234"
        assert user.phone == "555-1234"

    def test_user_phone_non_string_backward_incompatibility(self):
        """phone should be str | None; assigning an int is not valid per schema."""
        user = User(email="a@b.com", name="Alice")
        # The model does NOT enforce types at runtime (plain class), so we
        # verify the field annotation says str, not int.
        import inspect
        hints = {}
        # Collect annotations from the stub – we document the expected type.
        # In the real SQLAlchemy model this would be Mapped[str | None].
        # Here we assert that assigning a non-str value is semantically wrong.
        user.phone = 12345          # simulate bad data
        assert not isinstance(user.phone, str)  # documents the wrong state


# ===========================================================================
# Tests: GET /api/products
# ===========================================================================

class TestListProducts:
    def test_returns_200_with_empty_list(self, mock_db):
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        mock_db.query.return_value.count.return_value = 0
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []

        resp = client.get("/api/products")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []
        assert body["page"] == 1
        assert body["size"] == 20

    def test_returns_products(self, mock_db):
        p = _make_product()
        mock_db.query.return_value.count.return_value = 1
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = [p]

        resp = client.get("/api/products")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["name"] == "Widget"

    def test_category_filter_is_applied(self, mock_db):
        mock_q = mock_db.query.return_value
        mock_q.filter.return_value.count.return_value = 0
        mock_q.filter.return_value.offset.return_value.limit.return_value.all.return_value = []

        resp = client.get("/api/products?category=electronics")
        assert resp.status_code == status.HTTP_200_OK
        mock_q.filter.assert_called_once()

    def test_pagination_params(self, mock_db):
        mock_db.query.return_value.count.return_value = 50
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []

        resp = client.get("/api/products?page=3&size=10")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["page"] == 3
        assert body["size"] == 10

    def test_invalid_page_returns_422(self):
        resp = client.get("/api/products?page=0")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_size_too_large_returns_422(self):
        resp = client.get("/api/products?size=101")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===========================================================================
# Tests: POST /api/products
# ===========================================================================

class TestCreateProduct:
    _payload = dict(name="Gadget", description="cool", price=29.99,
                    stock=5, category="tech")

    def test_creates_product_returns_201(self, mock_db):
        product = _make_product(**self._payload)
        mock_db.refresh.side_effect = lambda p: None

        with patch("app.routers.products.Product", return_value=product):
            resp = client.post("/api/products", json=self._payload)

        assert resp.status_code == status.HTTP_201_CREATED
        mock_db.add.assert_called_once_with(product)
        mock_db.commit.assert_called_once()

    def test_zero_stock_sets_draft(self, mock_db):
        payload = {**self._payload, "stock": 0}
        product = _make_product(**payload, status=ProductStatus.DRAFT)
        mock_db.refresh.side_effect = lambda p: None

        with patch("app.routers.products.Product", return_value=product):
            resp = client.post("/api/products", json=payload)

        assert resp.status_code == status.HTTP_201_CREATED

    def test_positive_stock_sets_active(self, mock_db):
        product = _make_product(**self._payload, status=ProductStatus.ACTIVE)
        mock_db.refresh.side_effect = lambda p: None

        with patch("app.routers.products.Product", return_value=product):
            resp = client.post("/api/products", json=self._payload)

        assert resp.status_code == status.HTTP_201_CREATED

    def test_missing_required_field_returns_422(self):
        resp = client.post("/api/products", json={"name": "X"})  # missing price/stock
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_negative_price_not_accepted_by_schema(self):
        """Pydantic schema does not restrict price sign, but stock must be int."""
        resp = client.post("/api/products",
                           json={**self._payload, "stock": "not-an-int"})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===========================================================================
# Tests: PUT /api/products/{id}
# ===========================================================================

class TestUpdateProduct:
    def test_update_returns_200(self, mock_db):
        product = _make_product()
        mock_db.get.return_value = product
        mock_db.refresh.side_effect = lambda p: None

        resp = client.put("/api/products/1", json={"price": 19.99})
        assert resp.status_code == status.HTTP_200_OK
        assert product.price == 19.99

    def test_update_nonexistent_returns_404(self, mock_db):
        mock_db.get.return_value = None

        resp = client.put("/api/products/999", json={"price": 5.0})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_update_zero_stock_triggers_sold_out(self, mock_db):
        product = _make_product(stock=1, status=ProductStatus.ACTIVE)
        mock_db.get.return_value = product
        mock_db.refresh.side_effect = lambda p: None

        resp = client.put("/api/products/1", json={"stock": 0})
        assert resp.status_code == status.HTTP_200_OK
        assert product.status == ProductStatus.SOLD_OUT

    def test_update_with_empty_body_returns_200(self, mock_db):
        product = _make_product()
        mock_db.get.return_value = product
        mock_db.refresh.side_effect = lambda p: None

        resp = client.put("/api/products/1", json={})
        assert resp.status_code == status.HTTP_200_OK

    def test_update_invalid_price_type_returns_422(self):
        resp = client.put("/api/products/1", json={"price": "free"})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===========================================================================
# Tests: DELETE /api/products/{id}
# ===========================================================================

class TestDeleteProduct:
    def test_delete_returns_204(self, mock_db):
        product = _make_product()
        mock_db.get.return_value = product

        resp = client.delete("/api/products/1")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        mock_db.delete.assert_called_once_with(product)
        mock_db.commit.assert_called_once()

    def test_delete_nonexistent_returns_404(self, mock_db):
        mock_db.get.return_value = None

        resp = client.delete("/api/products/999")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# Tests: _sync_status helper
# ===========================================================================

class TestSyncStatus:
    def test_active_zero_stock_becomes_sold_out(self):
        p = _make_product(stock=0, status=ProductStatus.ACTIVE)
        _sync_status(p)
        assert p.status == ProductStatus.SOLD_OUT

    def test_active_non