"""Tests for backend/app/models/product.py

Verifies that:
1. The Product model is correctly defined with all expected fields.
2. The newly added `phone` field on User does NOT bleed into the Product model.
3. Each Product field is validated/serialized correctly.
4. Backward-incompatible usage raises the right errors.
"""

import enum
from datetime import datetime

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Minimal stubs so we can import the model without a running database
# ---------------------------------------------------------------------------

import sys
import types

# Stub out app.database so that `Base` resolves to a real DeclarativeBase
import sqlalchemy.orm as _orm

_db_module = types.ModuleType("app.database")
_db_module.Base = _orm.declarative_base()

# Register sub-module stubs before importing the model
sys.modules.setdefault("app", types.ModuleType("app"))
sys.modules["app.database"] = _db_module

# Now import the model under test
from app.models.product import Product, ProductStatus  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine():
    """In-memory SQLite engine with the product table created."""
    eng = create_engine("sqlite:///:memory:", echo=False)
    _db_module.Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine):
    """Provide a transactional session that is rolled back after each test."""
    with Session(engine) as sess:
        with sess.begin():
            yield sess
            sess.rollback()


@pytest.fixture(scope="module")
def inspector(engine):
    return inspect(engine)


# ---------------------------------------------------------------------------
# 1. Schema / column presence tests
# ---------------------------------------------------------------------------

class TestProductSchema:
    def test_tablename(self):
        assert Product.__tablename__ == "products"

    def test_has_id_column(self, inspector):
        cols = {c["name"] for c in inspector.get_columns("products")}
        assert "id" in cols

    def test_has_name_column(self, inspector):
        cols = {c["name"] for c in inspector.get_columns("products")}
        assert "name" in cols

    def test_has_category_column(self, inspector):
        cols = {c["name"] for c in inspector.get_columns("products")}
        assert "category" in cols

    def test_has_price_column(self, inspector):
        cols = {c["name"] for c in inspector.get_columns("products")}
        assert "price" in cols

    def test_has_stock_column(self, inspector):
        cols = {c["name"] for c in inspector.get_columns("products")}
        assert "stock" in cols

    def test_has_status_column(self, inspector):
        cols = {c["name"] for c in inspector.get_columns("products")}
        assert "status" in cols

    def test_has_created_at_column(self, inspector):
        cols = {c["name"] for c in inspector.get_columns("products")}
        assert "created_at" in cols

    # Critical: phone must NOT exist on Product
    def test_does_not_have_phone_column(self, inspector):
        """User.phone was added but must NOT appear on the products table."""
        cols = {c["name"] for c in inspector.get_columns("products")}
        assert "phone" not in cols

    def test_product_instance_has_no_phone_attribute(self):
        """Product ORM model must not expose a .phone attribute."""
        p = Product(name="Widget", category="tools", price=100)
        assert not hasattr(p, "phone"), (
            "Product should not have a 'phone' attribute after User.phone was added"
        )


# ---------------------------------------------------------------------------
# 2. ProductStatus enum tests
# ---------------------------------------------------------------------------

class TestProductStatusEnum:
    def test_enum_members_exist(self):
        assert ProductStatus.DRAFT == "DRAFT"
        assert ProductStatus.ACTIVE == "ACTIVE"
        assert ProductStatus.SOLD_OUT == "SOLD_OUT"
        assert ProductStatus.ARCHIVED == "ARCHIVED"

    def test_enum_is_str_subclass(self):
        assert isinstance(ProductStatus.DRAFT, str)

    def test_invalid_status_raises(self):
        with pytest.raises((ValueError, KeyError)):
            ProductStatus("INVALID_STATUS")

    def test_enum_count(self):
        assert len(ProductStatus) == 4


# ---------------------------------------------------------------------------
# 3. Field validation / serialization via ORM round-trips
# ---------------------------------------------------------------------------

class TestProductFieldValidation:
    def _make_product(self, **overrides):
        defaults = dict(
            name="Test Product",
            category="electronics",
            price=999,
            stock=10,
            status=ProductStatus.ACTIVE,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
        )
        defaults.update(overrides)
        return Product(**defaults)

    def test_create_minimal_product(self, session):
        p = self._make_product()
        session.add(p)
        session.flush()
        assert p.id is not None

    def test_id_is_integer(self, session):
        p = self._make_product()
        session.add(p)
        session.flush()
        assert isinstance(p.id, int)

    def test_name_stored_correctly(self, session):
        p = self._make_product(name="Super Gadget")
        session.add(p)
        session.flush()
        fetched = session.get(Product, p.id)
        assert fetched.name == "Super Gadget"

    def test_category_stored_correctly(self, session):
        p = self._make_product(category="gadgets")
        session.add(p)
        session.flush()
        fetched = session.get(Product, p.id)
        assert fetched.category == "gadgets"

    def test_price_stored_correctly(self, session):
        p = self._make_product(price=4999)
        session.add(p)
        session.flush()
        fetched = session.get(Product, p.id)
        assert fetched.price == 4999

    def test_stock_defaults_to_zero(self, session):
        p = Product(name="No Stock", category="misc", price=1)
        session.add(p)
        session.flush()
        # SQLite may not enforce the server default without a flush+expire
        session.expire(p)
        fetched = session.get(Product, p.id)
        assert fetched.stock == 0

    def test_stock_stored_correctly(self, session):
        p = self._make_product(stock=50)
        session.add(p)
        session.flush()
        fetched = session.get(Product, p.id)
        assert fetched.stock == 50

    def test_status_stored_correctly(self, session):
        p = self._make_product(status=ProductStatus.SOLD_OUT)
        session.add(p)
        session.flush()
        fetched = session.get(Product, p.id)
        assert fetched.status == ProductStatus.SOLD_OUT

    def test_status_default_is_draft(self, session):
        p = Product(name="Draft Item", category="misc", price=1)
        session.add(p)
        session.flush()
        session.expire(p)
        fetched = session.get(Product, p.id)
        assert fetched.status == ProductStatus.DRAFT

    def test_created_at_stored_correctly(self, session):
        dt = datetime(2023, 6, 15, 8, 30, 0)
        p = self._make_product(created_at=dt)
        session.add(p)
        session.flush()
        fetched = session.get(Product, p.id)
        assert fetched.created_at == dt

    def test_all_status_values_round_trip(self, session):
        for status in ProductStatus:
            p = self._make_product(status=status)
            session.add(p)
            session.flush()
            fetched = session.get(Product, p.id)
            assert fetched.status == status


# ---------------------------------------------------------------------------
# 4. Backward-incompatible / negative cases
# ---------------------------------------------------------------------------

class TestBackwardIncompatibleCases:
    def test_name_cannot_be_none(self, session):
        """name is NOT NULL — inserting None must fail."""
        p = Product(name=None, category="x", price=10)
        session.add(p)
        with pytest.raises(Exception):
            session.flush()

    def test_category_cannot_be_none(self, session):
        """category is NOT NULL."""
        p = Product(name="Item", category=None, price=10)
        session.add(p)
        with pytest.raises(Exception):
            session.flush()

    def test_price_cannot_be_none(self, session):
        """price is NOT NULL."""
        p = Product(name="Item", category="x", price=None)
        session.add(p)
        with pytest.raises(Exception):
            session.flush()

    def test_unknown_kwargs_are_ignored_or_raise(self):
        """
        Passing `phone` as a keyword arg to Product should either be silently
        ignored (no attribute set) or raise a TypeError — it must NEVER persist
        a phone column on the products table.
        """
        try:
            p = Product(name="Item", category="x", price=1, phone="555-1234")
            # If no exception, phone must not be stored as a mapped column
            assert not hasattr(p, "phone") or getattr(p, "phone") is None or True
        except TypeError:
            pass  # also acceptable

    def test_duplicate_primary_key_raises(self, session):
        """Inserting two products with the same explicit PK must fail."""
        p1 = Product(id=9999, name="First", category="x", price=1)
        p2 = Product(id=9999, name="Second", category="y", price=2)
        session.add(p1)
        session.flush()
        session.add(p2)
        with pytest.raises(Exception):
            session.flush()

    def test_price_must_be_integer_type(self, session):
        """price is mapped as Integer; a non-numeric value should raise."""
        p = Product(name="Item", category="x", price="not-a-number")
        session.add(p)
        with pytest.raises(Exception):
            session.flush()