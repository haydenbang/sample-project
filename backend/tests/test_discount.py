"""할인 정책 단위 테스트 (services/discount.py)."""

import pytest

from app.models.user import UserGrade
from app.services.discount import calculate_discount, coupon_discount, grade_discount


@pytest.mark.parametrize(
    "grade,expected",
    [
        (UserGrade.BRONZE, 0),
        (UserGrade.SILVER, 3000),
        (UserGrade.GOLD, 5000),
        (UserGrade.VIP, 15000),
    ],
)
def test_grade_discount(grade, expected):
    assert grade_discount(100_000, grade) == expected


def test_coupon_percent():
    assert coupon_discount(100_000, "WELCOME5") == 5000


def test_coupon_amount():
    assert coupon_discount(100_000, "SAVE3000") == 3000


def test_coupon_invalid_or_none():
    assert coupon_discount(100_000, None) == 0
    assert coupon_discount(100_000, "NOPE") == 0


def test_calculate_discount_combines_grade_and_coupon():
    # GOLD 5% + SAVE3000 = 5000 + 3000
    assert calculate_discount(100_000, UserGrade.GOLD, coupon_code="SAVE3000") == 8000


def test_calculate_discount_capped_at_subtotal():
    assert calculate_discount(2000, UserGrade.VIP, coupon_code="SAVE3000") == 2000