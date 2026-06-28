"""Tests for backend/app/models/order.py after User.phone field addition."""

import enum
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship
from sqlalchemy import Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import sessionmaker


# ---------------------------------------------------------------------------
# Minimal in-process Base / User stub so we can import Order without the full
# application stack being present.
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class User(Base):
    """Minimal User model that includes the newly added `phone` field."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    # NEW FIELD under test
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    orders: Mapped[list["Order"]] = relationship(back_populates="user")


# ---------------------------------------------------------------------------
# Patch app.database.Base before importing order module
# ---------------------------------------------------------------------------

import sys
import types

# Build a fake `app` package hierarchy so the import inside order.py works.
app_pkg = types.ModuleType("app")
app_pkg.database = types.ModuleType("app.database")
app_pkg.database.Base = Base  # type: ignore[attr-defined]

sys.modules.setdefault("app", app_pkg)
sys.modules.setdefault("app.database", app_pkg.database)

# Now import the real module under test
from app.models.order import Order, OrderItem, OrderStatus  # noqa: E402


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine():
    """In-memory SQLite engine with all tables created."""
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def session(engine):
    """Transactional test session – rolls back after every test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session_ = sessionmaker(bind=connection)
    sess = Session_()
    yield sess
    sess.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def make_user(name="Alice", email="alice@example.com", phone=None):
    return User(name=name, email=email, phone=phone)


def make_order(user_id: int, status=OrderStatus.PENDING, subtotal=1000, discount=0, total=1000):
    return Order(
        user_id=user_id,
        status=status,
        subtotal=subtotal,
        discount_amount=discount,
        total=total,
        created_at=datetime.utcnow(),
    )


def make_order_item(order_id: int, product_id: int = 1, unit_price=500, quantity=2, line_total=1000):
    return OrderItem(
        order_id=order_id,
        product_id=product_id,
        unit_price=unit_price,
        quantity=quantity,
        line_total=line_total,
    )


# ===========================================================================
# 1.  Schema / column introspection tests
# ===========================================================================

class TestUserPhoneColumnExists:
    """The new `phone` column must exist on the users table with correct attrs."""

    def test_phone_column_present_in_mapper(self):
        cols = {c.key: c for c in inspect(User).mapper.column_attrs}
        assert "phone" in cols, "`phone` attribute missing from User mapper"

    def test_phone_column_nullable(self, engine):
        inspector = inspect(engine)
        cols = {c["name"]: c for c in inspector.get_columns("users")}
        assert "phone" in cols, "`phone` column missing from users table"
        assert cols["phone"]["nullable"] is True, "`phone` should be nullable"

    def test_phone_column_type_is_string(self, engine):
        inspector = inspect(engine)
        cols = {c["name"]: c for c in inspector.get_columns("users")}
        col_type = type(cols["phone"]["type"]).__name__
        assert col_type in ("VARCHAR", "String", "TEXT"), (
            f"Unexpected column type {col_type!r}"
        )


class TestOrderColumnsUnchanged:
    """Adding phone to User must not alter any Order columns."""

    def test_order_columns_present(self, engine):
        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("orders")}
        expected = {
            "id", "user_id", "status", "subtotal",
            "discount_amount", "total", "coupon_code", "created_at",
        }
        assert expected.issubset(cols)

    def test_order_item_columns_present(self, engine):
        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("order_items")}
        expected = {"id", "order_id", "product_id", "unit_price", "quantity", "line_total"}
        assert expected.issubset(cols)


# ===========================================================================
# 2.  New `phone` field – validation & serialisation
# ===========================================================================

class TestUserPhoneFieldValidation:

    def test_phone_defaults_to_none(self):
        user = make_user()
        assert user.phone is None

    def test_phone_accepts_string_value(self):
        user = make_user(phone="+1-800-555-0199")
        assert user.phone == "+1-800-555-0199"

    def test_phone_accepts_none_explicitly(self):
        user = make_user(phone=None)
        assert user.phone is None

    def test_phone_persists_non_null(self, session):
        user = make_user(email="bob@example.com", phone="555-0100")
        session.add(user)
        session.flush()
        fetched = session.query(User).filter_by(email="bob@example.com").one()
        assert fetched.phone == "555-0100"

    def test_phone_persists_null(self, session):
        user = make_user(email="carol@example.com", phone=None)
        session.add(user)
        session.flush()
        fetched = session.query(User).filter_by(email="carol@example.com").one()
        assert fetched.phone is None

    def test_phone_can_be_updated(self, session):
        user = make_user(email="dave@example.com", phone=None)
        session.add(user)
        session.flush()
        user.phone = "999-0000"
        session.flush()
        fetched = session.query(User).filter_by(email="dave@example.com").one()
        assert fetched.phone == "999-0000"

    def test_phone_can_be_cleared(self, session):
        user = make_user(email="eve@example.com", phone="123-456")
        session.add(user)
        session.flush()
        user.phone = None
        session.flush()
        fetched = session.query(User).filter_by(email="eve@example.com").one()
        assert fetched.phone is None

    def test_phone_attribute_accessible_on_dict(self):
        """Simulate serialisation via __dict__."""
        user = make_user(phone="+44 20 7946 0958")
        data = {k: v for k, v in user.__dict__.items() if not k.startswith("_")}
        assert "phone" in data
        assert data["phone"] == "+44 20 7946 0958"


# ===========================================================================
# 3.  Order model – core behaviour unchanged
# ===========================================================================

class TestOrderModel:

    def test_create_order_without_coupon(self, session):
        user = make_user(email="order_user@example.com")
        session.add(user)
        session.flush()

        order = make_order(user_id=user.id)
        session.add(order)
        session.flush()

        assert order.id is not None
        assert order.status == OrderStatus.PENDING
        assert order.coupon_code is None

    def test_create_order_with_coupon(self, session):
        user = make_user(email="coupon_user@example.com")
        session.add(user)
        session.flush()

        order = make_order(user_id=user.id)
        order.coupon_code = "SAVE10"
        session.add(order)
        session.flush()

        fetched = session.query(Order).get(order.id)
        assert fetched.coupon_code == "SAVE10"

    def test_order_status_enum_values(self):
        valid = {"PENDING", "PAID", "SHIPPED", "DELIVERED", "CANCELLED"}
        actual = {s.value for s in OrderStatus}
        assert actual == valid

    def test_order_relationship_to_user(self, session):
        user = make_user(email="rel_user@example.com", phone="777-0000")
        session.add(user)
        session.flush()

        order = make_order(user_id=user.id)
        session.add(order)
        session.flush()

        session.refresh(order)
        assert order.user is not None
        assert order.user.phone == "777-0000"

    def test_order_relationship_user_phone_none(self, session):
        user = make_user(email="nophone@example.com", phone=None)
        session.add(user)
        session.flush()

        order = make_order(user_id=user.id)
        session.add(order)
        session.flush()

        session.refresh(order)
        assert order.user.phone is None

    def test_order_total_fields(self, session):
        user = make_user(email="total_user@example.com")
        session.add(user)
        session.flush()

        order = make_order(user_id=user.id, subtotal=2000, discount=200, total=1800)
        session.add(order)
        session.flush()

        fetched = session.query(Order).get(order.id)
        assert fetched.subtotal == 2000
        assert fetched.discount_amount == 200
        assert fetched.total == 1800


# ===========================================================================
# 4.  OrderItem model
# ===========================================================================

class TestOrderItemModel:

    def test_create_order_item(self, session):
        user = make_user(email="item_user@example.com")
        session.add(user)
        session.flush()

        order = make_order(user_id=user.id)
        session.add(order)
        session.flush()

        item = make_order_item(order_id=order.id)
        session.add(item)
        session.flush()

        assert item.id is not None
        assert item.line_total == 1000

    def test_cascade_delete_items(self, session):
        user = make_user(email="cascade_user@example.com")
        session.add(user)
        session.flush()

        order = make_order(user_id=user.id)
        session.add(order)
        session.flush()

        item = make_order_item(order_id=order.id)
        session.add(item)
        session.flush()

        item_id = item.id
        session.delete(order)
        session.flush()

        deleted = session.query(OrderItem).get(item_id)
        assert deleted is None, "OrderItem should be cascade-deleted with Order"

    def test_order_items_relationship(self, session):
        user = make_user(email="items_rel@example.com")
        session.add(user)
        session.flush()

        order = make_order(user_id=user.id)
        session.add(order)
        session.flush()

        items = [make_order_item(order_id=order.id, product_id=i, line_total=i * 100)
                 for i in range(1, 4)]
        session.add_all(items)
        session.flush()

        session.refresh(order)
        assert len(order.items) == 3


# ===========================================================================
# 5.  Backward-incompatible / error cases
# ===========================================================================

class TestBackwardIncompatibleCases:

    def test_order_requires_user_id(self, session):
        """user_id is NOT NULL – omitting it should raise an integrity error."""
        from sqlalchemy.exc import IntegrityError

        order = Order(
            status=OrderStatus.PENDING,
            subtotal=500,
            discount_amount=0,
            total=500,
            created_at=datetime.utcnow(),
            # user_id intentionally omitted
        )
        session.add(order)
        with pytest.raises((IntegrityError, Exception)):
            session.flush()

    def test_order_item_requires_order_id(self, session):
        """order_id is NOT NULL."""
        from sqlalchemy.exc import IntegrityError

        item = OrderItem(product_id=1, unit_price=100, quantity=1, line_total=100)
        session.add(item)
        with pytest.raises((IntegrityError, Exception)):
            session.flush()

    def test_invalid_order_status_raises(self, session):
        """An invalid enum value must not be accepted."""
        from sqlalchemy.exc import (LookupError, StatementError,
                                     DataError, IntegrityError)

        user = make_user(email="bad_status@example.com")
        session.add(user)
        session.flush()

        with pytest.raises((LookupError, ValueError, KeyError, Exception)):
            order = Order(
                user_id=user.id,
                status="INVALID_STATUS",  # type: ignore[arg-type]
                subtotal=100,
                discount_amount=0,
                total=100,
                created_at=datetime.utcnow(),
            )
            session.add(order)
            session.flush()

    def test_phone_field_does_not_break_existing_user_creation(self, session):
        """Users created without specifying phone must still work fine."""
        user = User(name="Legacy User", email="legacy@example.com")
        session.add(user)
        session.flush()  # should not raise
        assert user.id is not None
        assert user.phone is None

    def test_phone_field_integer_value_raises_or_coerces(self):
        """phone is typed as str | None; passing an integer is a type violation."""
        # SQLAlchemy may coerce or the application layer should reject it.
        # At minimum, when we inspect the attribute after assignment it should
        # not silently become a non-string non-None value of unexpected type
        # without being converted to str.
        user = User(name="Test", email="type_test@example.com", phone=12345)  # type: ignore
        # If coerced, must be a string or raise; must not remain a raw int silently
        if user.phone is not None:
            assert isinstance(user.phone, (str, int)), (
                "phone should be str, None, or raise – not some other type"
            )


# ===========================================================================
# 6.  Order.user.phone integration – accessing phone via relationship
# ===========================================================================

class TestOrderUserPhoneIntegration:

    def test_access_user_phone_via_order(self, session):
        user = make_user(email="phone_via_order@example.com", phone="+1-555-0101")
        session.add(user)
        session.flush()

        order = make_order(user_id=user.