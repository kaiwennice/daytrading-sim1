from decimal import Decimal

import pytest

from services.fills import apply_buy, apply_sell

FEE = Decimal("0.0005")


def test_buy_no_existing_position():
    res = apply_buy(
        balance=Decimal("1000"),
        pos_qty=Decimal("0"),
        pos_avg=Decimal("0"),
        qty=Decimal("1"),
        price=Decimal("100"),
        fee_rate=FEE,
    )
    assert res.new_balance == Decimal("899.95")
    assert res.new_qty == Decimal("1")
    assert res.new_avg == Decimal("100")
    assert res.fee == Decimal("0.05")


def test_buy_adds_to_position_weighted_avg():
    res = apply_buy(
        balance=Decimal("1000"),
        pos_qty=Decimal("1"),
        pos_avg=Decimal("100"),
        qty=Decimal("1"),
        price=Decimal("200"),
        fee_rate=FEE,
    )
    assert res.new_qty == Decimal("2")
    assert res.new_avg == Decimal("150")


def test_buy_insufficient_balance_raises():
    with pytest.raises(ValueError):
        apply_buy(
            balance=Decimal("10"),
            pos_qty=Decimal("0"),
            pos_avg=Decimal("0"),
            qty=Decimal("1"),
            price=Decimal("100"),
            fee_rate=FEE,
        )


def test_sell_realizes_pnl():
    res = apply_sell(
        balance=Decimal("0"),
        pos_qty=Decimal("2"),
        pos_avg=Decimal("100"),
        qty=Decimal("1"),
        price=Decimal("150"),
        fee_rate=FEE,
    )
    assert res.new_balance == Decimal("149.925")
    assert res.new_qty == Decimal("1")
    assert res.new_avg == Decimal("100")
    assert res.realized_pnl == Decimal("49.925")
    assert res.fee == Decimal("0.075")


def test_sell_more_than_held_raises():
    with pytest.raises(ValueError):
        apply_sell(
            balance=Decimal("0"),
            pos_qty=Decimal("1"),
            pos_avg=Decimal("100"),
            qty=Decimal("2"),
            price=Decimal("150"),
            fee_rate=FEE,
        )
