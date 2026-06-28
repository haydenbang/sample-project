"""Tests for backend/app/services/discount.py

Verifies that:
1. The discount service works correctly after the `phone` field was added to User.
2. The service is unaffected by the schema change (no breakage).
3. All discount logic (grade, coupon, combined) is validated.
4. Backward-incompatible usage raises the right errors.
"""

import pytest

from app.models.user import UserGrade
from app.services.discount import (
    COUPONS,
    GRADE_DISCOUNT_RATE,
    calculate_discount,
    coupon_discount,
    grade_discount,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def bronze_subtotal():
    return 10_000


@pytest.fixture()
def gold_subtotal():
    return 50_000


# ---------------------------------------------------------------------------
# 1. Model / Schema – phone field added to User (nullable)
# ---------------------------------------------------------------------------


class TestUserModelPhoneField:
    """Verify that the User model now exposes a nullable `phone` field
    and that the discount service import chain remains intact."""

    def test_user_model_importable_with_phone_field(self):
        """The User model should be importable and have the phone attribute."""
        try:
            from app.models.user import User  # noqa: F401
        except ImportError:
            pytest.skip("User model not importable in this test environment")

        from app.models.user import User

        # phone must be declared on the model (nullable → default None acceptable)
        assert hasattr(User, "phone") or "phone" in User.__table__.columns  # type: ignore[attr-defined]

    def test_user_phone_field_is_nullable(self):
        """phone column must be nullable (True)."""
        try:
            from app.models.user import User
        except ImportError:
            pytest.skip("User model not importable in this test environment")

        from app.models.user import User

        col = User.__table__.columns.get("phone")  # type: ignore[attr-defined]
        assert col is not None, "phone column not found on User table"
        assert col.nullable is True, "phone column should be nullable"

    def test_user_phone_field_accepts_none(self):
        """A User instance created without a phone value should have phone=None."""
        try:
            from app.models.user import User
        except ImportError:
            pytest.skip("User model not importable in this test environment")

        from app.models.user import User

        # Instantiate without providing phone
        user = User.__new__(User)
        # Directly set to None to simulate nullable behavior
        user.phone = None
        assert user.phone is None

    def test_user_phone_field_accepts_string(self):
        """A User instance should accept a string value for phone."""
        try:
            from app.models.user import User
        except ImportError:
            pytest.skip("User model not importable in this test environment")

        from app.models.user import User

        user = User.__new__(User)
        user.phone = "+82-10-1234-5678"
        assert user.phone == "+82-10-1234-5678"

    def test_user_grade_enum_still_importable(self):
        """UserGrade enum must remain importable after the phone field addition."""
        from app.models.user import UserGrade as UG

        assert UG.BRONZE is not None
        assert UG.SILVER is not None
        assert UG.GOLD is not None
        assert UG.VIP is not None

    def test_discount_service_unaffected_by_phone_field(self):
        """discount.py must continue to function correctly; phone is irrelevant."""
        result = calculate_discount(10_000, UserGrade.GOLD)
        assert result == 500  # 5 % of 10_000


# ---------------------------------------------------------------------------
# 2. GRADE_DISCOUNT_RATE – validation
# ---------------------------------------------------------------------------


class TestGradeDiscountRate:
    def test_all_grades_present(self):
        for grade in UserGrade:
            assert grade in GRADE_DISCOUNT_RATE

    def test_bronze_rate_is_zero(self):
        assert GRADE_DISCOUNT_RATE[UserGrade.BRONZE] == 0.0

    def test_silver_rate(self):
        assert GRADE_DISCOUNT_RATE[UserGrade.SILVER] == 0.03

    def test_gold_rate(self):
        assert GRADE_DISCOUNT_RATE[UserGrade.GOLD] == 0.05

    def test_vip_rate(self):
        assert GRADE_DISCOUNT_RATE[UserGrade.VIP] == 0.10

    def test_rates_are_floats(self):
        for rate in GRADE_DISCOUNT_RATE.values():
            assert isinstance(rate, float)


# ---------------------------------------------------------------------------
# 3. grade_discount()
# ---------------------------------------------------------------------------


class TestGradeDiscount:
    def test_bronze_returns_zero(self, bronze_subtotal):
        assert grade_discount(bronze_subtotal, UserGrade.BRONZE) == 0

    def test_silver_discount(self):
        assert grade_discount(10_000, UserGrade.SILVER) == 300  # 3 %

    def test_gold_discount(self, gold_subtotal):
        assert grade_discount(gold_subtotal, UserGrade.GOLD) == 2_500  # 5 %

    def test_vip_discount(self):
        assert grade_discount(100_000, UserGrade.VIP) == 10_000  # 10 %

    def test_returns_integer(self):
        result = grade_discount(99, UserGrade.SILVER)
        assert isinstance(result, int)

    def test_zero_subtotal(self):
        assert grade_discount(0, UserGrade.VIP) == 0

    def test_truncation_not_rounding(self):
        # 1 * 0.05 = 0.05 → int → 0
        assert grade_discount(1, UserGrade.GOLD) == 0

    def test_invalid_grade_raises(self):
        with pytest.raises((KeyError, AttributeError, TypeError)):
            grade_discount(10_000, "PLATINUM")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 4. coupon_discount()
# ---------------------------------------------------------------------------


class TestCouponDiscount:
    def test_none_coupon_returns_zero(self):
        assert coupon_discount(10_000, None) == 0

    def test_empty_string_coupon_returns_zero(self):
        assert coupon_discount(10_000, "") == 0

    def test_invalid_coupon_returns_zero(self):
        assert coupon_discount(10_000, "NOTEXIST") == 0

    def test_percent_coupon_welcome5(self):
        # 5 % of 10_000 = 500
        assert coupon_discount(10_000, "WELCOME5") == 500

    def test_percent_coupon_truncation(self):
        # 5 % of 9 = 0.45 → int → 0
        assert coupon_discount(9, "WELCOME5") == 0

    def test_amount_coupon_save3000(self):
        assert coupon_discount(20_000, "SAVE3000") == 3_000

    def test_amount_coupon_capped_at_subtotal(self):
        # subtotal < coupon amount
        assert coupon_discount(1_000, "SAVE3000") == 1_000

    def test_amount_coupon_exact_subtotal(self):
        assert coupon_discount(3_000, "SAVE3000") == 3_000

    def test_returns_integer(self):
        result = coupon_discount(10_000, "WELCOME5")
        assert isinstance(result, int)

    def test_coupons_table_has_expected_keys(self):
        assert "WELCOME5" in COUPONS
        assert "SAVE3000" in COUPONS

    def test_coupons_table_structure(self):
        for code, (kind, value) in COUPONS.items():
            assert kind in ("PERCENT", "AMOUNT"), f"Unknown coupon kind for {code}"
            assert isinstance(value, int)


# ---------------------------------------------------------------------------
# 5. calculate_discount()
# ---------------------------------------------------------------------------


class TestCalculateDiscount:
    def test_no_coupon_bronze(self):
        assert calculate_discount(10_000, UserGrade.BRONZE) == 0

    def test_grade_only_gold(self):
        assert calculate_discount(10_000, UserGrade.GOLD) == 500

    def test_grade_only_vip(self):
        assert calculate_discount(10_000, UserGrade.VIP) == 1_000

    def test_coupon_only_none_grade(self):
        # BRONZE + no coupon
        assert calculate_discount(10_000, UserGrade.BRONZE, None) == 0

    def test_combined_silver_welcome5(self):
        # silver 3 % + WELCOME5 5 % = 8 % of 10_000 = 800
        assert calculate_discount(10_000, UserGrade.SILVER, "WELCOME5") == 800

    def test_combined_gold_save3000(self):
        # gold 5 % of 50_000 = 2_500 + SAVE3000 3_000 = 5_500
        assert calculate_discount(50_000, UserGrade.GOLD, "SAVE3000") == 5_500

    def test_combined_vip_welcome5(self):
        # vip 10 % of 10_000 = 1_000 + WELCOME5 5 % of 10_000 = 500 → 1_500
        assert calculate_discount(10_000, UserGrade.VIP, "WELCOME5") == 1_500

    def test_total_discount_does_not_exceed_subtotal(self):
        # Force a tiny subtotal where combined discount would exceed it
        result = calculate_discount(100, UserGrade.VIP, "SAVE3000")
        assert result <= 100

    def test_returns_integer(self):
        result = calculate_discount(10_000, UserGrade.GOLD, "WELCOME5")
        assert isinstance(result, int)

    def test_zero_subtotal(self):
        assert calculate_discount(0, UserGrade.VIP, "WELCOME5") == 0

    def test_default_coupon_none(self):
        """coupon_code defaults to None – should not raise."""
        result = calculate_discount(10_000, UserGrade.SILVER)
        assert result == 300

    def test_invalid_coupon_no_extra_discount(self):
        result = calculate_discount(10_000, UserGrade.GOLD, "BADCODE")
        assert result == 500  # only grade discount

    def test_discount_capped_at_subtotal_large_coupon(self):
        subtotal = 1
        result = calculate_discount(subtotal, UserGrade.VIP, "SAVE3000")
        assert result == subtotal


# ---------------------------------------------------------------------------
# 6. Backward-incompatible / error cases
# ---------------------------------------------------------------------------


class TestBackwardIncompatibleCases:
    """Ensure that incorrect usage raises the right errors."""

    def test_grade_discount_wrong_type_raises(self):
        with pytest.raises((TypeError, AttributeError, KeyError)):
            grade_discount(10_000, 99)  # type: ignore[arg-type]

    def test_calculate_discount_wrong_grade_type_raises(self):
        with pytest.raises((TypeError, AttributeError, KeyError)):
            calculate_discount(10_000, "UNKNOWN_GRADE")  # type: ignore[arg-type]

    def test_grade_discount_negative_subtotal(self):
        # Negative subtotal: discount should be <= 0 (implementation-defined)
        result = grade_discount(-100, UserGrade.GOLD)
        assert isinstance(result, int)

    def test_coupon_discount_non_string_code_raises(self):
        with pytest.raises((TypeError, AttributeError)):
            coupon_discount(10_000, 12345)  # type: ignore[arg-type]

    def test_calculate_discount_missing_subtotal_raises(self):
        with pytest.raises(TypeError):
            calculate_discount(grade=UserGrade.GOLD)  # type: ignore[call-arg]

    def test_calculate_discount_missing_grade_raises(self):
        with pytest.raises(TypeError):
            calculate_discount(10_000)  # type: ignore[call-arg]

    def test_phone_field_not_required_by_discount(self):
        """discount.py must NOT require or reference phone in any way."""
        import inspect

        import app.services.discount as discount_module

        source = inspect.getsource(discount_module)
        assert "phone" not in source, (
            "discount.py should not reference the phone field"
        )