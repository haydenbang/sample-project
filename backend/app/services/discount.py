"""할인 정책 공통 서비스.

요구사항서(docs/requirements.md §3)의 비즈니스 규칙을 구현한다.
이 함수의 시그니처/규칙을 바꾸면 order_service, 테스트, 프론트 금액 표시가 영향받는다.
(변경 영향도 데모: scenario/discount-policy-change)
"""

from app.models.user import UserGrade

# 회원 등급별 할인율 (요구사항서 §3)
GRADE_DISCOUNT_RATE: dict[UserGrade, float] = {
    UserGrade.BRONZE: 0.0,
    UserGrade.SILVER: 0.03,
    UserGrade.GOLD: 0.05,
    UserGrade.VIP: 0.10,
    UserGrade.PLATINUM: 0.15,
}

# 데모용 쿠폰 테이블: code -> (종류, 값)
#   "PERCENT" -> 정률(%), "AMOUNT" -> 정액(원)
COUPONS: dict[str, tuple[str, int]] = {
    "WELCOME5": ("PERCENT", 5),
    "SAVE3000": ("AMOUNT", 3000),
}


def grade_discount(subtotal: int, grade: UserGrade) -> int:
    """회원 등급 할인액(원)을 반환한다."""
    rate = GRADE_DISCOUNT_RATE.get(grade, 0.0)
    return int(subtotal * rate)


def coupon_discount(subtotal: int, coupon_code: str | None) -> int:
    """쿠폰 할인액(원)을 반환한다. 유효하지 않은 쿠폰은 0."""
    if not coupon_code:
        return 0
    entry = COUPONS.get(coupon_code)
    if entry is None:
        return 0
    kind, value = entry
    if kind == "PERCENT":
        return int(subtotal * value / 100)
    return min(value, subtotal)


def calculate_discount(subtotal: int, grade: UserGrade, coupon_code: str | None = None) -> int:
    """등급 할인 + 쿠폰 할인 합계를 반환한다. (subtotal 초과 불가)"""
    total_discount = grade_discount(subtotal, grade) + coupon_discount(subtotal, coupon_code)
    return min(total_discount, subtotal)
