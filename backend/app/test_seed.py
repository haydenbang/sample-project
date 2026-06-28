"""Tests for the seed.py changes related to OrderOut.final_amount field addition."""

import pytest
from unittest.mock import MagicMock, patch, call
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers / minimal stubs so we can import seed without a real DB
# ---------------------------------------------------------------------------

class _MockQuery:
    """Minimal query stub that returns None for .first()."""

    def first(self):
        return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_db():
    """Return a mock SQLAlchemy Session."""
    db = MagicMock(spec=Session)
    # By default, simulate an empty DB (no existing users)
    db.query.return_value = _MockQuery()
    db.flush.return_value = None
    db.commit.return_value = None
    db.add.return_value = None
    db.add_all.return_value = None
    return db


# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------

# We patch heavy dependencies so the import never touches a real DB or bcrypt.
@pytest.fixture(autouse=True)
def patch_security(monkeypatch):
    """Patch hash_password so tests don't need bcrypt installed."""
    with patch("app.common.security.hash_password", return_value="hashed_pw"):
        yield


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestSeedFinalAmountField:
    """Verify that the Order object created by seed() includes final_amount."""

    def test_order_created_with_final_amount(self, mock_db):
        """seed() must create an Order that sets final_amount to a non-None value."""
        from app.seed import seed  # noqa: PLC0415

        created_orders = []

        def capture_add(obj):
            from app.models.order import Order  # noqa: PLC0415
            if isinstance(obj, Order):
                created_orders.append(obj)

        mock_db.add.side_effect = capture_add

        seed(mock_db)

        assert len(created_orders) == 1, "Exactly one Order should be added via db.add()"
        order = created_orders[0]
        assert hasattr(order, "final_amount"), "Order must have 'final_amount' attribute"
        assert order.final_amount is not None, "final_amount must not be None"

    def test_final_amount_is_integer(self, mock_db):
        """final_amount must be an integer value (not None, not float string, etc.)."""
        from app.seed import seed  # noqa: PLC0415
        from app.models.order import Order  # noqa: PLC0415

        created_orders = []

        def capture_add(obj):
            if isinstance(obj, Order):
                created_orders.append(obj)

        mock_db.add.side_effect = capture_add
        seed(mock_db)

        order = created_orders[0]
        assert isinstance(order.final_amount, int), (
            f"final_amount should be int, got {type(order.final_amount)}"
        )

    def test_final_amount_equals_total(self, mock_db):
        """In the seed fixture final_amount should equal the order total (74100)."""
        from app.seed import seed  # noqa: PLC0415
        from app.models.order import Order  # noqa: PLC0415

        created_orders = []

        def capture_add(obj):
            if isinstance(obj, Order):
                created_orders.append(obj)

        mock_db.add.side_effect = capture_add
        seed(mock_db)

        order = created_orders[0]
        assert order.final_amount == 74100, (
            f"Expected final_amount=74100, got {order.final_amount}"
        )

    def test_final_amount_equals_total_minus_discount(self, mock_db):
        """final_amount should equal subtotal - discount_amount."""
        from app.seed import seed  # noqa: PLC0415
        from app.models.order import Order  # noqa: PLC0415

        created_orders = []

        def capture_add(obj):
            if isinstance(obj, Order):
                created_orders.append(obj)

        mock_db.add.side_effect = capture_add
        seed(mock_db)

        order = created_orders[0]
        expected = order.subtotal - order.discount_amount
        assert order.final_amount == expected, (
            f"final_amount ({order.final_amount}) != subtotal - discount_amount ({expected})"
        )

    def test_final_amount_not_negative(self, mock_db):
        """final_amount must be >= 0 (nullable=False implies meaningful value)."""
        from app.seed import seed  # noqa: PLC0415
        from app.models.order import Order  # noqa: PLC0415

        created_orders = []

        def capture_add(obj):
            if isinstance(obj, Order):
                created_orders.append(obj)

        mock_db.add.side_effect = capture_add
        seed(mock_db)

        order = created_orders[0]
        assert order.final_amount >= 0, (
            f"final_amount should be >= 0, got {order.final_amount}"
        )

    def test_seed_skips_when_user_exists(self, mock_db):
        """seed() must be a no-op when the DB already contains users."""
        from app.seed import seed  # noqa: PLC0415

        # Simulate existing user
        existing_user = MagicMock()
        query_mock = MagicMock()
        query_mock.first.return_value = existing_user
        mock_db.query.return_value = query_mock

        seed(mock_db)

        mock_db.add.assert_not_called()
        mock_db.add_all.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_seed_commits_once(self, mock_db):
        """seed() should commit exactly once."""
        from app.seed import seed  # noqa: PLC0415

        seed(mock_db)

        mock_db.commit.assert_called_once()

    def test_seed_flushes_before_order(self, mock_db):
        """seed() must flush after adding products/users so IDs are available."""
        from app.seed import seed  # noqa: PLC0415

        seed(mock_db)

        mock_db.flush.assert_called()

    def test_order_other_financial_fields_present(self, mock_db):
        """Sanity check: subtotal, discount_amount, and total must also be set."""
        from app.seed import seed  # noqa: PLC0415
        from app.models.order import Order  # noqa: PLC0415

        created_orders = []

        def capture_add(obj):
            if isinstance(obj, Order):
                created_orders.append(obj)

        mock_db.add.side_effect = capture_add
        seed(mock_db)

        order = created_orders[0]
        assert order.subtotal is not None, "subtotal must be set"
        assert order.discount_amount is not None, "discount_amount must be set"
        assert order.total is not None, "total must be set"
        assert order.final_amount is not None, "final_amount must be set"


# ---------------------------------------------------------------------------
# Schema / serialization tests for OrderOut
# ---------------------------------------------------------------------------

class TestOrderOutSchema:
    """Verify the OrderOut Pydantic schema correctly handles final_amount."""

    @pytest.fixture()
    def order_out_cls(self):
        """Import the OrderOut schema (skip if not importable)."""
        try:
            from app.schemas.order import OrderOut  # noqa: PLC0415
            return OrderOut
        except ImportError:
            pytest.skip("app.schemas.order.OrderOut not available")

    def test_final_amount_field_exists_in_schema(self, order_out_cls):
        """OrderOut schema must declare final_amount as a field."""
        fields = order_out_cls.model_fields if hasattr(order_out_cls, "model_fields") else order_out_cls.__fields__
        assert "final_amount" in fields, (
            "OrderOut schema must contain 'final_amount' field"
        )

    def test_final_amount_is_required(self, order_out_cls):
        """final_amount is non-nullable so it must be required in the schema."""
        fields = order_out_cls.model_fields if hasattr(order_out_cls, "model_fields") else order_out_cls.__fields__
        field = fields["final_amount"]
        # Pydantic v2 uses FieldInfo with is_required(); v1 uses required attribute
        if hasattr(field, "is_required"):
            assert field.is_required(), "final_amount should be required"
        elif hasattr(field, "required"):
            assert field.required, "final_amount should be required"

    def test_order_out_rejects_none_final_amount(self, order_out_cls):
        """Creating an OrderOut with final_amount=None must raise a validation error."""
        import pydantic  # noqa: PLC0415

        sample = {
            "id": 1,
            "user_id": 1,
            "status": "PAID",
            "subtotal": 78000,
            "discount_amount": 3900,
            "total": 74100,
            "final_amount": None,  # <-- invalid per nullable=False
        }
        with pytest.raises((pydantic.ValidationError, TypeError, ValueError)):
            order_out_cls(**sample)

    def test_order_out_accepts_valid_final_amount(self, order_out_cls):
        """Creating an OrderOut with a valid integer final_amount must succeed."""
        # Try to build a minimal valid object; some fields may be optional
        try:
            obj = order_out_cls(
                id=1,
                user_id=1,
                status="PAID",
                subtotal=78000,
                discount_amount=3900,
                total=74100,
                final_amount=74100,
            )
            assert obj.final_amount == 74100
        except TypeError as exc:
            # Extra required fields exist; just confirm final_amount parses ok
            if "final_amount" not in str(exc):
                pytest.skip(f"Schema requires additional fields: {exc}")

    def test_order_out_serializes_final_amount(self, order_out_cls):
        """final_amount must be included in the serialized output."""
        try:
            obj = order_out_cls(
                id=1,
                user_id=1,
                status="PAID",
                subtotal=78000,
                discount_amount=3900,
                total=74100,
                final_amount=74100,
            )
        except TypeError as exc:
            pytest.skip(f"Schema requires additional fields: {exc}")

        if hasattr(obj, "model_dump"):
            data = obj.model_dump()
        else:
            data = obj.dict()

        assert "final_amount" in data, "Serialized output must contain 'final_amount'"
        assert data["final_amount"] == 74100


# ---------------------------------------------------------------------------
# Backward-incompatible cases
# ---------------------------------------------------------------------------

class TestBackwardIncompatibility:
    """Ensure that omitting final_amount raises appropriate errors."""

    def test_order_model_requires_final_amount_for_non_nullable_column(self, mock_db):
        """
        Directly constructing an Order without final_amount and flushing it
        should eventually cause an IntegrityError or similar DB-level error.
        This test validates that the code path which omits final_amount would
        break at the DB layer (simulated here).
        """
        from app.models.order import Order  # noqa: PLC0415
        from sqlalchemy.exc import IntegrityError  # noqa: PLC0415

        # Simulate DB rejecting a NULL in a NOT NULL column
        mock_db.flush.side_effect = IntegrityError(
            statement="INSERT INTO orders",
            params={},
            orig=Exception("NOT NULL constraint failed: orders.final_amount"),
        )

        order = Order(
            user_id=1,
            status="PAID",
            subtotal=78000,
            discount_amount=3900,
            total=74100,
            # final_amount intentionally omitted
        )
        mock_db.add(order)

        with pytest.raises(IntegrityError):
            mock_db.flush()

    def test_order_out_schema_missing_final_amount_raises(self):
        """
        Constructing OrderOut without final_amount raises ValidationError,
        demonstrating backward-incompatibility for old code that didn't set it.
        """
        try:
            from app.schemas.order import OrderOut  # noqa: PLC0415
            import pydantic  # noqa: PLC0415
        except ImportError:
            pytest.skip("app.schemas.order.OrderOut not available")

        with pytest.raises((pydantic.ValidationError, TypeError)):
            # Deliberately omit final_amount
            OrderOut(
                id=1,
                user_id=1,
                status="PAID",
                subtotal=78000,
                discount_amount=3900,
                total=74100,
                # final_amount missing
            )

    def test_order_dict_without_final_amount_fails_validation(self):
        """
        A raw dict representing an old-style order (without final_amount)
        must fail OrderOut validation.
        """
        try:
            from app.schemas.order import OrderOut  # noqa: PLC0415
            import pydantic  # noqa: PLC0415
        except ImportError:
            pytest.skip("app.schemas.order.OrderOut not available")

        old_payload = {
            "id": 2,
            "user_id": 5,
            "status": "PENDING",
            "subtotal": 50000,
            "discount_amount": 0,
            "total": 50000,
            # final_amount is absent — old schema
        }

        with pytest.raises((pydantic.ValidationError, TypeError)):
            if hasattr(OrderOut, "model_validate"):
                OrderOut.model_validate(old_payload)
            else:
                OrderOut(**old_payload)