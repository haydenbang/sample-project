"""Tests for product schema changes - brand_id field addition."""

import pytest
from pydantic import ValidationError

from app.schemas.product import ProductBase, ProductCreate, ProductUpdate, ProductOut, ProductListOut
from app.models.product import ProductStatus


# ---------------------------------------------------------------------------
# ProductBase tests
# ---------------------------------------------------------------------------

class TestProductBaseBrandId:
    """Tests for brand_id field in ProductBase."""

    def test_brand_id_defaults_to_none(self):
        """brand_id should default to None when not provided."""
        product = ProductBase(name="Test Product", category="Electronics", price=100)
        assert product.brand_id is None

    def test_brand_id_accepts_valid_integer(self):
        """brand_id should accept a valid positive integer."""
        product = ProductBase(name="Test Product", category="Electronics", price=100, brand_id=42)
        assert product.brand_id == 42

    def test_brand_id_accepts_none_explicitly(self):
        """brand_id should accept explicit None."""
        product = ProductBase(name="Test Product", category="Electronics", price=100, brand_id=None)
        assert product.brand_id is None

    def test_brand_id_accepts_zero(self):
        """brand_id should accept 0 as a valid integer."""
        product = ProductBase(name="Test Product", category="Electronics", price=100, brand_id=0)
        assert product.brand_id == 0

    def test_brand_id_accepts_large_integer(self):
        """brand_id should accept large integers."""
        product = ProductBase(name="Test Product", category="Electronics", price=100, brand_id=999999)
        assert product.brand_id == 999999

    def test_brand_id_rejects_string(self):
        """brand_id should reject non-numeric string values."""
        with pytest.raises(ValidationError) as exc_info:
            ProductBase(name="Test Product", category="Electronics", price=100, brand_id="not_an_int")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("brand_id",) for e in errors)

    def test_brand_id_rejects_float_string(self):
        """brand_id should reject float string values."""
        with pytest.raises(ValidationError) as exc_info:
            ProductBase(name="Test Product", category="Electronics", price=100, brand_id="1.5")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("brand_id",) for e in errors)

    def test_brand_id_type_annotation_is_optional_int(self):
        """brand_id field should be typed as int | None."""
        import inspect
        fields = ProductBase.model_fields
        assert "brand_id" in fields
        field = fields["brand_id"]
        # The field should be optional (allow None)
        assert field.is_required() is False

    def test_product_base_serialization_includes_brand_id(self):
        """Serialized dict should include brand_id."""
        product = ProductBase(name="Test Product", category="Electronics", price=100, brand_id=5)
        data = product.model_dump()
        assert "brand_id" in data
        assert data["brand_id"] == 5

    def test_product_base_serialization_brand_id_none(self):
        """Serialized dict should include brand_id=None when not set."""
        product = ProductBase(name="Test Product", category="Electronics", price=100)
        data = product.model_dump()
        assert "brand_id" in data
        assert data["brand_id"] is None

    def test_product_base_json_serialization_includes_brand_id(self):
        """JSON serialization should include brand_id field."""
        product = ProductBase(name="Test Product", category="Electronics", price=100, brand_id=10)
        json_data = product.model_dump(mode="json")
        assert "brand_id" in json_data
        assert json_data["brand_id"] == 10

    def test_product_base_json_serialization_brand_id_null(self):
        """JSON serialization should include brand_id as null when None."""
        product = ProductBase(name="Test Product", category="Electronics", price=100)
        json_data = product.model_dump(mode="json")
        assert "brand_id" in json_data
        assert json_data["brand_id"] is None


# ---------------------------------------------------------------------------
# ProductCreate tests
# ---------------------------------------------------------------------------

class TestProductCreateBrandId:
    """Tests for brand_id field in ProductCreate (inherits from ProductBase)."""

    def test_product_create_inherits_brand_id(self):
        """ProductCreate should inherit brand_id from ProductBase."""
        product = ProductCreate(name="New Product", category="Books", price=50, brand_id=7)
        assert product.brand_id == 7

    def test_product_create_brand_id_optional(self):
        """ProductCreate brand_id should be optional."""
        product = ProductCreate(name="New Product", category="Books", price=50)
        assert product.brand_id is None

    def test_product_create_brand_id_none_explicit(self):
        """ProductCreate brand_id should accept explicit None."""
        product = ProductCreate(name="New Product", category="Books", price=50, brand_id=None)
        assert product.brand_id is None

    def test_product_create_full_payload(self):
        """ProductCreate should work with all fields including brand_id."""
        product = ProductCreate(
            name="Full Product",
            category="Electronics",
            price=299,
            stock=10,
            brand_id=100
        )
        assert product.name == "Full Product"
        assert product.brand_id == 100
        assert product.stock == 10

    def test_product_create_brand_id_in_dict(self):
        """brand_id should appear in the serialized dict for ProductCreate."""
        product = ProductCreate(name="New Product", category="Books", price=50, brand_id=3)
        data = product.model_dump()
        assert data["brand_id"] == 3

    def test_product_create_rejects_invalid_brand_id(self):
        """ProductCreate should reject invalid brand_id types."""
        with pytest.raises(ValidationError):
            ProductCreate(name="New Product", category="Books", price=50, brand_id="invalid")


# ---------------------------------------------------------------------------
# ProductUpdate tests
# ---------------------------------------------------------------------------

class TestProductUpdateBrandId:
    """Tests for brand_id field in ProductUpdate."""

    def test_product_update_has_brand_id_field(self):
        """ProductUpdate should have brand_id field."""
        fields = ProductUpdate.model_fields
        assert "brand_id" in fields

    def test_product_update_brand_id_defaults_to_none(self):
        """ProductUpdate brand_id should default to None."""
        update = ProductUpdate()
        assert update.brand_id is None

    def test_product_update_brand_id_accepts_integer(self):
        """ProductUpdate should accept integer brand_id."""
        update = ProductUpdate(brand_id=15)
        assert update.brand_id == 15

    def test_product_update_brand_id_accepts_none(self):
        """ProductUpdate should accept None for brand_id."""
        update = ProductUpdate(brand_id=None)
        assert update.brand_id is None

    def test_product_update_brand_id_only(self):
        """ProductUpdate should work with only brand_id specified."""
        update = ProductUpdate(brand_id=20)
        data = update.model_dump(exclude_none=True)
        assert data == {"brand_id": 20}

    def test_product_update_brand_id_with_other_fields(self):
        """ProductUpdate brand_id should coexist with other update fields."""
        update = ProductUpdate(name="Updated Name", price=199, brand_id=30)
        assert update.name == "Updated Name"
        assert update.price == 199
        assert update.brand_id == 30

    def test_product_update_rejects_string_brand_id(self):
        """ProductUpdate should reject non-integer brand_id."""
        with pytest.raises(ValidationError) as exc_info:
            ProductUpdate(brand_id="bad_value")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("brand_id",) for e in errors)

    def test_product_update_brand_id_serialization(self):
        """Serialized ProductUpdate should include brand_id."""
        update = ProductUpdate(brand_id=25)
        data = update.model_dump()
        assert "brand_id" in data
        assert data["brand_id"] == 25

    def test_product_update_brand_id_none_in_dump(self):
        """Serialized ProductUpdate should include brand_id=None when not set."""
        update = ProductUpdate(price=100)
        data = update.model_dump()
        assert "brand_id" in data
        assert data["brand_id"] is None


# ---------------------------------------------------------------------------
# ProductOut tests
# ---------------------------------------------------------------------------

class TestProductOutBrandId:
    """Tests for brand_id field in ProductOut."""

    def _make_product_out_dict(self, **kwargs):
        defaults = {
            "id": 1,
            "name": "Test Product",
            "category": "Electronics",
            "price": 100,
            "stock": 5,
            "status": ProductStatus.active,
        }
        defaults.update(kwargs)
        return defaults

    def test_product_out_has_brand_id_field(self):
        """ProductOut should have brand_id field."""
        fields = ProductOut.model_fields
        assert "brand_id" in fields

    def test_product_out_brand_id_none(self):
        """ProductOut should accept brand_id=None."""
        data = self._make_product_out_dict(brand_id=None)
        product = ProductOut(**data)
        assert product.brand_id is None

    def test_product_out_brand_id_integer(self):
        """ProductOut should accept integer brand_id."""
        data = self._make_product_out_dict(brand_id=55)
        product = ProductOut(**data)
        assert product.brand_id == 55

    def test_product_out_brand_id_default_none(self):
        """ProductOut should default brand_id to None if not provided."""
        data = self._make_product_out_dict()
        product = ProductOut(**data)
        assert product.brand_id is None

    def test_product_out_from_attributes(self):
        """ProductOut should support from_attributes (ORM mode)."""

        class MockProduct:
            id = 1
            name = "ORM Product"
            category = "Electronics"
            price = 200
            stock = 3
            status = ProductStatus.active
            brand_id = 77

        product = ProductOut.model_validate(MockProduct())
        assert product.brand_id == 77

    def test_product_out_from_attributes_brand_id_none(self):
        """ProductOut from ORM model with brand_id=None."""

        class MockProduct:
            id = 2
            name = "ORM Product No Brand"
            category = "Electronics"
            price = 200
            stock = 3
            status = ProductStatus.active
            brand_id = None

        product = ProductOut.model_validate(MockProduct())
        assert product.brand_id is None

    def test_product_out_serialization_includes_brand_id(self):
        """ProductOut serialization should include brand_id."""
        data = self._make_product_out_dict(brand_id=88)
        product = ProductOut(**data)
        serialized = product.model_dump()
        assert "brand_id" in serialized
        assert serialized["brand_id"] == 88

    def test_product_out_rejects_string_brand_id(self):
        """ProductOut should reject non-integer brand_id."""
        data = self._make_product_out_dict(brand_id="not_an_int")
        with pytest.raises(ValidationError) as exc_info:
            ProductOut(**data)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("brand_id",) for e in errors)


# ---------------------------------------------------------------------------
# ProductListOut tests
# ---------------------------------------------------------------------------

class TestProductListOutBrandId:
    """Tests for brand_id field in ProductListOut via nested ProductOut."""

    def _make_product_out(self, brand_id=None):
        return ProductOut(
            id=1,
            name="Test Product",
            category="Electronics",
            price=100,
            stock=5,
            status=ProductStatus.active,
            brand_id=brand_id,
        )

    def test_product_list_out_contains_brand_id(self):
        """ProductListOut items should contain brand_id."""
        items = [self._make_product_out(brand_id=10)]
        list_out = ProductListOut(items=items, total=1, page=1, size=10)
        assert list_out.items[0].brand_id == 10

    def test_product_list_out_brand_id_none(self):
        """ProductListOut items should support brand_id=None."""
        items = [self._make_product_out(brand_id=None)]
        list_out = ProductListOut(items=items, total=1, page=1, size=10)
        assert list_out.items[0].brand_id is None

    def test_product_list_out_mixed_brand_ids(self):
        """ProductListOut should handle a mix of brand_id values."""
        items = [
            self._make_product_out(brand_id=1),
            self._make_product_out(brand_id=None),
            self._make_product_out(brand_id=99),
        ]
        list_out = ProductListOut(items=items, total=3, page=1, size=10)
        assert list_out.items[0].brand_id == 1
        assert list_out.items[1].brand_id is None
        assert list_out.items[2].brand_id == 99

    def test_product_list_out_serialization(self):
        """ProductListOut serialization should include brand_id in items."""
        items = [self._make_product_out(brand_id=42)]
        list_out = ProductListOut(items=items, total=1, page=1, size=10)
        data = list_out.model_dump()
        assert "brand_id" in data["items"][0]
        assert data["items"][0]["brand_id"] == 42


# ---------------------------------------------------------------------------
# Backward compatibility / edge case tests
# ---------------------------------------------------------------------------

class TestBrandIdBackwardCompatibility:
    """Tests ensuring existing code without brand_id still works."""

    def test_product_base_without_brand_id_still_valid(self):
        """Existing code that doesn't pass brand_id should still work."""
        product = ProductBase(name="Legacy Product", category="Books", price=10)
        assert product.brand_id is None

    def test_product_create_without_brand_id_still_valid(self):
        """ProductCreate without brand_id should still be valid."""
        product = ProductCreate(name="Legacy Product", category="Books", price=10)
        assert product.brand_id is None

    def test_product_update_empty_still_valid(self):
        """Empty ProductUpdate (all None) should still be valid."""
        update = ProductUpdate()
        assert update.brand_id is None

    def test_product_out_without_brand_id_in_payload(self):
        """ProductOut should still construct if brand_id absent (defaults None)."""
        product = ProductOut(
            id=1,
            name="Test",
            category="Cat",
            price=10,
            stock=0,
            status=ProductStatus.active,
        )
        assert product.brand_id is None

    def test_brand_id_field_is_nullable_type(self):
        """brand_id field annotation should be int | None (nullable)."""
        import typing
        fields = ProductBase.model_fields
        brand_id_field = fields["brand_id"]
        # Pydantic stores annotation; verify None is allowed by checking default
        assert brand_id_field.default is None