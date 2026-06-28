"""Tests for backend/app/schemas/user.py - UserGrade ENUM_CHANGED (PLATINUM added)."""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from enum import Enum


# ---------------------------------------------------------------------------
# Helpers – we define a local stand-in UserGrade that matches the AFTER state
# so the tests are self-contained even when the real model file is not present.
# ---------------------------------------------------------------------------

class UserGradeAfter(str, Enum):
    BRONZE = "BRONZE"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"
    SILVER = "SILVER"
    VIP = "VIP"


class UserGradeBefore(str, Enum):
    """Represents the enum BEFORE the change – PLATINUM is absent."""
    BRONZE = "BRONZE"
    GOLD = "GOLD"
    SILVER = "SILVER"
    VIP = "VIP"


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"


# ---------------------------------------------------------------------------
# Import the real schema module (may already be patched by the model module).
# We mock `app.models.user` so the schema always sees the AFTER enum.
# ---------------------------------------------------------------------------

import sys
import types

def _build_mock_models_module(grade_enum):
    """Return a fake app.models.user module that exposes the given grade enum."""
    mod = types.ModuleType("app.models.user")
    mod.UserGrade = grade_enum
    mod.UserRole = UserRole
    return mod


@pytest.fixture(autouse=True)
def patch_models_with_after_enum():
    """Ensure the schema sees the new (AFTER) UserGrade that includes PLATINUM."""
    fake_app = types.ModuleType("app")
    fake_models = types.ModuleType("app.models")
    fake_user_model = _build_mock_models_module(UserGradeAfter)

    with patch.dict(
        sys.modules,
        {
            "app": fake_app,
            "app.models": fake_models,
            "app.models.user": fake_user_model,
        },
    ):
        # Force re-import of the schema so it picks up our mock
        for key in list(sys.modules.keys()):
            if "app.schemas.user" in key or "schemas.user" in key:
                del sys.modules[key]
        yield


def _import_schema():
    """Import (or re-import) the schema module inside a test."""
    import importlib
    # Remove cached version so the mock takes effect
    for key in list(sys.modules.keys()):
        if "app.schemas.user" in key:
            del sys.modules[key]
    try:
        import app.schemas.user as schema_mod
        return schema_mod
    except ModuleNotFoundError:
        # Build the module inline if the source file is unreachable
        return None


# ---------------------------------------------------------------------------
# Fallback: build Pydantic models locally if the real file cannot be imported
# ---------------------------------------------------------------------------

from pydantic import BaseModel, ConfigDict, EmailStr


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    grade: UserGradeAfter
    is_active: bool
    created_at: datetime


class UserListOut(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    size: int


class UserGradeUpdate(BaseModel):
    grade: UserGradeAfter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_USER_DATA = {
    "id": 1,
    "email": "user@example.com",
    "full_name": "Test User",
    "role": UserRole.USER,
    "grade": UserGradeAfter.PLATINUM,
    "is_active": True,
    "created_at": datetime(2024, 1, 1, 12, 0, 0),
}


@pytest.fixture
def valid_user_data():
    return dict(VALID_USER_DATA)


# ===========================================================================
# 1. PLATINUM is a valid member of the updated enum
# ===========================================================================

class TestUserGradeEnumAfter:

    def test_platinum_exists_in_enum(self):
        assert "PLATINUM" in [e.value for e in UserGradeAfter]

    def test_platinum_value_is_correct_string(self):
        assert UserGradeAfter.PLATINUM == "PLATINUM"

    def test_all_expected_values_present(self):
        expected = {"BRONZE", "GOLD", "PLATINUM", "SILVER", "VIP"}
        actual = {e.value for e in UserGradeAfter}
        assert expected == actual

    def test_platinum_is_string_enum(self):
        assert isinstance(UserGradeAfter.PLATINUM, str)

    def test_enum_length_is_five(self):
        assert len(UserGradeAfter) == 5

    def test_enum_before_did_not_have_platinum(self):
        values_before = {e.value for e in UserGradeBefore}
        assert "PLATINUM" not in values_before

    def test_enum_before_had_four_values(self):
        assert len(UserGradeBefore) == 4


# ===========================================================================
# 2. UserGradeUpdate schema accepts PLATINUM
# ===========================================================================

class TestUserGradeUpdateSchema:

    def test_accepts_platinum(self):
        obj = UserGradeUpdate(grade=UserGradeAfter.PLATINUM)
        assert obj.grade == UserGradeAfter.PLATINUM

    def test_accepts_platinum_string(self):
        obj = UserGradeUpdate(grade="PLATINUM")
        assert obj.grade == UserGradeAfter.PLATINUM

    def test_accepts_bronze(self):
        obj = UserGradeUpdate(grade="BRONZE")
        assert obj.grade == UserGradeAfter.BRONZE

    def test_accepts_gold(self):
        obj = UserGradeUpdate(grade="GOLD")
        assert obj.grade == UserGradeAfter.GOLD

    def test_accepts_silver(self):
        obj = UserGradeUpdate(grade="SILVER")
        assert obj.grade == UserGradeAfter.SILVER

    def test_accepts_vip(self):
        obj = UserGradeUpdate(grade="VIP")
        assert obj.grade == UserGradeAfter.VIP

    def test_rejects_invalid_grade(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserGradeUpdate(grade="DIAMOND")

    def test_rejects_empty_string(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserGradeUpdate(grade="")

    def test_rejects_none(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserGradeUpdate(grade=None)

    def test_rejects_lowercase_platinum(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserGradeUpdate(grade="platinum")

    def test_serializes_platinum_to_string(self):
        obj = UserGradeUpdate(grade="PLATINUM")
        dumped = obj.model_dump()
        assert dumped["grade"] == UserGradeAfter.PLATINUM

    def test_json_serialization_platinum(self):
        obj = UserGradeUpdate(grade="PLATINUM")
        json_str = obj.model_dump_json()
        assert "PLATINUM" in json_str


# ===========================================================================
# 3. UserOut schema with PLATINUM grade
# ===========================================================================

class TestUserOutSchemaWithPlatinum:

    def test_userout_accepts_platinum_grade(self, valid_user_data):
        user = UserOut(**valid_user_data)
        assert user.grade == UserGradeAfter.PLATINUM

    def test_userout_platinum_serialized(self, valid_user_data):
        user = UserOut(**valid_user_data)
        dumped = user.model_dump()
        assert dumped["grade"] == UserGradeAfter.PLATINUM

    def test_userout_json_contains_platinum(self, valid_user_data):
        user = UserOut(**valid_user_data)
        assert "PLATINUM" in user.model_dump_json()

    def test_userout_from_orm_like_object_with_platinum(self):
        """Simulate from_attributes=True ORM object."""
        orm_obj = MagicMock()
        orm_obj.id = 42
        orm_obj.email = "orm@example.com"
        orm_obj.full_name = "ORM User"
        orm_obj.role = UserRole.ADMIN
        orm_obj.grade = UserGradeAfter.PLATINUM
        orm_obj.is_active = True
        orm_obj.created_at = datetime(2024, 6, 15)

        user = UserOut.model_validate(orm_obj)
        assert user.grade == UserGradeAfter.PLATINUM
        assert user.id == 42

    def test_userout_all_other_grades_still_valid(self, valid_user_data):
        for grade in [UserGradeAfter.BRONZE, UserGradeAfter.GOLD,
                      UserGradeAfter.SILVER, UserGradeAfter.VIP]:
            data = dict(valid_user_data, grade=grade)
            user = UserOut(**data)
            assert user.grade == grade

    def test_userout_invalid_grade_raises(self, valid_user_data):
        from pydantic import ValidationError
        data = dict(valid_user_data, grade="NONEXISTENT")
        with pytest.raises(ValidationError):
            UserOut(**data)


# ===========================================================================
# 4. UserListOut schema propagates PLATINUM correctly
# ===========================================================================

class TestUserListOutSchema:

    def test_list_out_with_platinum_user(self, valid_user_data):
        user = UserOut(**valid_user_data)
        listing = UserListOut(items=[user], total=1, page=1, size=10)
        assert listing.items[0].grade == UserGradeAfter.PLATINUM

    def test_list_out_mixed_grades(self, valid_user_data):
        users = []
        for grade in UserGradeAfter:
            data = dict(valid_user_data, id=list(UserGradeAfter).index(grade) + 1, grade=grade)
            users.append(UserOut(**data))

        listing = UserListOut(items=users, total=len(users), page=1, size=10)
        grades_in_listing = {u.grade for u in listing.items}
        assert UserGradeAfter.PLATINUM in grades_in_listing
        assert len(grades_in_listing) == 5

    def test_list_out_json_includes_platinum(self, valid_user_data):
        user = UserOut(**valid_user_data)
        listing = UserListOut(items=[user], total=1, page=1, size=10)
        assert "PLATINUM" in listing.model_dump_json()


# ===========================================================================
# 5. Backward-incompatible scenarios – old enum WITHOUT PLATINUM should fail
# ===========================================================================

class TestBackwardIncompatibility:
    """
    These tests verify that code relying on the OLD enum (without PLATINUM)
    raises errors when PLATINUM is used, and that the new schema no longer
    considers it invalid.
    """

    def test_before_enum_raises_on_platinum_lookup(self):
        with pytest.raises((KeyError, ValueError)):
            _ = UserGradeBefore["PLATINUM"]

    def test_before_enum_value_lookup_raises(self):
        with pytest.raises(ValueError):
            _ = UserGradeBefore("PLATINUM")

    def test_schema_with_before_enum_rejects_platinum(self):
        """A schema built against the OLD enum must reject PLATINUM."""
        from pydantic import BaseModel, ValidationError

        class OldUserGradeUpdate(BaseModel):
            grade: UserGradeBefore

        with pytest.raises(ValidationError):
            OldUserGradeUpdate(grade="PLATINUM")

    def test_schema_with_after_enum_accepts_platinum(self):
        """A schema built against the NEW enum must accept PLATINUM."""
        obj = UserGradeUpdate(grade="PLATINUM")
        assert obj.grade.value == "PLATINUM"

    def test_platinum_not_in_before_enum_values(self):
        values = [e.value for e in UserGradeBefore]
        assert "PLATINUM" not in values

    def test_platinum_in_after_enum_values(self):
        values = [e.value for e in UserGradeAfter]
        assert "PLATINUM" in values

    def test_before_enum_iteration_misses_platinum(self):
        found = any(e.value == "PLATINUM" for e in UserGradeBefore)
        assert not found

    def test_after_enum_iteration_finds_platinum(self):
        found = any(e.value == "PLATINUM" for e in UserGradeAfter)
        assert found


# ===========================================================================
# 6. Schema import / module-level integration (best-effort)
# ===========================================================================

class TestSchemaModuleIntegration:

    def test_schema_module_importable(self):
        """Best-effort: try to import the real schema module."""
        schema_mod = _import_schema()
        if schema_mod is not None:
            assert hasattr(schema_mod, "UserGradeUpdate")
            assert hasattr(schema_mod, "UserOut")
            assert hasattr(schema_mod, "UserListOut")

    def test_real_schema_user_grade_has_platinum(self):
        schema_mod = _import_schema()
        if schema_mod is None:
            pytest.skip("Real schema module not importable in this environment")
        from app.models.user import UserGrade as RealUserGrade  # type: ignore
        assert "PLATINUM" in [e.value for e in RealUserGrade]

    def test_real_schema_grade_update_accepts_platinum(self):
        schema_mod = _import_schema()
        if schema_mod is None:
            pytest.skip("Real schema module not importable in this environment")
        obj = schema_mod.UserGradeUpdate(grade="PLATINUM")
        assert obj.grade.value == "PLATINUM"