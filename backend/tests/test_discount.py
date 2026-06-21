import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.discount import calc_discount


def test_no_discount_below_5():
    rate, total = calc_discount(1000.0, 2, user_id=1)
    assert rate == 0.0
    assert total == 2000.0


def test_five_percent_at_quantity_5():
    rate, total = calc_discount(1000.0, 5, user_id=1)
    assert rate == 0.05
    assert abs(total - 4750.0) < 0.01


def test_ten_percent_at_quantity_10():
    rate, total = calc_discount(1000.0, 10, user_id=1)
    assert rate == 0.1
    assert abs(total - 9000.0) < 0.01


def test_total_is_unit_times_qty_times_discount():
    rate, total = calc_discount(2000.0, 7, user_id=1)
    expected = 2000.0 * 7 * (1 - rate)
    assert abs(total - expected) < 0.01
