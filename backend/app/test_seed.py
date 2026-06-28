"""Tests for seed.py verifying PLATINUM enum value and UserGrade schema changes."""

import pytest
from unittest.mock import MagicMock, patch, call
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers / stubs so tests run without a real database
# ---------------------------------------------------------------------------

class _FakeQuery:
    """Minimal query stub."""

    def __init__(self, first_result=None):
        self._first_result = first_result

    def first(self):
        return self._first_result


def _make_db(already_seeded: bool = False) -> MagicMock:
    db = MagicMock(spec=Session)
    db.query.return_value = _FakeQuery(first_result=object() if already_seeded else None)
    db.flush.return_value = None
    db.add_all.return_value = None
    db.add.return_value = None
    db.commit.return_value = None
    return db


# ---------------------------------------------------------------------------
# Tests for UserGrade enum values
# ---------------------------------------------------------------------------

class TestUserGradeEnum:
    """Verify the enum contains exactly the expected values after the change."""

    def test_platinum_value_exists(self):
        from app.models.user import UserGrade
        assert hasattr(UserGrade, "PLATINUM"), "PLATINUM must be a member of UserGrade"

    def test_bronze_value_exists(self):
        from app.models.user import UserGrade
        assert hasattr(UserGrade, "BRONZE")

    def test_gold_value_exists(self):
        from app.models.user import UserGrade
        assert hasattr(UserGrade, "GOLD")

    def test_silver_value_exists(self):
        from app.models.user import UserGrade
        assert hasattr(UserGrade, "SILVER")

    def test_vip_value_exists(self):
        from app.models.user import UserGrade
        assert hasattr(UserGrade, "VIP")

    def test_all_expected_values_present(self):
        from app.models.user import UserGrade
        expected = {"BRONZE", "GOLD", "PLATINUM", "SILVER", "VIP"}
        actual = {m.name for m in UserGrade}
        assert expected == actual, (
            f"UserGrade members mismatch. Expected {expected}, got {actual}"
        )

    def test_platinum_enum_value_string(self):
        """PLATINUM value should be a valid string (commonly its own name)."""
        from app.models.user import UserGrade
        assert isinstance(UserGrade.PLATINUM.value, str)
        assert UserGrade.PLATINUM.value != ""

    def test_no_extra_values(self):
        from app.models.user import UserGrade
        allowed = {"BRONZE", "GOLD", "PLATINUM", "SILVER", "VIP"}
        extras = {m.name for m in UserGrade} - allowed
        assert not extras, f"Unexpected extra enum members: {extras}"

    def test_platinum_is_distinct_from_other_grades(self):
        from app.models.user import UserGrade
        assert UserGrade.PLATINUM != UserGrade.GOLD
        assert UserGrade.PLATINUM != UserGrade.VIP
        assert UserGrade.PLATINUM != UserGrade.SILVER
        assert UserGrade.PLATINUM != UserGrade.BRONZE


# ---------------------------------------------------------------------------
# Tests for seed() function behaviour
# ---------------------------------------------------------------------------

class TestSeedFunction:
    """Verify seed() creates the right users, including the PLATINUM one."""

    def test_seed_skips_when_already_seeded(self):
        from app.seed import seed
        db = _make_db(already_seeded=True)
        seed(db)
        db.add_all.assert_not_called()
        db.commit.assert_not_called()

    def test_seed_calls_add_all_twice_and_add_once(self):
        from app.seed import seed
        db = _make_db(already_seeded=False)
        seed(db)
        assert db.add_all.call_count == 2, "add_all should be called for users and products"
        db.add.assert_called_once()

    def test_seed_commits_once(self):
        from app.seed import seed
        db = _make_db(already_seeded=False)
        seed(db)
        db.commit.assert_called_once()

    def test_seed_flushes_once(self):
        from app.seed import seed
        db = _make_db(already_seeded=False)
        seed(db)
        db.flush.assert_called_once()

    def test_seed_creates_platinum_user(self):
        """The seed must create a user whose grade is PLATINUM."""
        from app.models.user import UserGrade
        from app.seed import seed

        captured_users = []

        def capture_add_all(items):
            captured_users.extend(items)

        db = _make_db(already_seeded=False)
        db.add_all.side_effect = capture_add_all

        seed(db)

        grades = [getattr(u, "grade", None) for u in captured_users]
        assert UserGrade.PLATINUM in grades, (
            f"No PLATINUM user found in seed data. Grades present: {grades}"
        )

    def test_seed_platinum_user_email(self):
        """The PLATINUM user should have the expected email."""
        from app.models.user import UserGrade
        from app.seed import seed

        captured_users = []

        def capture_add_all(items):
            captured_users.extend(items)

        db = _make_db(already_seeded=False)
        db.add_all.side_effect = capture_add_all

        seed(db)

        platinum_users = [u for u in captured_users if getattr(u, "grade", None) == UserGrade.PLATINUM]
        assert len(platinum_users) == 1, "Exactly one PLATINUM user should be seeded"
        assert platinum_users[0].email == "platinum@shopadmin.io"

    def test_seed_platinum_user_full_name(self):
        from app.models.user import UserGrade
        from app.seed import seed

        captured_users = []

        def capture_add_all(items):
            captured_users.extend(items)

        db = _make_db(already_seeded=False)
        db.add_all.side_effect = capture_add_all

        seed(db)

        platinum_users = [u for u in captured_users if getattr(u, "grade", None) == UserGrade.PLATINUM]
        assert platinum_users[0].full_name == "플래티넘회원"

    def test_seed_admin_has_vip_grade(self):
        from app.models.user import UserGrade
        from app.seed import seed

        captured_users = []

        def capture_add_all(items):
            captured_users.extend(items)

        db = _make_db(already_seeded=False)
        db.add_all.side_effect = capture_add_all

        seed(db)

        admin_users = [u for u in captured_users if getattr(u, "email", None) == "admin@shopadmin.io"]
        assert len(admin_users) == 1
        assert admin_users[0].grade == UserGrade.VIP

    def test_seed_customer_has_gold_grade(self):
        from app.models.user import UserGrade
        from app.seed import seed

        captured_users = []

        def capture_add_all(items):
            captured_users.extend(items)

        db = _make_db(already_seeded=False)
        db.add_all.side_effect = capture_add_all

        seed(db)

        customer_users = [u for u in captured_users if getattr(u, "email", None) == "user@shopadmin.io"]
        assert len(customer_users) == 1
        assert customer_users[0].grade == UserGrade.GOLD

    def test_seed_creates_three_users(self):
        from app.models.user import User
        from app.seed import seed

        captured_users = []
        captured_products = []
        call_count = [0]

        def capture_add_all(items):
            call_count[0] += 1
            if call_count[0] == 1:
                captured_users.extend(items)
            else:
                captured_products.extend(items)

        db = _make_db(already_seeded=False)
        db.add_all.side_effect = capture_add_all

        seed(db)

        assert len(captured_users) == 3, f"Expected 3 users, got {len(captured_users)}"

    def test_seed_creates_three_products(self):
        from app.seed import seed

        captured_products = []
        call_count = [0]

        def capture_add_all(items):
            call_count[0] += 1
            if call_count[0] == 2:
                captured_products.extend(items)

        db = _make_db(already_seeded=False)
        db.add_all.side_effect = capture_add_all

        seed(db)

        assert len(captured_products) == 3, f"Expected 3 products, got {len(captured_products)}"


# ---------------------------------------------------------------------------
# Backward-incompatible / negative tests
# ---------------------------------------------------------------------------

class TestBackwardIncompatible:
    """Verify that using an old/invalid grade value raises the right errors."""

    def test_invalid_enum_name_raises_key_error(self):
        """Accessing a non-existent enum member by name should raise KeyError."""
        from app.models.user import UserGrade
        with pytest.raises(KeyError):
            _ = UserGrade["INVALID_GRADE"]

    def test_invalid_enum_value_raises_value_error(self):
        """Constructing enum from an invalid value should raise ValueError."""
        from app.models.user import UserGrade
        with pytest.raises(ValueError):
            _ = UserGrade("INVALID_GRADE")

    def test_old_missing_value_is_not_present(self):
        """
        If a consumer hard-codes an old value that was removed (hypothetically),
        they would get an AttributeError. Here we just confirm the enum is strict.
        """
        from app.models.user import UserGrade
        # All original values are still present (no removal), so this should pass
        original_values = ["BRONZE", "GOLD", "SILVER", "VIP"]
        for v in original_values:
            assert hasattr(UserGrade, v), f"{v} should still exist in UserGrade"

    def test_platinum_not_equal_to_any_old_value(self):
        """PLATINUM is a new, distinct value and must not collide with old ones."""
        from app.models.user import UserGrade
        old_values = [UserGrade.BRONZE, UserGrade.GOLD, UserGrade.SILVER, UserGrade.VIP]
        for old in old_values:
            assert UserGrade.PLATINUM != old, f"PLATINUM must differ from {old}"

    def test_enum_lookup_by_value_platinum(self):
        """Round-trip: construct PLATINUM from its own value."""
        from app.models.user import UserGrade
        pt = UserGrade.PLATINUM
        reconstructed = UserGrade(pt.value)
        assert reconstructed == UserGrade.PLATINUM

    def test_assigning_wrong_type_raises(self):
        """Assigning an integer instead of enum should raise ValueError/KeyError."""
        from app.models.user import UserGrade
        with pytest.raises((ValueError, KeyError)):
            _ = UserGrade(99999)

    def test_none_value_raises(self):
        """None is not a valid enum value."""
        from app.models.user import UserGrade
        with pytest.raises((ValueError, KeyError, TypeError)):
            _ = UserGrade(None)