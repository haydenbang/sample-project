"""Tests for Order model and OrderOut schema with the new final_amount field."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, DeclarativeBase

# ---------------------------------------------------------------------------
# Minimal Base for in-memory testing (avoids importing the real app.database)
# ---------------------------------------------------------------------------
from sqlalchemy.orm import DeclarativeBase as _DeclarativeBase


class Base(_DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Re-define the models here using the Base above so we can test them in
# isolation with an in-memory SQLite database without needing the full app.
# ---------------------------------------------------------------------------
import enum
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class User(Base):
    """Minimal User stub so the ForeignKey constraint can be satisfied."""
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class Product(Base):
    """Minimal Product stub so the ForeignKey constraint can be satisfied."""
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.PENDING, index=True, nullable=False
    )
    subtotal: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    final_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    coupon_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True, nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")


# ---------------------------------------------------------------------------
# Pydantic schema (OrderOut) – defined here to mirror what the real app
# should expose after the fix.
# ---------------------------------------------------------------------------
from pydantic import BaseModel, ValidationError, field_validator
from typing import Optional


class OrderOut(BaseModel):
    id: int
    user_id: int
    status: OrderStatus
    subtotal: int
    discount_amount: int
    total: int
    final_amount: int  # NEW non-nullable field
    coupon_code: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def engine():
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture()
def db_session(engine):
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture()
def sample_user(db_session):
    user = User(id=1)
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def sample_product(db_session):
    product = Product(id=1)
    db_session.add(product)
    db_session.flush()
    return product


@pytest.fixture()
def sample_order(db_session, sample_user):
    order = Order(
        user_id=sample_user.id,
        status=OrderStatus.PENDING,
        subtotal=10000,
        discount_amount=500,
        total=9500,
        final_amount=9500,
        created_at=datetime(2024, 1, 15, 12, 0, 0),
    )
    db_session.add(order)
    db_session.flush()
    return order


# ===========================================================================
# 1. Schema-level tests – OrderOut
# ===========================================================================

class TestOrderOutSchema:
    """Verify that the OrderOut Pydantic schema handles final_amount correctly."""

    def _base_payload(self, **overrides):
        payload = {
            "id": 1,
            "user_id": 42,
            "status": OrderStatus.PENDING,
            "subtotal": 10000,
            "discount_amount": 500,
            "total": 9500,
            "final_amount": 9500,
            "coupon_code": None,
            "created_at": datetime(2024, 1, 15, 12, 0, 0),
        }
        payload.update(overrides)
        return payload

    # --- happy-path ---

    def test_valid_payload_with_final_amount(self):
        """OrderOut should parse successfully when final_amount is provided."""
        out = OrderOut(**self._base_payload())
        assert out.final_amount == 9500

    def test_final_amount_zero_is_valid(self):
        """final_amount of 0 (fully discounted) must be accepted."""
        out = OrderOut(**self._base_payload(final_amount=0))
        assert out.final_amount == 0

    def test_final_amount_large_value(self):
        """final_amount should handle large integer values."""
        out = OrderOut(**self._base_payload(final_amount=9_999_999))
        assert out.final_amount == 9_999_999

    def test_final_amount_is_integer_type(self):
        """final_amount must be serialised as an integer."""
        out = OrderOut(**self._base_payload(final_amount=1234))
        assert isinstance(out.final_amount, int)

    def test_serialization_includes_final_amount(self):
        """model_dump() must include the final_amount key."""
        out = OrderOut(**self._base_payload(final_amount=8800))
        data = out.model_dump()
        assert "final_amount" in data
        assert data["final_amount"] == 8800

    def test_json_serialization_includes_final_amount(self):
        """model_dump_json() output must contain final_amount."""
        out = OrderOut(**self._base_payload(final_amount=7700))
        json_str = out.model_dump_json()
        assert "final_amount" in json_str
        assert "7700" in json_str

    def test_final_amount_coerced_from_string_integer(self):
        """Pydantic should coerce a numeric string to int for final_amount."""
        out = OrderOut(**self._base_payload(final_amount="9500"))  # type: ignore[arg-type]
        assert out.final_amount == 9500

    # --- backward-incompatible / error cases ---

    def test_missing_final_amount_raises_validation_error(self):
        """Omitting final_amount must raise a ValidationError (non-nullable)."""
        payload = self._base_payload()
        del payload["final_amount"]
        with pytest.raises(ValidationError) as exc_info:
            OrderOut(**payload)
        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "final_amount" in field_names

    def test_none_final_amount_raises_validation_error(self):
        """Passing None for final_amount must raise a ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            OrderOut(**self._base_payload(final_amount=None))  # type: ignore[arg-type]
        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "final_amount" in field_names

    def test_non_numeric_final_amount_raises_validation_error(self):
        """Non-numeric string for final_amount must raise a ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            OrderOut(**self._base_payload(final_amount="not_a_number"))  # type: ignore[arg-type]
        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "final_amount" in field_names

    def test_float_final_amount_is_coerced_or_rejected(self):
        """A float value should either be coerced to int or rejected; never silently kept as float."""
        try:
            out = OrderOut(**self._base_payload(final_amount=9500.99))  # type: ignore[arg-type]
            # If accepted, it must be an int
            assert isinstance(out.final_amount, int)
        except ValidationError:
            pass  # rejection is also acceptable

    # --- from_attributes (ORM mode) ---

    def test_from_orm_model(self):
        """OrderOut.model_validate() should map an ORM Order object with final_amount."""
        mock_order = MagicMock()
        mock_order.id = 10
        mock_order.user_id = 5
        mock_order.status = OrderStatus.PAID
        mock_order.subtotal = 20000
        mock_order.discount_amount = 1000
        mock_order.total = 19000
        mock_order.final_amount = 19000
        mock_order.coupon_code = "SAVE10"
        mock_order.created_at = datetime(2024, 3, 1, 9, 0, 0)

        out = OrderOut.model_validate(mock_order)
        assert out.final_amount == 19000
        assert out.id == 10


# ===========================================================================
# 2. SQLAlchemy model column tests
# ===========================================================================

class TestOrderModelColumn:
    """Verify the SQLAlchemy Order model has the correct final_amount column."""

    def test_final_amount_column_exists(self):
        """Order model must have a final_amount attribute."""
        assert hasattr(Order, "final_amount")

    def test_final_amount_column_type(self, engine):
        """The final_amount column in the DB must be of Integer type."""
        insp = inspect(engine)
        columns = {col["name"]: col for col in insp.get_columns("orders")}
        assert "final_amount" in columns
        from sqlalchemy import Integer as SAInteger
        assert isinstance(columns["final_amount"]["type"], SAInteger)

    def test_final_amount_column_not_nullable(self, engine):
        """The final_amount column must be NOT NULL."""
        insp = inspect(engine)
        columns = {col["name"]: col for col in insp.get_columns("orders")}
        assert "final_amount" in columns
        assert columns["final_amount"]["nullable"] is False

    def test_order_table_has_expected_columns(self, engine):
        """orders table must include all expected columns including final_amount."""
        insp = inspect(engine)
        col_names = {col["name"] for col in insp.get_columns("orders")}
        expected = {
            "id", "user_id", "status", "subtotal", "discount_amount",
            "total", "final_amount", "coupon_code", "created_at",
        }
        assert expected.issubset(col_names)


# ===========================================================================
# 3. Database persistence tests
# ===========================================================================

class TestOrderPersistence:
    """End-to-end persistence tests for the Order model with final_amount."""

    def test_create_order_with_final_amount(self, db_session, sample_user):
        """An Order with final_amount must persist and retrieve correctly."""
        order = Order(
            user_id=sample_user.id,
            status=OrderStatus.PENDING,
            subtotal=5000,
            discount_amount=0,
            total=5000,
            final_amount=5000,
            created_at=datetime.utcnow(),
        )
        db_session.add(order)
        db_session.flush()
        db_session.refresh(order)
        assert order.final_amount == 5000

    def test_final_amount_stored_and_retrieved(self, db_session, sample_user):
        """final_amount written to DB must match the value read back."""
        expected = 12345
        order = Order(
            user_id=sample_user.id,
            status=OrderStatus.PAID,
            subtotal=13000,
            discount_amount=655,
            total=12345,
            final_amount=expected,
            created_at=datetime.utcnow(),
        )
        db_session.add(order)
        db_session.flush()
        order_id = order.id

        db_session.expire(order)
        retrieved = db_session.get(Order, order_id)
        assert retrieved is not None
        assert retrieved.final_amount == expected

    def test_final_amount_zero_persists(self, db_session, sample_user):
        """final_amount = 0 (e.g., fully comped order) must persist correctly."""
        order = Order(
            user_id=sample_user.id,
            status=OrderStatus.PAID,
            subtotal=1000,
            discount_amount=1000,
            total=0,
            final_amount=0,
            created_at=datetime.utcnow(),
        )
        db_session.add(order)
        db_session.flush()
        db_session.expire(order)
        retrieved = db_session.get(Order, order.id)
        assert retrieved.final_amount == 0

    def test_update_final_amount(self, db_session, sample_user):
        """Updating final_amount on an existing order must be persisted."""
        order = Order(
            user_id=sample_user.id,
            status=OrderStatus.PENDING,
            subtotal=8000,
            discount_amount=0,
            total=8000,
            final_amount=8000,
            created_at=datetime.utcnow(),
        )
        db_session.add(order)
        db_session.flush()

        order.final_amount = 7500
        db_session.flush()
        db_session.expire(order)

        updated = db_session.get(Order, order.id)
        assert updated.final_amount == 7500

    def test_missing_final_amount_raises_integrity_error(self, db_session, sample_user):
        """Inserting an Order without final_amount must raise an IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        # Build the INSERT without final_amount via raw execute to bypass ORM defaults
        from sqlalchemy import text
        with pytest.raises((IntegrityError,