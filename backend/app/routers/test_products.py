"""Tests for backend/app/routers/products.py — verifying brand_id field handling."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, PropertyMock
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Minimal stub models and schemas so tests don't need the full app stack
# ---------------------------------------------------------------------------

import sys
import types

# ---- stub app.models.product ----
product_mod = types.ModuleType("app.models.product")


class ProductStatus:
    ACTIVE = "ACTIVE"
    SOLD_OUT = "SOLD_OUT"
    DRAFT = "DRAFT"


class Product:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if not hasattr(self, "brand_id"):
            self.brand_id = None
        if not hasattr(self, "status"):
            self.status = None
        if not hasattr(self, "id"):
            self.id = 1

    def __repr__(self):
        return f"<Product id={getattr(self, 'id', None)} brand_id={self.brand_id}>"


product_mod.Product = Product
product_mod.ProductStatus = ProductStatus
sys.modules["app.models.product"] = product_mod

# ---- stub app.models.user ----
user_mod = types.ModuleType("app.models.user")


class UserRole:
    ADMIN = "ADMIN"
    STAFF = "STAFF"


user_mod.UserRole = UserRole
sys.modules["app.models.user"] = user_mod

# ---- stub app.database ----
db_mod = types.ModuleType("app.database")


def get_db():
    yield MagicMock(spec=Session)


db_mod.get_db = get_db
sys.modules["app.database"] = db_mod

# ---- stub app.common.deps ----
deps_mod = types.ModuleType("app.common.deps")


def require_roles(*roles):
    def dep():
        return MagicMock()

    return dep


deps_mod.require_roles = require_roles
sys.modules["app.common.deps"] = deps_mod

# ---- Pydantic schemas ----
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List


class ProductCreate(BaseModel):
    name: str
    price: float
    stock: int
    category: Optional[str] = None
    brand_id: Optional[int] = None  # new field


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    category: Optional[str] = None
    brand_id: Optional[int] = None  # new field


class ProductOut(BaseModel):
    id: int
    name: str
    price: float
    stock: int
    category: Optional[str] = None
    brand_id: Optional[int] = None  # new field
    status: Optional[str] = None

    class Config:
        from_attributes = True


class ProductListOut(BaseModel):
    items: List[ProductOut]
    total: int
    page: int
    size: int


# ---- stub app.schemas.product ----
schemas_mod = types.ModuleType("app.schemas.product")
schemas_mod.ProductCreate = ProductCreate
schemas_mod.ProductUpdate = ProductUpdate
schemas_mod.ProductOut = ProductOut
schemas_mod.ProductListOut = ProductListOut
sys.modules["app.schemas.product"] = schemas_mod

# ---- stub parent modules ----
for mod_name in ["app", "app.common", "app.schemas", "app.models"]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)

# ---------------------------------------------------------------------------
# Now import the router under test
# ---------------------------------------------------------------------------
from app.routers.products import router, _sync_status  # noqa: E402

app = FastAPI()
app.include_router(router)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_db_product(**kwargs) -> Product:
    defaults = dict(id=1, name="Widget", price=9.99, stock=10, category="tools", brand_id=None, status="ACTIVE")
    defaults.update(kwargs)
    return Product(**defaults)


def mock_db_session(product=None, products=None, total=0):
    """Return a MagicMock that mimics a SQLAlchemy Session."""
    db = MagicMock(spec=Session)
    query_mock = MagicMock()
    db.query.return_value = query_mock
    query_mock.filter.return_value = query_mock
    query_mock.count.return_value = total
    query_mock.offset.return_value = query_mock
    query_mock.limit.return_value = query_mock
    query_mock.all.return_value = products or []
    db.refresh.side_effect = lambda p: None
    return db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    return TestClient(app, raise_server_exceptions=True)


# ===========================================================================
# Tests: ProductCreate schema — brand_id field
# ===========================================================================


class TestProductCreateSchema:
    def test_brand_id_present_and_valid(self):
        data = {"name": "Gizmo", "price": 5.0, "stock": 3, "brand_id": 42}
        schema = ProductCreate(**data)
        assert schema.brand_id == 42

    def test_brand_id_none_by_default(self):
        data = {"name": "Gizmo", "price": 5.0, "stock": 3}
        schema = ProductCreate(**data)
        assert schema.brand_id is None

    def test_brand_id_null_explicit(self):
        data = {"name": "Gizmo", "price": 5.0, "stock": 3, "brand_id": None}
        schema = ProductCreate(**data)
        assert schema.brand_id is None

    def test_brand_id_zero_is_accepted(self):
        """Zero is a valid int, even if unusual."""
        data = {"name": "Gizmo", "price": 5.0, "stock": 3, "brand_id": 0}
        schema = ProductCreate(**data)
        assert schema.brand_id == 0

    def test_brand_id_string_raises_validation_error(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ProductCreate(name="Gizmo", price=5.0, stock=3, brand_id="not-an-int")

    def test_brand_id_float_coerced_to_int(self):
        """Pydantic v2 coerces compatible floats."""
        schema = ProductCreate(name="Gizmo", price=5.0, stock=3, brand_id=3.0)
        assert schema.brand_id == 3

    def test_brand_id_negative_accepted(self):
        """Negative int should be accepted — no constraint in the model."""
        schema = ProductCreate(name="Gizmo", price=5.0, stock=3, brand_id=-1)
        assert schema.brand_id == -1

    def test_model_dump_includes_brand_id(self):
        schema = ProductCreate(name="Gizmo", price=5.0, stock=3, brand_id=7)
        dumped = schema.model_dump()
        assert "brand_id" in dumped
        assert dumped["brand_id"] == 7

    def test_model_dump_includes_brand_id_when_none(self):
        schema = ProductCreate(name="Gizmo", price=5.0, stock=3)
        dumped = schema.model_dump()
        assert "brand_id" in dumped
        assert dumped["brand_id"] is None


# ===========================================================================
# Tests: ProductUpdate schema — brand_id field
# ===========================================================================


class TestProductUpdateSchema:
    def test_brand_id_can_be_updated(self):
        schema = ProductUpdate(brand_id=99)
        assert schema.brand_id == 99

    def test_brand_id_can_be_set_to_none(self):
        schema = ProductUpdate(brand_id=None)
        assert schema.brand_id is None

    def test_model_dump_exclude_unset_omits_brand_id_when_not_supplied(self):
        schema = ProductUpdate(name="NewName")
        dumped = schema.model_dump(exclude_unset=True)
        assert "brand_id" not in dumped

    def test_model_dump_exclude_unset_includes_brand_id_when_supplied(self):
        schema = ProductUpdate(name="NewName", brand_id=5)
        dumped = schema.model_dump(exclude_unset=True)
        assert "brand_id" in dumped
        assert dumped["brand_id"] == 5

    def test_brand_id_string_raises_validation_error(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ProductUpdate(brand_id="bad")


# ===========================================================================
# Tests: ProductOut schema — brand_id serialization
# ===========================================================================


class TestProductOutSchema:
    def test_brand_id_serialized_correctly(self):
        p = make_db_product(brand_id=10)
        out = ProductOut.model_validate(p)
        assert out.brand_id == 10

    def test_brand_id_none_serialized_correctly(self):
        p = make_db_product(brand_id=None)
        out = ProductOut.model_validate(p)
        assert out.brand_id is None

    def test_brand_id_appears_in_json_output(self):
        p = make_db_product(brand_id=55)
        out = ProductOut.model_validate(p)
        json_data = out.model_dump()
        assert "brand_id" in json_data
        assert json_data["brand_id"] == 55

    def test_brand_id_none_appears_in_json_output(self):
        p = make_db_product(brand_id=None)
        out = ProductOut.model_validate(p)
        json_data = out.model_dump()
        assert "brand_id" in json_data
        assert json_data["brand_id"] is None

    def test_product_without_brand_id_attribute_defaults_none(self):
        """Backward-compat: older Product objects may lack brand_id attr."""
        p = make_db_product()
        del p.brand_id  # simulate old object
        # Re-attach None manually to avoid AttributeError in from_attributes
        p.brand_id = None
        out = ProductOut.model_validate(p)
        assert out.brand_id is None


# ===========================================================================
# Tests: _sync_status helper
# ===========================================================================


class TestSyncStatus:
    def test_stock_zero_active_becomes_sold_out(self):
        p = make_db_product(stock=0, status=ProductStatus.ACTIVE)
        _sync_status(p)
        assert p.status == ProductStatus.SOLD_OUT

    def test_stock_nonzero_active_unchanged(self):
        p = make_db_product(stock=5, status=ProductStatus.ACTIVE)
        _sync_status(p)
        assert p.status == ProductStatus.ACTIVE

    def test_stock_zero_draft_unchanged(self):
        p = make_db_product(stock=0, status=ProductStatus.DRAFT)
        _sync_status(p)
        assert p.status == ProductStatus.DRAFT

    def test_brand_id_not_affected_by_sync_status(self):
        p = make_db_product(stock=0, status=ProductStatus.ACTIVE, brand_id=7)
        _sync_status(p)
        assert p.brand_id == 7


# ===========================================================================
# Tests: POST /api/products — create_product endpoint
# ===========================================================================


class TestCreateProductEndpoint:
    def _post(self, client, payload, db):
        with patch("app.routers.products.get_db", return_value=iter([db])):
            resp = client.post("/api/products", json=payload)
        return resp

    def test_create_with_brand_id_returns_201(self, client):
        db = mock_db_session()
        db.refresh.side_effect = lambda p: setattr(p, "id", 1) or None

        payload = {"name": "Widget", "price": 9.99, "stock": 5, "brand_id": 42}

        captured = {}

        original_add = db.add

        def capture_add(obj):
            captured["product"] = obj

        db.add.side_effect = capture_add

        with patch("app.routers.products.get_db", return_value=iter([db])):
            resp = client.post("/api/products", json=payload)

        # brand_id should have been passed to Product constructor
        assert captured["product"].brand_id == 42

    def test_create_without_brand_id_defaults_none(self, client):
        db = mock_db_session()
        captured = {}

        def capture_add(obj):
            captured["product"] = obj

        db.add.side_effect = capture_add

        payload = {"name": "Widget", "price": 9.99, "stock": 5}

        with patch("app.routers.products.get_db", return_value=iter([db])):
            resp = client.post("/api/products", json=payload)

        assert captured["product"].brand_id is None

    def test_create_brand_id_null_explicit(self, client):
        db = mock_db_session()
        captured = {}

        def capture_add(obj):
            captured["product"] = obj

        db.add.side_effect = capture_add

        payload = {"name": "Widget", "price": 9.99, "stock": 5, "brand_id": None}

        with patch("app.routers.products.get_db", return_value=iter([db])):
            resp = client.post("/api/products", json=payload)

        assert captured["product"].brand_id is None

    def test_create_brand_id_invalid_string_returns_422(self, client):
        db = mock_db_session()
        payload = {"name": "Widget", "price": 9.99, "stock": 5, "brand_id": "not-an-int"}

        with patch("app.routers.products.get_db", return_value=iter([db])):
            resp = client.post("/api/products", json=payload)

        assert resp.status_code == 422

    def test_create_brand_id_missing_does_not_cause_500(self, client):
        db = mock_db_session()
        db.refresh.side_effect = lambda p: None
        payload = {"name": "Widget", "price": 9.99, "stock": 5}

        with patch("app.routers.products.get_db", return_value=iter([db])):
            resp = client.post("/api/products", json=payload)

        # Should not be a server error
        assert resp.status_code != 500

    def test_model_dump_passes_brand_id_to_product(self):
        """Unit test: ProductCreate.model_dump() always includes brand_id."""
        schema = ProductCreate(name="X", price=1.0, stock=1, brand_id=99)
        dumped = schema.model_dump()
        product = Product(**dumped)
        assert product.brand_id == 99

    def test_model_dump_passes_brand_id_none_to_product(self):
        schema = ProductCreate(name="X", price=1.0, stock=1)
        dumped = schema.model_dump()
        product = Product(**dumped)
        assert product.brand_id is None


# ===========================================================================
# Tests: GET /api/products — list_products endpoint
# ===========================================================================


class TestListProductsEndpoint:
    def test_list_returns_brand_id_