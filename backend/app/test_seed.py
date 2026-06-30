"""Tests for backend/app/seed.py - verifying brand_id field handling."""

import pytest
from unittest.mock import MagicMock, patch, call
from sqlalchemy.orm import Session

from app.models.product import Product, ProductStatus


class TestProductBrandIdField:
    """Tests for the newly added brand_id field on Product model."""

    def test_product_accepts_brand_id_integer(self):
        """Test that Product correctly accepts an integer brand_id."""
        product = Product(
            name="Test Product",
            category="Test Category",
            price=10000,
            stock=5,
            status=ProductStatus.ACTIVE,
            brand_id=1,
        )
        assert product.brand_id == 1

    def test_product_accepts_brand_id_none(self):
        """Test that Product correctly accepts None for brand_id (nullable)."""
        product = Product(
            name="Test Product",
            category="Test Category",
            price=10000,
            stock=5,
            status=ProductStatus.ACTIVE,
            brand_id=None,
        )
        assert product.brand_id is None

    def test_product_brand_id_defaults_to_none_when_not_provided(self):
        """Test that brand_id is None when not explicitly provided."""
        product = Product(
            name="Test Product",
            category="Test Category",
            price=10000,
            stock=5,
            status=ProductStatus.ACTIVE,
        )
        assert product.brand_id is None

    def test_product_brand_id_is_nullable(self):
        """Test that brand_id column is nullable (Optional[int])."""
        # Verify the column accepts None without raising
        product = Product(brand_id=None)
        assert product.brand_id is None

    def test_product_brand_id_accepts_various_integer_values(self):
        """Test that brand_id accepts various positive integer values."""
        for brand_id in [1, 2, 100, 999, 99999]:
            product = Product(
                name=f"Product {brand_id}",
                category="Test",
                price=1000,
                stock=1,
                status=ProductStatus.ACTIVE,
                brand_id=brand_id,
            )
            assert product.brand_id == brand_id

    def test_product_brand_id_type_is_int_or_none(self):
        """Test that brand_id stores an integer value correctly."""
        product = Product(brand_id=42)
        assert isinstance(product.brand_id, int)
        assert product.brand_id == 42


class TestSeedBrandIdValues:
    """Tests for seed data using brand_id field."""

    def test_keyboard_has_brand_id_1(self):
        """Test that keyboard product is created with brand_id=1."""
        keyboard = Product(
            name="무선 키보드",
            category="주변기기",
            price=39000,
            stock=12,
            status=ProductStatus.ACTIVE,
            brand_id=1,
        )
        assert keyboard.brand_id == 1

    def test_mouse_has_brand_id_1(self):
        """Test that mouse product is created with brand_id=1."""
        mouse = Product(
            name="무선 마우스",
            category="주변기기",
            price=25000,
            stock=30,
            status=ProductStatus.ACTIVE,
            brand_id=1,
        )
        assert mouse.brand_id == 1

    def test_monitor_has_brand_id_2(self):
        """Test that monitor product is created with brand_id=2."""
        monitor = Product(
            name="27인치 모니터",
            category="디스플레이",
            price=210000,
            stock=0,
            status=ProductStatus.SOLD_OUT,
            brand_id=2,
        )
        assert monitor.brand_id == 2

    def test_products_can_have_different_brand_ids(self):
        """Test that different products can have different brand_ids."""
        product1 = Product(name="P1", brand_id=1)
        product2 = Product(name="P2", brand_id=2)
        assert product1.brand_id != product2.brand_id

    def test_products_can_share_brand_id(self):
        """Test that multiple products can share the same brand_id."""
        keyboard = Product(name="무선 키보드", brand_id=1)
        mouse = Product(name="무선 마우스", brand_id=1)
        assert keyboard.brand_id == mouse.brand_id == 1


class TestSeedFunction:
    """Tests for the seed function behavior with brand_id."""

    def _make_mock_db(self, has_existing_user=False):
        """Helper to create a mock database session."""
        mock_db = MagicMock(spec=Session)
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query

        if has_existing_user:
            mock_query.first.return_value = MagicMock()
        else:
            mock_query.first.return_value = None

        return mock_db

    def test_seed_skips_if_users_exist(self):
        """Test that seed returns early if users already exist."""
        from app.seed import seed

        mock_db = self._make_mock_db(has_existing_user=True)
        seed(mock_db)

        mock_db.add_all.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_seed_calls_add_all_for_products(self):
        """Test that seed calls db.add_all with products including brand_id."""
        from app.seed import seed

        mock_db = self._make_mock_db(has_existing_user=False)

        with patch("app.seed.hash_password", return_value="hashed"):
            seed(mock_db)

        assert mock_db.add_all.call_count == 2
        mock_db.commit.assert_called_once()

    def test_seed_creates_products_with_brand_id(self):
        """Test that seed creates products with brand_id field populated."""
        from app.seed import seed

        mock_db = self._make_mock_db(has_existing_user=False)
        created_products = []

        original_add_all = mock_db.add_all.side_effect

        def capture_add_all(items):
            for item in items:
                if isinstance(item, Product):
                    created_products.append(item)

        mock_db.add_all.side_effect = capture_add_all

        with patch("app.seed.hash_password", return_value="hashed"):
            seed(mock_db)

        assert len(created_products) == 3

        brand_ids = [p.brand_id for p in created_products]
        assert 1 in brand_ids
        assert 2 in brand_ids

    def test_seed_keyboard_brand_id(self):
        """Test that keyboard in seed has brand_id=1."""
        from app.seed import seed

        mock_db = self._make_mock_db(has_existing_user=False)
        created_products = []

        def capture_add_all(items):
            for item in items:
                if isinstance(item, Product):
                    created_products.append(item)

        mock_db.add_all.side_effect = capture_add_all

        with patch("app.seed.hash_password", return_value="hashed"):
            seed(mock_db)

        keyboard = next((p for p in created_products if p.name == "무선 키보드"), None)
        assert keyboard is not None
        assert keyboard.brand_id == 1

    def test_seed_mouse_brand_id(self):
        """Test that mouse in seed has brand_id=1."""
        from app.seed import seed

        mock_db = self._make_mock_db(has_existing_user=False)
        created_products = []

        def capture_add_all(items):
            for item in items:
                if isinstance(item, Product):
                    created_products.append(item)

        mock_db.add_all.side_effect = capture_add_all

        with patch("app.seed.hash_password", return_value="hashed"):
            seed(mock_db)

        mouse = next((p for p in created_products if p.name == "무선 마우스"), None)
        assert mouse is not None
        assert mouse.brand_id == 1

    def test_seed_monitor_brand_id(self):
        """Test that monitor in seed has brand_id=2."""
        from app.seed import seed

        mock_db = self._make_mock_db(has_existing_user=False)
        created_products = []

        def capture_add_all(items):
            for item in items:
                if isinstance(item, Product):
                    created_products.append(item)

        mock_db.add_all.side_effect = capture_add_all

        with patch("app.seed.hash_password", return_value="hashed"):
            seed(mock_db)

        monitor = next((p for p in created_products if p.name == "27인치 모니터"), None)
        assert monitor is not None
        assert monitor.brand_id == 2

    def test_seed_flushes_before_order_creation(self):
        """Test that seed flushes after adding products (before creating order)."""
        from app.seed import seed

        mock_db = self._make_mock_db(has_existing_user=False)

        with patch("app.seed.hash_password", return_value="hashed"):
            seed(mock_db)

        mock_db.flush.assert_called_once()

    def test_seed_commits_at_end(self):
        """Test that seed commits at the end."""
        from app.seed import seed

        mock_db = self._make_mock_db(has_existing_user=False)

        with patch("app.seed.hash_password", return_value="hashed"):
            seed(mock_db)

        mock_db.commit.assert_called_once()


class TestBrandIdBackwardCompatibility:
    """Tests for backward compatibility of the brand_id field."""

    def test_product_without_brand_id_does_not_raise(self):
        """Test that creating a Product without brand_id does not raise an error."""
        try:
            product = Product(
                name="Old Product",
                category="Test",
                price=10000,
                stock=1,
                status=ProductStatus.ACTIVE,
            )
        except TypeError as e:
            pytest.fail(f"Creating Product without brand_id raised TypeError: {e}")

    def test_product_with_brand_id_none_does_not_raise(self):
        """Test that creating a Product with brand_id=None does not raise an error."""
        try:
            product = Product(
                name="Product With None Brand",
                category="Test",
                price=10000,
                stock=1,
                status=ProductStatus.ACTIVE,
                brand_id=None,
            )
            assert product.brand_id is None
        except (TypeError, ValueError) as e:
            pytest.fail(f"Creating Product with brand_id=None raised an error: {e}")

    def test_product_brand_id_field_exists(self):
        """Test that the brand_id field exists on the Product model."""
        product = Product()
        assert hasattr(product, "brand_id"), "Product model must have brand_id attribute"

    def test_product_with_string_brand_id_type_annotation(self):
        """
        Test that brand_id accepts int-compatible values.
        The type annotation is Mapped[int | None] so it should accept integers.
        """
        product = Product(brand_id=10)
        assert product.brand_id == 10
        assert isinstance(product.brand_id, int)

    def test_product_brand_id_is_not_required(self):
        """Test that brand_id is not a required field (nullable=True)."""
        # Should not raise any exception
        product = Product(name="Test")
        # brand_id should be None by default since it's nullable
        assert product.brand_id is None

    def test_product_can_update_brand_id(self):
        """Test that brand_id can be updated after creation."""
        product = Product(name="Test Product", brand_id=1)
        assert product.brand_id == 1

        product.brand_id = 2
        assert product.brand_id == 2

        product.brand_id = None
        assert product.brand_id is None

    def test_product_brand_id_zero_is_valid_integer(self):
        """Test that brand_id=0 is accepted as a valid integer."""
        product = Product(brand_id=0)
        assert product.brand_id == 0

    def test_multiple_products_independent_brand_ids(self):
        """Test that changing brand_id on one product doesn't affect another."""
        product1 = Product(name="Product 1", brand_id=1)
        product2 = Product(name="Product 2", brand_id=1)

        product1.brand_id = 3

        assert product1.brand_id == 3
        assert product2.brand_id == 1


class TestProductModelStructure:
    """Tests for the overall Product model structure with the new brand_id field."""

    def test_product_has_all_expected_fields(self):
        """Test that Product model has all expected fields including brand_id."""
        product = Product(
            name="Complete Product",
            category="Electronics",
            price=50000,
            stock=10,
            status=ProductStatus.ACTIVE,
            brand_id=5,
        )
        assert product.name == "Complete Product"
        assert product.category == "Electronics"
        assert product.price == 50000
        assert product.stock == 10
        assert product.status == ProductStatus.ACTIVE
        assert product.brand_id == 5

    def test_product_brand_id_stored_correctly(self):
        """Test that brand_id is stored and retrieved correctly."""
        brand_id_value = 42
        product = Product(brand_id=brand_id_value)
        assert product.brand_id == brand_id_value

    def test_seed_products_brand_id_are_integers_or_none(self):
        """Test that brand_id values used in seed are all integers or None."""
        seed_products = [
            Product(name="무선 키보드", brand_id=1),
            Product(name="무선 마우스", brand_id=1),
            Product(name="27인치 모니터", brand_id=2),
        ]

        for product in seed_products:
            assert product.brand_id is None or isinstance(product.brand_id, int), (
                f"Product '{product.name}' has brand_id of type "
                f"{type(product.brand_id)}, expected int or None"
            )