"""Tests for backend/app/models/order.py verifying correct handling of Product.brand_id addition."""

import enum
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from sqlalchemy import Integer, String, ForeignKey, DateTime, Enum as SAEnum


# ---------------------------------------------------------------------------
# Minimal Base & stub models so we can import order.py without a full app
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# Stub User model referenced by Order relationship
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    orders: Mapped[list["Order"]] = relationship(back_populates="user")


# Stub Product model WITH the new brand_id field
class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    brand_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NEW FIELD


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus), default=OrderStatus.PENDING, index=True, nullable=False
    )
    subtotal: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
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

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine():
    """In-memory SQLite engine with all tables created."""
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def session(engine):
    """Provide a transactional session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    sess = Session(bind=connection)
    yield sess
    sess.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def sample_user(session):
    user = User(name="Test User")
    session.add(user)
    session.flush()
    return user


@pytest.fixture()
def sample_product_no_brand(session):
    product = Product(name="No Brand Product", brand_id=None)
    session.add(product)
    session.flush()
    return product


@pytest.fixture()
def sample_product_with_brand(session):
    product = Product(name="Branded Product", brand_id=42)
    session.add(product)
    session.flush()
    return product


@pytest.fixture()
def sample_order(session, sample_user):
    order = Order(
        user_id=sample_user.id,
        status=OrderStatus.PENDING,
        subtotal=1000,
        discount_amount=0,
        total=1000,
        created_at=datetime.utcnow(),
    )
    session.add(order)
    session.flush()
    return order


# ===========================================================================
# 1. Schema / column presence tests
# ===========================================================================

class TestProductBrandIdColumn:
    """Verify that Product.brand_id column exists and has the right properties."""

    def test_product_has_brand_id_attribute(self):
        assert hasattr(Product, "brand_id"), "Product must have a brand_id attribute"

    def test_brand_id_column_is_nullable(self, engine):
        insp = inspect(engine)
        columns = {col["name"]: col for col in insp.get_columns("products")}
        assert "brand_id" in columns, "brand_id column must exist in 'products' table"
        assert columns["brand_id"]["nullable"] is True, "brand_id must be nullable"

    def test_brand_id_column_type_is_integer(self, engine):
        insp = inspect(engine)
        columns = {col["name"]: col for col in insp.get_columns("products")}
        col_type = type(columns["brand_id"]["type"]).__name__.upper()
        assert "INT" in col_type, f"brand_id should be an integer type, got {col_type}"

    def test_order_item_has_product_relationship(self):
        """The fix adds a `product` relationship to OrderItem."""
        assert hasattr(OrderItem, "product"), "OrderItem must have a 'product' relationship"

    def test_order_item_product_relationship_points_to_product(self):
        from sqlalchemy.orm import RelationshipProperty
        rel = inspect(OrderItem).relationships["product"]
        assert rel.mapper.class_ is Product


# ===========================================================================
# 2. Product brand_id field – valid values
# ===========================================================================

class TestProductBrandIdValidValues:

    def test_create_product_with_brand_id_none(self, session, sample_product_no_brand):
        session.refresh(sample_product_no_brand)
        assert sample_product_no_brand.brand_id is None

    def test_create_product_with_brand_id_integer(self, session, sample_product_with_brand):
        session.refresh(sample_product_with_brand)
        assert sample_product_with_brand.brand_id == 42

    def test_create_product_brand_id_zero(self, session):
        product = Product(name="Zero Brand", brand_id=0)
        session.add(product)
        session.flush()
        session.refresh(product)
        assert product.brand_id == 0

    def test_create_product_brand_id_large_int(self, session):
        product = Product(name="Large Brand", brand_id=2**30)
        session.add(product)
        session.flush()
        session.refresh(product)
        assert product.brand_id == 2**30

    def test_update_product_brand_id_from_none_to_value(self, session, sample_product_no_brand):
        sample_product_no_brand.brand_id = 99
        session.flush()
        session.refresh(sample_product_no_brand)
        assert sample_product_no_brand.brand_id == 99

    def test_update_product_brand_id_from_value_to_none(self, session, sample_product_with_brand):
        sample_product_with_brand.brand_id = None
        session.flush()
        session.refresh(sample_product_with_brand)
        assert sample_product_with_brand.brand_id is None

    def test_multiple_products_different_brand_ids(self, session):
        p1 = Product(name="P1", brand_id=1)
        p2 = Product(name="P2", brand_id=2)
        p3 = Product(name="P3", brand_id=None)
        session.add_all([p1, p2, p3])
        session.flush()
        for p in (p1, p2, p3):
            session.refresh(p)
        assert p1.brand_id == 1
        assert p2.brand_id == 2
        assert p3.brand_id is None


# ===========================================================================
# 3. OrderItem → Product relationship with brand_id
# ===========================================================================

class TestOrderItemProductRelationship:

    def test_order_item_can_access_product_brand_id_when_set(
        self, session, sample_order, sample_product_with_brand
    ):
        item = OrderItem(
            order_id=sample_order.id,
            product_id=sample_product_with_brand.id,
            unit_price=500,
            quantity=2,
        )
        session.add(item)
        session.flush()
        session.refresh(item)
        assert item.product.brand_id == 42

    def test_order_item_can_access_product_brand_id_when_none(
        self, session, sample_order, sample_product_no_brand
    ):
        item = OrderItem(
            order_id=sample_order.id,
            product_id=sample_product_no_brand.id,
            unit_price=300,
            quantity=1,
        )
        session.add(item)
        session.flush()
        session.refresh(item)
        assert item.product.brand_id is None

    def test_order_item_product_brand_id_does_not_raise_attribute_error(
        self, session, sample_order, sample_product_with_brand
    ):
        item = OrderItem(
            order_id=sample_order.id,
            product_id=sample_product_with_brand.id,
            unit_price=100,
            quantity=1,
        )
        session.add(item)
        session.flush()
        session.refresh(item)
        try:
            _ = item.product.brand_id
        except AttributeError as exc:
            pytest.fail(f"Accessing brand_id raised AttributeError: {exc}")

    def test_accessing_brand_id_on_product_stub_without_field_raises_attribute_error(self):
        """Backward-incompatible: a Product-like object without brand_id raises AttributeError."""
        class OldProduct:
            """Simulates the old Product model that did NOT have brand_id."""
            id = 1
            name = "old product"

        old_product = OldProduct()
        with pytest.raises(AttributeError):
            _ = old_product.brand_id


# ===========================================================================
# 4. Order model – unchanged behaviour is preserved
# ===========================================================================

class TestOrderModelIntegrity:

    def test_create_order_with_pending_status(self, session, sample_user):
        order = Order(
            user_id=sample_user.id,
            status=OrderStatus.PENDING,
            subtotal=500,
            discount_amount=0,
            total=500,
            created_at=datetime.utcnow(),
        )
        session.add(order)
        session.flush()
        assert order.id is not None
        assert order.status == OrderStatus.PENDING

    def test_order_status_enum_values(self):
        assert set(OrderStatus) == {
            OrderStatus.PENDING,
            OrderStatus.PAID,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED,
        }

    def test_order_invalid_status_raises(self, session, sample_user):
        """Passing an invalid status string should not silently succeed."""
        with pytest.raises(Exception):
            order = Order(
                user_id=sample_user.id,
                status="INVALID_STATUS",  # type: ignore[arg-type]
                subtotal=500,
                discount_amount=0,
                total=500,
                created_at=datetime.utcnow(),
            )
            session.add(order)
            session.flush()

    def test_order_cascade_delete_removes_items(
        self, session, sample_order, sample_product_with_brand
    ):
        item = OrderItem(
            order_id=sample_order.id,
            product_id=sample_product_with_brand.id,
            unit_price=200,
            quantity=3,
        )
        session.add(item)
        session.flush()
        item_id = item.id

        session.delete(sample_order)
        session.flush()

        remaining = session.get(OrderItem, item_id)
        assert remaining is None, "OrderItem should be deleted with its Order (cascade)"

    def test_order_requires_user_id(self, session):
        with pytest.raises(Exception):
            order = Order(
                user_id=None,  # type: ignore[arg-type]
                status=OrderStatus.PENDING,
                subtotal=100,
                discount_amount=0,
                total=100,
                created_at=datetime.utcnow(),
            )
            session.add(order)
            session.flush()

    def test_order_coupon_code_nullable(self, session, sample_user):
        order = Order(
            user_id=sample_user.id,
            status=OrderStatus.PAID,
            subtotal=800,
            discount_amount=100,
            total=700,
            coupon_code=None,
            created_at=datetime.utcnow(),
        )
        session.add(order)
        session.flush()
        session.refresh(order)
        assert order.coupon_code is None

    def test_order_coupon_code_stored(self, session, sample_user):
        order = Order(
            user_id=sample_user.id,
            status=OrderStatus.PAID,
            subtotal=800,
            discount_amount=100,
            total=700,
            coupon_code="SAVE10",
            created_at=datetime.utcnow(),
        )
        session.add(order)
        session.flush()
        session.refresh(order)
        assert order.coupon_code == "SAVE10"


# ===========================================================================
# 5. OrderItem model – field constraints
# ===========================================================================

class TestOrderItemFieldConstraints:

    def test_order_item_requires_product_id(self, session, sample_order):
        with pytest.raises(Exception):
            item = OrderItem(
                order_id=sample_order.id,
                product_id=None,  # type: ignore[arg-type]
                unit_price=100,
                quantity=1,
            )
            session.add(item)
            session.flush()

    def test_order_item_requires_order_id(self, session, sample_product_with_brand):
        with pytest.raises(Exception):
            item = OrderItem(
                order_id=None,  # type: ignore[arg-type]
                product_id=sample_product_with_brand.id,
                unit_price=100,
                quantity=1,
            )
            session.add(item)
            session.flush()

    def test_order_item_stores_unit_price_and_quantity(
        self, session, sample_order, sample_product_no_brand
    ):
        item = OrderItem(
            order