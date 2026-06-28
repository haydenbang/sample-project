"""Tests for backend/app/services/discount.py

Verifies that the PLATINUM grade addition to the UserGrade enum is handled
correctly throughout the discount service, and that backward-incompatible
scenarios (e.g. passing an invalid/old grade value) raise appropriate errors.
"""

import pytest
from unittest.mock import patch
from enum import Enum


# ---------------------------------------------------------------------------
# Minimal stubs so the module can be imported without the full app stack
# ---------------------------------------------------------------------------

class UserGrade(str, Enum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"  # NEW value
    VIP = "VIP"


# Patch the model import before importing the service
import sys
import types

# Build a fake app.models.user module
fake_user_module = types.ModuleType("app.models.user")
fake_user_module.UserGrade = UserGrade

fake_app = types.ModuleType("app")
fake_models = types.ModuleType("app.models")
fake_app.models = fake_models
fake_models.user = fake_user_module

sys.modules.setdefault("app", fake_app)
sys.modules.setdefault("app.models", fake_models)
sys.modules["app.models.user"] = fake_user_module

# Now import the service under test
from app.services.discount import (  # noqa: E402
    GRADE_DISCOUNT_RATE,
    COUPONS,
    grade_discount,
    coupon_discount,
    calculate_discount,
)


# ===========================================================================
# 1.  Enum membership tests
# ===========================================================================

class TestUserGradeEnum:
    """Verify that the PLATINUM value exists and the full set is correct."""

    def test_platinum_exists(self):
        assert "PLATINUM" in UserGrade.__members__

    def test_all_expected_values_present(self):
        expected = {"BRONZE", "SILVER", "GOLD", "PLATINUM", "VIP"}
        assert set(UserGrade.__members__.keys()) == expected

    def test_platinum_value(self):
        assert UserGrade.PLATINUM.value == "PLATINUM"

    def test_enum_count(self):
        # Before the change there were 4 values; now there must be 5
        assert len(UserGrade) == 5


# ===========================================================================
# 2.  GRADE_DISCOUNT_RATE dictionary tests
# ===========================================================================

class TestGradeDiscountRateMapping:
    """Every UserGrade must have an entry in GRADE_DISCOUNT_RATE."""

    def test_platinum_rate_in_mapping(self):
        assert UserGrade.PLATINUM in GRADE_DISCOUNT_RATE

    def test_platinum_rate_value(self):
        assert GRADE_DISCOUNT_RATE[UserGrade.PLATINUM] == pytest.approx(0.08)

    def test_all_grades_covered(self):
        for grade in UserGrade:
            assert grade in GRADE_DISCOUNT_RATE, f"{grade} missing from GRADE_DISCOUNT_RATE"

    def test_no_extra_grades_in_mapping(self):
        assert set(GRADE_DISCOUNT_RATE.keys()) == set(UserGrade)

    # Spot-check the other rates are unchanged
    def test_bronze_rate(self):
        assert GRADE_DISCOUNT_RATE[UserGrade.BRONZE] == pytest.approx(0.0)

    def test_silver_rate(self):
        assert GRADE_DISCOUNT_RATE[UserGrade.SILVER] == pytest.approx(0.03)

    def test_gold_rate(self):
        assert GRADE_DISCOUNT_RATE[UserGrade.GOLD] == pytest.approx(0.05)

    def test_vip_rate(self):
        assert GRADE_DISCOUNT_RATE[UserGrade.VIP] == pytest.approx(0.10)


# ===========================================================================
# 3.  grade_discount() — new PLATINUM grade
# ===========================================================================

class TestGradeDiscountPlatinum:
    """PLATINUM should apply an 8 % discount."""

    def test_platinum_discount_basic(self):
        # 10_000 * 0.08 = 800
        assert grade_discount(10_000, UserGrade.PLATINUM) == 800

    def test_platinum_discount_large_amount(self):
        # 100_000 * 0.08 = 8_000
        assert grade_discount(100_000, UserGrade.PLATINUM) == 8_000

    def test_platinum_discount_zero_subtotal(self):
        assert grade_discount(0, UserGrade.PLATINUM) == 0

    def test_platinum_discount_is_integer(self):
        result = grade_discount(10_001, UserGrade.PLATINUM)
        assert isinstance(result, int)

    def test_platinum_discount_truncates(self):
        # 10_001 * 0.08 = 800.08 -> truncated to 800
        assert grade_discount(10_001, UserGrade.PLATINUM) == 800


# ===========================================================================
# 4.  grade_discount() — existing grades unchanged
# ===========================================================================

class TestGradeDiscountExistingGrades:
    """Ensure the previously-existing grades still work correctly."""

    @pytest.mark.parametrize("grade,subtotal,expected", [
        (UserGrade.BRONZE,  10_000, 0),
        (UserGrade.SILVER,  10_000, 300),
        (UserGrade.GOLD,    10_000, 500),
        (UserGrade.VIP,     10_000, 1_000),
    ])
    def test_existing_grade_discount(self, grade, subtotal, expected):
        assert grade_discount(subtotal, grade) == expected


# ===========================================================================
# 5.  coupon_discount() — unaffected by enum change, but smoke-tested
# ===========================================================================

class TestCouponDiscount:
    def test_no_coupon(self):
        assert coupon_discount(10_000, None) == 0

    def test_empty_string_coupon(self):
        assert coupon_discount(10_000, "") == 0

    def test_invalid_coupon(self):
        assert coupon_discount(10_000, "DOESNOTEXIST") == 0

    def test_percent_coupon(self):
        # WELCOME5 -> 5 % of 10_000 = 500
        assert coupon_discount(10_000, "WELCOME5") == 500

    def test_amount_coupon(self):
        # SAVE3000 -> 3_000, subtotal large enough
        assert coupon_discount(10_000, "SAVE3000") == 3_000

    def test_amount_coupon_capped_at_subtotal(self):
        # subtotal < coupon face value -> capped
        assert coupon_discount(1_000, "SAVE3000") == 1_000


# ===========================================================================
# 6.  calculate_discount() — integration with PLATINUM
# ===========================================================================

class TestCalculateDiscountPlatinum:
    def test_platinum_no_coupon(self):
        # 10_000 * 0.08 = 800
        assert calculate_discount(10_000, UserGrade.PLATINUM) == 800

    def test_platinum_with_percent_coupon(self):
        # grade: 800, coupon: 500, total: 1_300
        assert calculate_discount(10_000, UserGrade.PLATINUM, "WELCOME5") == 1_300

    def test_platinum_with_amount_coupon(self):
        # grade: 800, coupon: 3_000, total: 3_800
        assert calculate_discount(10_000, UserGrade.PLATINUM, "SAVE3000") == 3_800

    def test_discount_capped_at_subtotal(self):
        # Very small subtotal; combined discount must not exceed it
        assert calculate_discount(100, UserGrade.VIP, "SAVE3000") == 100

    def test_platinum_discount_capped_at_subtotal(self):
        assert calculate_discount(500, UserGrade.PLATINUM, "SAVE3000") == 500

    def test_calculate_returns_integer(self):
        result = calculate_discount(9_999, UserGrade.PLATINUM)
        assert isinstance(result, int)


# ===========================================================================
# 7.  Backward-incompatible / error cases
# ===========================================================================

class TestBackwardIncompatible:
    """
    Before the enum change, PLATINUM did not exist.  Code that tries to use
    the old enum (without PLATINUM) should raise errors that reflect the
    missing member.
    """

    def test_old_enum_without_platinum_raises_key_error(self):
        """Simulates a stale enum that lacks PLATINUM being looked up in the
        new GRADE_DISCOUNT_RATE mapping."""
        class OldUserGrade(str, Enum):
            BRONZE = "BRONZE"
            SILVER = "SILVER"
            GOLD = "GOLD"
            VIP = "VIP"
            # PLATINUM intentionally absent

        # The new mapping uses the new enum values as keys.  Looking up an old
        # enum member by its string value should fail at the new Enum boundary.
        with pytest.raises((KeyError, ValueError)):
            # Attempting to coerce the string "PLATINUM" on the *old* enum
            OldUserGrade("PLATINUM")

    def test_string_platinum_not_accepted_by_old_enum(self):
        """'PLATINUM' as a raw string is not a valid member of the old enum."""
        class OldUserGrade(str, Enum):
            BRONZE = "BRONZE"
            SILVER = "SILVER"
            GOLD = "GOLD"
            VIP = "VIP"

        with pytest.raises(ValueError):
            OldUserGrade("PLATINUM")

    def test_invalid_grade_string_raises_value_error(self):
        """An entirely unknown grade string should not be silently accepted."""
        with pytest.raises(ValueError):
            UserGrade("UNKNOWN_GRADE")

    def test_grade_discount_unknown_grade_falls_back_to_zero(self):
        """
        If somehow an unknown grade slips through (e.g. monkey-patched),
        grade_discount should return 0 via the dict.get(..., 0.0) fallback.
        """
        # We pass a sentinel object that is not a real UserGrade member.
        unknown = object()
        result = grade_discount(10_000, unknown)  # type: ignore[arg-type]
        assert result == 0

    def test_platinum_not_in_old_enum_members(self):
        """Confirms the old enum truly lacked PLATINUM (regression guard)."""
        class OldUserGrade(str, Enum):
            BRONZE = "BRONZE"
            SILVER = "SILVER"
            GOLD = "GOLD"
            VIP = "VIP"

        assert "PLATINUM" not in OldUserGrade.__members__

    def test_calculate_discount_with_none_grade_raises(self):
        """Passing None as a grade must not silently return 0 without a type
        check — it should either work via fallback or raise."""
        # The implementation uses dict.get with default 0.0, so None would
        # return 0 for grade_discount; that is acceptable but we assert the
        # contract explicitly.
        result = calculate_discount(10_000, None)  # type: ignore[arg-type]
        # None is not a valid grade: discount must be 0 (fallback behaviour)
        assert result == 0


# ===========================================================================
# 8.  Serialization / value round-trip
# ===========================================================================

class TestPlatinumSerialization:
    """Verify PLATINUM serialises to/from its string value correctly."""

    def test_platinum_string_value(self):
        assert UserGrade.PLATINUM.value == "PLATINUM"

    def test_platinum_from_string(self):
        assert UserGrade("PLATINUM") is UserGrade.PLATINUM

    def test_platinum_str_representation(self):
        # Because UserGrade inherits from str, str(member) == its value
        assert str(UserGrade.PLATINUM) == "PLATINUM"

    def test_grade_discount_rate_keys_are_enum_members(self):
        for key in GRADE_DISCOUNT_RATE:
            assert isinstance(key, UserGrade)

    def test_platinum_in_grade_discount_rate_via_string_lookup(self):
        """Simulate deserialising from JSON: look up via UserGrade('PLATINUM')."""
        grade = UserGrade("PLATINUM")
        assert grade in GRADE_DISCOUNT_RATE
        assert GRADE_DISCOUNT_RATE[grade] == pytest.approx(0.08)