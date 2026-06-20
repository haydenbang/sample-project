def calc_discount(unit_price: float, quantity: int, user_id: int) -> tuple[float, float]:
    """단순 할인율 계산 — 수량 기반."""
    rate = 0.0
    if quantity >= 10:
        rate = 0.1
    elif quantity >= 5:
        rate = 0.05
    total = unit_price * quantity * (1 - rate)
    return rate, total
