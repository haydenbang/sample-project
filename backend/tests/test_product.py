"""Tests for ProductStatus enum change - addition of LOW_STOCK value."""

import pytest
from enum import Enum
from unittest.mock import patch, MagicMock
import sys
import types


# ---------------------------------------------------------------------------
# Helpers to build a minimal fake app.models.product with the NEW enum
# ---------------------------------------------------------------------------

def _make_product_status_enum(values):
    """Dynamically create a ProductStatus enum with given values."""
    return Enum("ProductStatus", {v: v for v in values})


OLD_VALUES = ["ACTIVE", "ARCHIVED", "DRAFT", "SOLD_OUT"]
NEW_VALUES = ["ACTIVE", "ARCHIVED", "DRAFT", "LOW_STOCK", "SOLD_OUT"]


def _install_model_module(enum_values):
    """
    Install a fake `app.models.product` module into sys.modules so that
    `app.schemas.product` picks it up when imported.
    Returns the ProductStatus enum used.
    """
    product_status = _make_product_status_enum(enum_values)

    # Build fake module hierarchy
    for mod_name in ("app", "app.models", "app.models.product",
                     "app.schemas", "app.schemas.product"):
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)

    sys.modules["app.models.product"].ProductStatus = product_status
    return product_status


def _load_schema_module(product_status_enum):
    """
    (Re-)load app.schemas.product with the given ProductStatus enum injected.
    Returns the module.
    """
    # Remove cached schema module so re-import picks up new enum
    for key in list(sys.modules.keys()):
        if "app.schemas.product" in key:
            del sys.modules[key]

    # Patch the model module's enum
    sys.modules["app.models.product"].ProductStatus = product_status_enum

    # Now import the schema using importlib to get a fresh copy
    import importlib
    schema_mod = importlib.import_module("app.schemas.product")
    return schema_mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def setup_app_package():
    """Ensure the fake app package exists for the whole session."""
    _install_model_module(NEW_VALUES)
    yield


@pytest.fixture()
def new_product_status():
    return _make_product_status_enum(NEW_VALUES)


@pytest.fixture()
def old_product_status():
    return _make_product_status_enum(OLD_VALUES)


@pytest.fixture()
def schema_module(new_product_status):
    """Load schema module backed by the NEW enum (with LOW_STOCK)."""
    return _load_schema_module(new_product_status)


@pytest.fixture()
def schema_module_old(old_product_status):
    """Load schema module backed by the OLD enum (without LOW_STOCK)."""
    return _load_schema_module(old_product_status)


# ---------------------------------------------------------------------------
# 1. Enum structure tests
# ---------------------------------------------------------------------------

class TestProductStatusEnumStructure:
    def test_new_enum_has_low_stock(self, new_product_status):
        assert "LOW_STOCK" in new_product_status.__members__

    def test_new_enum_has_all_old_values(self, new_product_status):
        for v in OLD_VALUES:
            assert v in new_product_status.__members__, f"{v} missing from new enum"

    def test_new_enum_total_count(self, new_product_status):
        assert len(new_product_status) == 5

    def test_old_enum_does_not_have_low_stock(self, old_product_status):
        assert "LOW_STOCK" not in old_product_status.__members__

    def test_old_enum_total_count(self, old_product_status):
        assert len(old_product_status) == 4

    def test_low_stock_value(self, new_product_status):
        assert new_product_status["LOW_STOCK"].value == "LOW_STOCK"

    def test_all_expected_values_present(self, new_product_status):
        expected = {"ACTIVE", "ARCHIVED", "DRAFT", "LOW_STOCK", "SOLD_OUT"}
        actual = set(new_product_status.__members__.keys())
        assert actual == expected


# ---------------------------------------------------------------------------
# 2. ProductUpdate schema – new enum
# ---------------------------------------------------------------------------

class TestProductUpdateWithNewEnum:
    def test_update_status_low_stock_accepted(self, schema_module):
        ProductUpdate = schema_module.ProductUpdate
        obj = ProductUpdate(status="LOW_STOCK")
        assert obj.status.value == "LOW_STOCK"

    def test_update_status_active_accepted(self, schema_module):
        ProductUpdate = schema_module.ProductUpdate
        obj = ProductUpdate(status="ACTIVE")
        assert obj.status.value == "ACTIVE"

    def test_update_status_archived_accepted(self, schema_module):
        ProductUpdate = schema_module.ProductUpdate
        obj = ProductUpdate(status="ARCHIVED")
        assert obj.status.value == "ARCHIVED"

    def test_update_status_draft_accepted(self, schema_module):
        ProductUpdate = schema_module.ProductUpdate
        obj = ProductUpdate(status="DRAFT")
        assert obj.status.value == "DRAFT"

    def test_update_status_sold_out_accepted(self, schema_module):
        ProductUpdate = schema_module.ProductUpdate
        obj = ProductUpdate(status="SOLD_OUT")
        assert obj.status.value == "SOLD_OUT"

    def test_update_status_none_accepted(self, schema_module):
        ProductUpdate = schema_module.ProductUpdate
        obj = ProductUpdate(status=None)
        assert obj.status is None

    def test_update_status_invalid_raises(self, schema_module):
        ProductUpdate = schema_module.ProductUpdate
        with pytest.raises(Exception):  # pydantic ValidationError
            ProductUpdate(status="DISCONTINUED")

    def test_update_all_fields_none(self, schema_module):
        ProductUpdate = schema_module.ProductUpdate
        obj = ProductUpdate()
        assert obj.status is None
        assert obj.name is None
        assert obj.price is None

    def test_update_serializes_low_stock(self, schema_module):
        ProductUpdate = schema_module.ProductUpdate
        obj = ProductUpdate(status="LOW_STOCK")
        data = obj.model_dump()
        assert data["status"].value == "LOW_STOCK"

    def test_update_json_serialization_low_stock(self, schema_module):
        ProductUpdate = schema_module.ProductUpdate
        obj = ProductUpdate(status="LOW_STOCK")
        json_str = obj.model_dump_json()
        assert "LOW_STOCK" in json_str


# ---------------------------------------------------------------------------
# 3. ProductOut schema – new enum
# ---------------------------------------------------------------------------

class TestProductOutWithNewEnum:
    def _make_db_row(self, product_status_enum, **kwargs):
        """Create a mock ORM object."""
        defaults = dict(id=1, name="Widget", category="Tools",
                        price=999, stock=5,
                        status=product_status_enum["ACTIVE"])
        defaults.update(kwargs)
        row = MagicMock(**defaults)
        # Make attribute access work like an ORM model
        for k, v in defaults.items():
            setattr(row, k, v)
        return row

    def test_product_out_low_stock_from_orm(self, schema_module, new_product_status):
        ProductOut = schema_module.ProductOut
        row = self._make_db_row(new_product_status,
                                status=new_product_status["LOW_STOCK"])
        obj = ProductOut.model_validate(row)
        assert obj.status.value == "LOW_STOCK"

    def test_product_out_active_from_orm(self, schema_module, new_product_status):
        ProductOut = schema_module.ProductOut
        row = self._make_db_row(new_product_status,
                                status=new_product_status["ACTIVE"])
        obj = ProductOut.model_validate(row)
        assert obj.status.value == "ACTIVE"

    def test_product_out_sold_out_from_orm(self, schema_module, new_product_status):
        ProductOut = schema_module.ProductOut
        row = self._make_db_row(new_product_status,
                                status=new_product_status["SOLD_OUT"])
        obj = ProductOut.model_validate(row)
        assert obj.status.value == "SOLD_OUT"

    def test_product_out_serialization_includes_status(self, schema_module, new_product_status):
        ProductOut = schema_module.ProductOut
        row = self._make_db_row(new_product_status,
                                status=new_product_status["LOW_STOCK"])
        obj = ProductOut.model_validate(row)
        data = obj.model_dump()
        assert "status" in data

    def test_product_out_json_contains_low_stock(self, schema_module, new_product_status):
        ProductOut = schema_module.ProductOut
        row = self._make_db_row(new_product_status,
                                status=new_product_status["LOW_STOCK"])
        obj = ProductOut.model_validate(row)
        assert "LOW_STOCK" in obj.model_dump_json()

    def test_product_out_has_id_field(self, schema_module, new_product_status):
        ProductOut = schema_module.ProductOut
        row = self._make_db_row(new_product_status, id=42)
        obj = ProductOut.model_validate(row)
        assert obj.id == 42

    def test_product_out_has_correct_price(self, schema_module, new_product_status):
        ProductOut = schema_module.ProductOut
        row = self._make_db_row(new_product_status, price=1500)
        obj = ProductOut.model_validate(row)
        assert obj.price == 1500


# ---------------------------------------------------------------------------
# 4. ProductCreate / ProductBase – unchanged but smoke-tested
# ---------------------------------------------------------------------------

class TestProductCreateSmoke:
    def test_create_valid(self, schema_module):
        ProductCreate = schema_module.ProductCreate
        obj = ProductCreate(name="Widget", category="Tools", price=500, stock=10)
        assert obj.name == "Widget"

    def test_create_missing_name_raises(self, schema_module):
        ProductCreate = schema_module.ProductCreate
        with pytest.raises(Exception):
            ProductCreate(category="Tools", price=500)

    def test_create_negative_price_raises(self, schema_module):
        ProductCreate = schema_module.ProductCreate
        with pytest.raises(Exception):
            ProductCreate(name="Bad", category="Tools", price=-1)

    def test_create_zero_price_ok(self, schema_module):
        ProductCreate = schema_module.ProductCreate
        obj = ProductCreate(name="Free", category="Promo", price=0)
        assert obj.price == 0


# ---------------------------------------------------------------------------
# 5. ProductListOut – smoke test
# ---------------------------------------------------------------------------

class TestProductListOut:
    def _make_product_out(self, schema_module, new_product_status, status_key="ACTIVE"):
        ProductOut = schema_module.ProductOut
        row = MagicMock()
        row.id = 1
        row.name = "Widget"
        row.category = "Tools"
        row.price = 100
        row.stock = 5
        row.status = new_product_status[status_key]
        return ProductOut.model_validate(row)

    def test_list_out_with_low_stock_items(self, schema_module, new_product_status):
        ProductListOut = schema_module.ProductListOut
        item = self._make_product_out(schema_module, new_product_status, "LOW_STOCK")
        lst = ProductListOut(items=[item], total=1, page=1, size=10)
        assert lst.total == 1
        assert lst.items[0].status.value == "LOW_STOCK"

    def test_list_out_mixed_statuses(self, schema_module, new_product_status):
        ProductListOut = schema_module.ProductListOut
        items = [
            self._make_product_out(schema_module, new_product_status, s)
            for s in ["ACTIVE", "LOW_STOCK", "SOLD_OUT"]
        ]
        lst = ProductListOut(items=items, total=3, page=1, size=10)
        statuses = [i.status.value for i in lst.items]
        assert "LOW_STOCK" in statuses
        assert "ACTIVE" in statuses

    def test_list_out_empty(self, schema_module):
        ProductListOut = schema_module.ProductListOut
        lst = ProductListOut(items=[], total=0, page=1, size=10)
        assert lst.items == []
        assert lst.total == 0


# ---------------------------------------------------------------------------
# 6. Backward-incompatibility: OLD enum rejects LOW_STOCK
# ---------------------------------------------------------------------------

class TestBackwardIncompatibility:
    def test_old_enum_raises_for_low_stock(self, schema_module_old):
        ProductUpdate = schema_module_old.ProductUpdate
        with pytest.raises(Exception):
            ProductUpdate(status="LOW_STOCK")

    def test_old_enum_still_accepts_active(self, schema_module_old):
        ProductUpdate = schema_module_old.ProductUpdate
        obj = ProductUpdate(status="ACTIVE")
        assert obj.status.value == "ACTIVE"

    def test_old_enum_still_accepts_sold_out(self, schema_module_old):
        ProductUpdate = schema_module_old.ProductUpdate
        obj = ProductUpdate(status="SOLD_OUT")
        assert obj.status.value == "SOLD_OUT"

    def test_old_enum_raises_for_any_unknown_value(self, schema_module_old):
        ProductUpdate = schema_module_old.ProductUpdate
        for bad in ("LOW_STOCK", "PENDING", "EXPIRED", ""):
            with pytest.raises(Exception):
                ProductUpdate(status=bad)

    def test_old_schema_missing_low_stock_in_members(self, schema_module_old):
        ProductStatus = schema_module_old.ProductUpdate.__annotations__["status"]
        # The union includes None; drill into the enum args
        # Just confirm LOW_STOCK not reachable via old schema validation
        with pytest.raises(Exception):
            schema_module_old.ProductUpdate(status="LOW_STOCK")

    def test_new_schema_accepts_where_old_fails(self, schema_module, schema_module_old):
        """LOW_STOCK is accepted by new schema but rejected by old."""
        new_obj = schema_module.ProductUpdate(status="LOW_STOCK")
        assert new_obj.status.value == "LOW_STOCK"
        with pytest.raises(Exception):
            schema_module_old.ProductUpdate(status="LOW_STOCK")


# ---------------------------------------------------------------------------
# 7. Enum value equality and identity
# ---------------------------------------------------------------------------

class TestEnumValues:
    def test_low_stock_string_value(self, new_product_status):
        assert new_product_status.LOW_STOCK.value == "LOW_STOCK"

    def test_active_value_unchanged(self, new_product_status):
        assert new_product_status.ACTIVE.value == "ACTIVE"

    def test_archived_value_unchanged(self, new_product_status):
        assert new_product_status.ARCHIVED.value == "ARCHIVED"

    def test_draft_value_unchanged(self, new_product_status):
        assert new_product_status.DRAFT.value == "DRAFT"

    def test_sold_out_value_unchanged(self, new_product_status):
        assert new_product_status.SOLD_OUT.value == "SOLD_OUT"

    def test_enum_iteration_includes_low_stock(self, new_product_status):
        values = [m.value for m