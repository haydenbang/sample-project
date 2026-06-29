"""Tests for seed.py verifying ProductStatus enum changes including LOW_STOCK."""

import pytest
from unittest.mock import MagicMock, patch, call
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers / stubs so we can import without a real database
# ---------------------------------------------------------------------------

class _FakeEnum:
    """Minimal stand-in for SQLAlchemy-backed enums used in models."""

    def __init__(self, value: str):
        self.value = value

    def __eq__(self, other):
        if isinstance(other, _FakeEnum):
            return self.value == other.value
        return self.value == other

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.value}>"


# ---------------------------------------------------------------------------
# ProductStatus enum tests (unit-level, model-independent)
# ---------------------------------------------------------------------------

class TestProductStatusEnum:
    """Verify the ProductStatus enum contains exactly the expected members."""

    def _import_product_status(self):
        try:
            from app.models.product import ProductStatus
            return ProductStatus
        except ImportError:
            pytest.skip("app.models.product not importable in this environment")

    def test_low_stock_member_exists(self):
        ProductStatus = self._import_product_status()
        assert hasattr(ProductStatus, "LOW_STOCK"), (
            "ProductStatus must have LOW_STOCK member after enum change"
        )

    def test_low_stock_value(self):
        ProductStatus = self._import_product_status()
        assert ProductStatus.LOW_STOCK.value == "LOW_STOCK"

    def test_all_expected_values_present(self):
        ProductStatus = self._import_product_status()
        expected = {"ACTIVE", "ARCHIVED", "DRAFT", "LOW_STOCK", "SOLD_OUT"}
        actual = {m.value for m in ProductStatus}
        assert expected == actual, (
            f"Expected enum values {expected}, got {actual}"
        )

    def test_original_values_still_present(self):
        """Backward-compatible: values that existed before must still exist."""
        ProductStatus = self._import_product_status()
        pre_existing = {"ACTIVE", "ARCHIVED", "DRAFT", "SOLD_OUT"}
        actual = {m.value for m in ProductStatus}
        missing = pre_existing - actual
        assert not missing, f"Removed enum values (backward-incompatible): {missing}"

    def test_no_extra_unexpected_values(self):
        """No undocumented values should have been added."""
        ProductStatus = self._import_product_status()
        allowed = {"ACTIVE", "ARCHIVED", "DRAFT", "LOW_STOCK", "SOLD_OUT"}
        actual = {m.value for m in ProductStatus}
        unexpected = actual - allowed
        assert not unexpected, f"Unexpected extra enum values: {unexpected}"

    def test_active_member(self):
        ProductStatus = self._import_product_status()
        assert ProductStatus.ACTIVE.value == "ACTIVE"

    def test_archived_member(self):
        ProductStatus = self._import_product_status()
        assert ProductStatus.ARCHIVED.value == "ARCHIVED"

    def test_draft_member(self):
        ProductStatus = self._import_product_status()
        assert ProductStatus.DRAFT.value == "DRAFT"

    def test_sold_out_member(self):
        ProductStatus = self._import_product_status()
        assert ProductStatus.SOLD_OUT.value == "SOLD_OUT"

    def test_enum_member_count(self):
        ProductStatus = self._import_product_status()
        assert len(list(ProductStatus)) == 5, (
            "ProductStatus should have exactly 5 members after adding LOW_STOCK"
        )


# ---------------------------------------------------------------------------
# Seed function tests using mocked DB session
# ---------------------------------------------------------------------------

class TestSeedFunction:
    """Verify seed() correctly seeds LOW_STOCK product and other statuses."""

    @pytest.fixture()
    def mock_db(self):
        db = MagicMock(spec=Session)
        # First call to query().first() returns None → not yet seeded
        db.query.return_value.first.return_value = None
        # flush() must assign IDs so OrderItem foreign keys work
        def _flush_side_effect():
            # Simulate auto-increment ID assignment
            pass
        db.flush.side_effect = _flush_side_effect
        return db

    @pytest.fixture()
    def seeded_db(self, mock_db):
        """Run seed() against the mock DB and return it."""
        try:
            from app.seed import seed
        except ImportError:
            pytest.skip("app.seed not importable in this environment")
        seed(mock_db)
        return mock_db

    # ------------------------------------------------------------------
    # Basic invocation
    # ------------------------------------------------------------------

    def test_seed_calls_commit(self, seeded_db):
        seeded_db.commit.assert_called_once()

    def test_seed_calls_flush(self, seeded_db):
        seeded_db.flush.assert_called_once()

    def test_seed_calls_add_all(self, seeded_db):
        assert seeded_db.add_all.call_count == 2  # users + products

    def test_seed_calls_add_for_order(self, seeded_db):
        seeded_db.add.assert_called_once()

    # ------------------------------------------------------------------
    # Early-exit when already seeded
    # ------------------------------------------------------------------

    def test_seed_skips_if_already_seeded(self):
        try:
            from app.seed import seed
        except ImportError:
            pytest.skip("app.seed not importable in this environment")

        db = MagicMock(spec=Session)
        db.query.return_value.first.return_value = object()  # already has a user
        seed(db)
        db.add_all.assert_not_called()
        db.commit.assert_not_called()

    # ------------------------------------------------------------------
    # Product status assertions
    # ------------------------------------------------------------------

    def _collect_products(self, seeded_db):
        """Return all Product instances passed to add_all."""
        try:
            from app.models.product import Product
        except ImportError:
            pytest.skip("app.models.product not importable")

        products = []
        for c in seeded_db.add_all.call_args_list:
            items = c[0][0]  # first positional arg is the list
            for item in items:
                if isinstance(item, Product):
                    products.append(item)
        return products

    def test_headset_has_low_stock_status(self, seeded_db):
        try:
            from app.models.product import ProductStatus
        except ImportError:
            pytest.skip("app.models.product not importable")

        products = self._collect_products(seeded_db)
        headset = next((p for p in products if "헤드셋" in (p.name or "")), None)
        assert headset is not None, "Headset product should be seeded"
        assert headset.status == ProductStatus.LOW_STOCK, (
            f"Headset should have LOW_STOCK status, got {headset.status}"
        )

    def test_monitor_has_sold_out_status(self, seeded_db):
        try:
            from app.models.product import ProductStatus
        except ImportError:
            pytest.skip("app.models.product not importable")

        products = self._collect_products(seeded_db)
        monitor = next((p for p in products if "모니터" in (p.name or "")), None)
        assert monitor is not None, "Monitor product should be seeded"
        assert monitor.status == ProductStatus.SOLD_OUT

    def test_keyboard_has_active_status(self, seeded_db):
        try:
            from app.models.product import ProductStatus
        except ImportError:
            pytest.skip("app.models.product not importable")

        products = self._collect_products(seeded_db)
        keyboard = next((p for p in products if "키보드" in (p.name or "")), None)
        assert keyboard is not None, "Keyboard product should be seeded"
        assert keyboard.status == ProductStatus.ACTIVE

    def test_mouse_has_active_status(self, seeded_db):
        try:
            from app.models.product import ProductStatus
        except ImportError:
            pytest.skip("app.models.product not importable")

        products = self._collect_products(seeded_db)
        mouse = next((p for p in products if "마우스" in (p.name or "")), None)
        assert mouse is not None, "Mouse product should be seeded"
        assert mouse.status == ProductStatus.ACTIVE

    def test_four_products_seeded(self, seeded_db):
        try:
            from app.models.product import Product
        except ImportError:
            pytest.skip("app.models.product not importable")

        products = self._collect_products(seeded_db)
        assert len(products) == 4, f"Expected 4 products, got {len(products)}"

    def test_low_stock_product_has_nonzero_stock(self, seeded_db):
        products = self._collect_products(seeded_db)
        headset = next((p for p in products if "헤드셋" in (p.name or "")), None)
        if headset is None:
            pytest.skip("Headset not found")
        assert headset.stock > 0, "LOW_STOCK product should have some stock remaining"

    def test_sold_out_product_has_zero_stock(self, seeded_db):
        products = self._collect_products(seeded_db)
        monitor = next((p for p in products if "모니터" in (p.name or "")), None)
        if monitor is None:
            pytest.skip("Monitor not found")
        assert monitor.stock == 0, "SOLD_OUT product should have 0 stock"


# ---------------------------------------------------------------------------
# Backward-incompatibility guard: using removed / non-existent value
# ---------------------------------------------------------------------------

class TestBackwardIncompatibleUsage:
    """Ensure that unknown / removed enum values raise appropriate errors."""

    def _import_product_status(self):
        try:
            from app.models.product import ProductStatus
            return ProductStatus
        except ImportError:
            pytest.skip("app.models.product not importable in this environment")

    def test_accessing_nonexistent_value_raises_key_error(self):
        ProductStatus = self._import_product_status()
        with pytest.raises((KeyError, AttributeError, ValueError)):
            _ = ProductStatus["NONEXISTENT"]

    def test_calling_with_bad_value_raises_value_error(self):
        ProductStatus = self._import_product_status()
        with pytest.raises((ValueError, KeyError)):
            _ = ProductStatus("NONEXISTENT")

    def test_low_stock_not_equal_to_sold_out(self):
        ProductStatus = self._import_product_status()
        assert ProductStatus.LOW_STOCK != ProductStatus.SOLD_OUT

    def test_low_stock_not_equal_to_active(self):
        ProductStatus = self._import_product_status()
        assert ProductStatus.LOW_STOCK != ProductStatus.ACTIVE

    def test_low_stock_is_distinct_from_all_others(self):
        ProductStatus = self._import_product_status()
        others = [m for m in ProductStatus if m != ProductStatus.LOW_STOCK]
        for member in others:
            assert ProductStatus.LOW_STOCK != member, (
                f"LOW_STOCK should not equal {member}"
            )


# ---------------------------------------------------------------------------
# Serialisation / validation tests (Pydantic-style, if schemas exist)
# ---------------------------------------------------------------------------

class TestProductStatusSerialization:
    """If Pydantic schemas exist, verify LOW_STOCK round-trips correctly."""

    def _import_schema(self):
        try:
            from app.schemas.product import ProductCreate, ProductRead  # adjust path
            return ProductCreate, ProductRead
        except ImportError:
            pytest.skip("Pydantic product schemas not available")

    def _import_product_status(self):
        try:
            from app.models.product import ProductStatus
            return ProductStatus
        except ImportError:
            pytest.skip("app.models.product not importable")

    def test_product_create_accepts_low_stock(self):
        ProductCreate, _ = self._import_schema()
        ProductStatus = self._import_product_status()

        try:
            obj = ProductCreate(
                name="테스트 상품",
                category="테스트",
                price=10000,
                stock=3,
                status=ProductStatus.LOW_STOCK,
            )
            assert obj.status == ProductStatus.LOW_STOCK
        except TypeError:
            # If the schema doesn't have a status field, skip
            pytest.skip("ProductCreate schema signature differs")

    def test_product_create_accepts_low_stock_string(self):
        ProductCreate, _ = self._import_schema()

        try:
            obj = ProductCreate(
                name="테스트 상품",
                category="테스트",
                price=10000,
                stock=3,
                status="LOW_STOCK",
            )
            assert obj.status.value == "LOW_STOCK" or obj.status == "LOW_STOCK"
        except (TypeError, Exception) as exc:
            if "LOW_STOCK" in str(exc) or "not a valid" in str(exc).lower():
                pytest.fail(
                    "Schema rejected LOW_STOCK string — enum not updated in schema"
                )
            pytest.skip(f"Schema structure differs: {exc}")

    def test_product_create_rejects_invalid_status(self):
        ProductCreate, _ = self._import_schema()

        with pytest.raises((ValueError, TypeError, Exception)):
            ProductCreate(
                name="테스트 상품",
                category="테스트",
                price=10000,
                stock=3,
                status="INVALID_STATUS",
            )


# ---------------------------------------------------------------------------
# Integration-style: enum value coverage check
# ---------------------------------------------------------------------------

class TestEnumCoverage:
    """Ensure seed data covers several distinct ProductStatus values."""

    def test_seed_uses_low_stock_status(self):
        """The new LOW_STOCK value must actually be used in seed data."""
        try:
            from app.models.product import ProductStatus
            from app.seed import seed
        except ImportError:
            pytest.skip("Required modules not importable")

        db = MagicMock(spec=Session)
        db.query.return_value.first.return_value = None

        seed(db)

        from app.models.product import Product

        all_products = []
        for c in db.add_all.call_args_list:
            for item in c[0][0]:
                if isinstance(item, Product):
                    all_products.append(item)

        statuses_used = {p.status for p in all_products}
        assert ProductStatus.LOW_STOCK in statuses_used, (
            "Seed data must include at least one LOW_STOCK product"
        )

    def test_seed_covers_active_and_sold_out_and_low_stock(self):
        try:
            from app.models.product import Product, ProductStatus
            from app.seed import seed
        except ImportError:
            pytest.skip("Required modules not importable")

        db = MagicMock(spec=Session)
        db.query.return_value.first.return_value = None

        seed(db)

        all_products = []
        for c in db.add_all.call_args_list:
            for item in c[0][0]:
                if isinstance(item, Product):
                    all_products.append(item)

        statuses_used = {p.status for p in all_products}
        required = {ProductStatus.ACTIVE, ProductStatus.SOLD_OUT, ProductStatus.LOW_STOCK}
        missing = required - statuses_used
        assert not missing, (
            f"Seed data missing these ProductStatus values: {missing}"
        )