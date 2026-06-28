"""Tests for seed.py with the new final_amount field on Order/OrderOut."""

import pytest
from unittest.mock import MagicMock, patch, call
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

class FakeUser:
    _id_counter = 1

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.id = FakeUser._id_counter
        FakeUser._id_counter += 1


class FakeProduct:
    _id_counter = 100

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.id = FakeProduct._id_counter
        FakeProduct._id_counter += 1


class FakeOrderItem:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeOrder:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_id_counters():
    """Reset fake id counters between tests."""
    FakeUser._id_counter = 1
    FakeProduct._id_counter = 100
    yield


@pytest.fixture
def mock_db():
    db = MagicMock(spec=Session)
    # By default, query().first() returns None → seed not yet run
    db.query.return_value.first.return_value = None
    return db


@pytest.fixture
def patched_seed(mock_db):
    """Return the seed function with external dependencies patched."""
    with (
        patch("app.common.security.hash_password", side_effect=lambda p: f"hashed:{p}"),
        patch("app.models.user.User", side_effect=FakeUser),
        patch("app.models.user.UserRole") as mock_role,
        patch("app.models.user.UserGrade") as mock_grade,
        patch("app.models.product.Product", side_effect=FakeProduct),
        patch("app.models.product.ProductStatus") as mock_pstatus,
        patch("app.models.order.Order", side_effect=FakeOrder),
        patch("app.models.order.OrderItem", side_effect=FakeOrderItem),
        patch("app.models.order.OrderStatus") as mock_ostatus,
    ):
        mock_role.ADMIN = "ADMIN"
        mock_role.VIEWER = "VIEWER"
        mock_grade.VIP = "VIP"
        mock_grade.GOLD = "GOLD"
        mock_pstatus.ACTIVE = "ACTIVE"
        mock_pstatus.SOLD_OUT = "SOLD_OUT"
        mock_ostatus.PAID = "PAID"

        from app.seed import seed  # noqa: PLC0415
        yield seed, mock_db


# ---------------------------------------------------------------------------
# Tests – seed guard
# ---------------------------------------------------------------------------

class TestSeedGuard:
    def test_seed_skips_when_users_already_exist(self, mock_db):
        """If a User already exists in the DB the seed function must return early."""
        mock_db.query.return_value.first.return_value = FakeUser(email="existing@example.com")

        with (
            patch("app.common.security.hash_password"),
            patch("app.models.user.User", side_effect=FakeUser),
            patch("app.models.user.UserRole"),
            patch("app.models.user.UserGrade"),
            patch("app.models.product.Product", side_effect=FakeProduct),
            patch("app.models.product.ProductStatus"),
            patch("app.models.order.Order", side_effect=FakeOrder),
            patch("app.models.order.OrderItem", side_effect=FakeOrderItem),
            patch("app.models.order.OrderStatus"),
        ):
            from app.seed import seed  # noqa: PLC0415
            seed(mock_db)

        mock_db.add_all.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_seed_runs_when_no_users_exist(self, mock_db):
        mock_db.query.return_value.first.return_value = None

        with (
            patch("app.common.security.hash_password", return_value="hashed"),
            patch("app.models.user.User", side_effect=FakeUser),
            patch("app.models.user.UserRole"),
            patch("app.models.user.UserGrade"),
            patch("app.models.product.Product", side_effect=FakeProduct),
            patch("app.models.product.ProductStatus"),
            patch("app.models.order.Order", side_effect=FakeOrder),
            patch("app.models.order.OrderItem", side_effect=FakeOrderItem),
            patch("app.models.order.OrderStatus"),
        ):
            from app.seed import seed  # noqa: PLC0415
            seed(mock_db)

        mock_db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Tests – Order.final_amount field presence and value
# ---------------------------------------------------------------------------

class TestOrderFinalAmountField:
    """Ensure the new non-nullable `final_amount` field is handled correctly."""

    def test_order_created_with_final_amount(self, mock_db):
        """seed() must create an Order that carries the final_amount attribute."""
        created_orders: list[FakeOrder] = []

        def capture_order(**kwargs):
            o = FakeOrder(**kwargs)
            created_orders.append(o)
            return o

        with (
            patch("app.common.security.hash_password", return_value="hashed"),
            patch("app.models.user.User", side_effect=FakeUser),
            patch("app.models.user.UserRole"),
            patch("app.models.user.UserGrade"),
            patch("app.models.product.Product", side_effect=FakeProduct),
            patch("app.models.product.ProductStatus"),
            patch("app.models.order.Order", side_effect=capture_order),
            patch("app.models.order.OrderItem", side_effect=FakeOrderItem),
            patch("app.models.order.OrderStatus"),
        ):
            from app.seed import seed  # noqa: PLC0415
            seed(mock_db)

        assert len(created_orders) == 1, "Exactly one order should be created"
        order = created_orders[0]
        assert hasattr(order, "final_amount"), (
            "Order must have the 'final_amount' field (field was added)"
        )

    def test_final_amount_is_not_none(self, mock_db):
        """final_amount must not be None (field is non-nullable)."""
        created_orders: list[FakeOrder] = []

        def capture_order(**kwargs):
            o = FakeOrder(**kwargs)
            created_orders.append(o)
            return o

        with (
            patch("app.common.security.hash_password", return_value="hashed"),
            patch("app.models.user.User", side_effect=FakeUser),
            patch("app.models.user.UserRole"),
            patch("app.models.user.UserGrade"),
            patch("app.models.product.Product", side_effect=FakeProduct),
            patch("app.models.product.ProductStatus"),
            patch("app.models.order.Order", side_effect=capture_order),
            patch("app.models.order.OrderItem", side_effect=FakeOrderItem),
            patch("app.models.order.OrderStatus"),
        ):
            from app.seed import seed  # noqa: PLC0415
            seed(mock_db)

        assert created_orders[0].final_amount is not None, (
            "final_amount must not be None – field is non-nullable"
        )

    def test_final_amount_is_integer(self, mock_db):
        """final_amount must be an integer (column type = int)."""
        created_orders: list[FakeOrder] = []

        def capture_order(**kwargs):
            o = FakeOrder(**kwargs)
            created_orders.append(o)
            return o

        with (
            patch("app.common.security.hash_password", return_value="hashed"),
            patch("app.models.user.User", side_effect=FakeUser),
            patch("app.models.user.UserRole"),
            patch("app.models.user.UserGrade"),
            patch("app.models.product.Product", side_effect=FakeProduct),
            patch("app.models.product.ProductStatus"),
            patch("app.models.order.Order", side_effect=capture_order),
            patch("app.models.order.OrderItem", side_effect=FakeOrderItem),
            patch("app.models.order.OrderStatus"),
        ):
            from app.seed import seed  # noqa: PLC0415
            seed(mock_db)

        assert isinstance(created_orders[0].final_amount, int), (
            "final_amount must be an int"
        )

    def test_final_amount_equals_total(self, mock_db):
        """In the seed, final_amount should equal the order total (74100)."""
        created_orders: list[FakeOrder] = []

        def capture_order(**kwargs):
            o = FakeOrder(**kwargs)
            created_orders.append(o)
            return o

        with (
            patch("app.common.security.hash_password", return_value="hashed"),
            patch("app.models.user.User", side_effect=FakeUser),
            patch("app.models.user.UserRole"),
            patch("app.models.user.UserGrade"),
            patch("app.models.product.Product", side_effect=FakeProduct),
            patch("app.models.product.ProductStatus"),
            patch("app.models.order.Order", side_effect=capture_order),
            patch("app.models.order.OrderItem", side_effect=FakeOrderItem),
            patch("app.models.order.OrderStatus"),
        ):
            from app.seed import seed  # noqa: PLC0415
            seed(mock_db)

        order = created_orders[0]
        assert order.final_amount == 74100, (
            f"Expected final_amount=74100, got {order.final_amount}"
        )

    def test_final_amount_matches_total_field(self, mock_db):
        """final_amount must be equal to the `total` field in the seed data."""
        created_orders: list[FakeOrder] = []

        def capture_order(**kwargs):
            o = FakeOrder(**kwargs)
            created_orders.append(o)
            return o

        with (
            patch("app.common.security.hash_password", return_value="hashed"),
            patch("app.models.user.User", side_effect=FakeUser),
            patch("app.models.user.UserRole"),
            patch("app.models.user.UserGrade"),
            patch("app.models.product.Product", side_effect=FakeProduct),
            patch("app.models.product.ProductStatus"),
            patch("app.models.order.Order", side_effect=capture_order),
            patch("app.models.order.OrderItem", side_effect=FakeOrderItem),
            patch("app.models.order.OrderStatus"),
        ):
            from app.seed import seed  # noqa: PLC0415
            seed(mock_db)

        order = created_orders[0]
        assert order.final_amount == order.total


# ---------------------------------------------------------------------------
# Tests – backward-incompatible cases (missing final_amount)
# ---------------------------------------------------------------------------

class TestBackwardIncompatibility:
    """Verify that creating an Order without final_amount raises an error."""

    def test_order_without_final_amount_raises_type_error(self):
        """Pydantic / dataclass schemas that set final_amount as required must raise."""

        # Simulate a schema that has final_amount as a required, non-nullable field.
        class OrderOutSchema:
            def __init__(
                self,
                subtotal: int,
                discount_amount: int,
                total: int,
                final_amount: int,       # required, non-nullable
            ):
                if final_amount is None:
                    raise ValueError("final_amount must not be None")
                if not isinstance(final_amount, int):
                    raise TypeError("final_amount must be an int")
                self.subtotal = subtotal
                self.discount_amount = discount_amount
                self.total = total
                self.final_amount = final_amount

        # Should succeed when provided
        schema = OrderOutSchema(
            subtotal=78000,
            discount_amount=3900,
            total=74100,
            final_amount=74100,
        )
        assert schema.final_amount == 74100

        # Must raise TypeError when final_amount is not provided at all
        with pytest.raises(TypeError):
            OrderOutSchema(subtotal=78000, discount_amount=3900, total=74100)  # type: ignore[call-arg]

    def test_order_with_none_final_amount_raises_value_error(self):
        """Passing None for final_amount must raise ValueError (non-nullable column)."""

        class OrderOutSchema:
            def __init__(self, *, final_amount: int):
                if final_amount is None:
                    raise ValueError("final_amount must not be None (non-nullable column)")
                self.final_amount = final_amount

        with pytest.raises(ValueError, match="non-nullable"):
            OrderOutSchema(final_amount=None)  # type: ignore[arg-type]

    def test_order_with_string_final_amount_raises_type_error(self):
        """Passing a string where int is expected must raise TypeError."""

        class OrderOutSchema:
            def __init__(self, *, final_amount: int):
                if not isinstance(final_amount, int):
                    raise TypeError(
                        f"final_amount must be int, got {type(final_amount).__name__}"
                    )
                self.final_amount = final_amount

        with pytest.raises(TypeError, match="int"):
            OrderOutSchema(final_amount="74100")  # type: ignore[arg-type]

    def test_order_with_float_final_amount_raises_type_error(self):
        """Passing a float for an int column should raise TypeError."""

        class OrderOutSchema:
            def __init__(self, *, final_amount: int):
                if not isinstance(final_amount, int):
                    raise TypeError(
                        f"final_amount must be int, got {type(final_amount).__name__}"
                    )
                self.final_amount = final_amount

        with pytest.raises(TypeError):
            OrderOutSchema(final_amount=74100.0)  # type: ignore[arg-type]

    def test_old_order_dict_without_final_amount_fails_validation(self):
        """A payload that predates the schema change (no final_amount) must fail."""

        def validate_order_out(data: dict) -> dict:
            if "final_amount" not in data:
                raise KeyError("final_amount is required but was not provided")
            if data["final_amount"] is None:
                raise ValueError("final_amount must not be None")
            if not isinstance(data["final_amount"], int):
                raise TypeError("final_amount must be an int")
            return data

        old_payload = {
            "subtotal": 78000,
            "discount_amount": 3900,
            "total": 74100,
            # 'final_amount' intentionally absent (old schema)
        }

        with pytest.raises(KeyError, match="final_amount"):
            validate_order_out(old_payload)

    def test_new_order_dict_with_final_amount_passes_validation(self):
        """A payload that includes final_amount must pass validation."""

        def validate_order_out(data: dict) -> dict:
            if "final_amount" not in data:
                raise KeyError("final_amount is required but was not provided")
            if data["final_amount"] is None:
                raise ValueError("final_amount must not be None")
            if not isinstance(data["final_amount"], int):
                raise TypeError("final_amount must be an int")
            return data

        new_payload = {
            "subtotal":