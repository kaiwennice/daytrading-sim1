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


# ---------------------------------------------------------------------------
# Leverage-aware tests
# ---------------------------------------------------------------------------


def test_apply_buy_1x_no_change():
    """leverage=1 should give identical numeric results to the pre-leverage behaviour."""
    res = apply_buy(
        balance=Decimal("1000"),
        pos_qty=Decimal("0"),
        pos_avg=Decimal("0"),
        qty=Decimal("1"),
        price=Decimal("100"),
        fee_rate=FEE,
        leverage=1,
        pos_leverage=1,
    )
    assert res.new_balance == Decimal("899.95")
    assert res.new_qty == Decimal("1")
    assert res.new_avg == Decimal("100")
    assert res.fee == Decimal("0.05")
    assert res.new_leverage == 1
    assert res.liquidation_price is None


def test_apply_buy_2x_halves_margin():
    """Buy 1 BTC @ 100 with 2x leverage: margin=50, fee=0.05, cost=50.05."""
    res = apply_buy(
        balance=Decimal("1000"),
        pos_qty=Decimal("0"),
        pos_avg=Decimal("0"),
        qty=Decimal("1"),
        price=Decimal("100"),
        fee_rate=FEE,
        leverage=2,
        pos_leverage=1,
    )
    assert res.new_balance == Decimal("1000") - Decimal("50.05")
    assert res.new_qty == Decimal("1")
    assert res.new_avg == Decimal("100")
    assert res.fee == Decimal("0.05")
    assert res.new_leverage == 2
    # liq_price = 100 * (1 - 0.5 + 0.01) = 51
    assert res.liquidation_price == Decimal("51")


def test_apply_buy_blended_leverage():
    """Adding 1 BTC @ 100 (2x) to existing 1 BTC @ 100 (2x): blended leverage stays 2."""
    res = apply_buy(
        balance=Decimal("1000"),
        pos_qty=Decimal("1"),
        pos_avg=Decimal("100"),
        qty=Decimal("1"),
        price=Decimal("100"),
        fee_rate=FEE,
        leverage=2,
        pos_leverage=2,
    )
    assert res.new_qty == Decimal("2")
    assert res.new_avg == Decimal("100")
    assert res.new_leverage == 2
    # liq_price = 100 * (1 - 0.5 + 0.01) = 51
    assert res.liquidation_price == Decimal("51")


def test_apply_sell_1x_unchanged():
    """Selling with pos_leverage=1 should give the same balance as the original formula."""
    res = apply_sell(
        balance=Decimal("0"),
        pos_qty=Decimal("2"),
        pos_avg=Decimal("100"),
        qty=Decimal("1"),
        price=Decimal("150"),
        fee_rate=FEE,
        pos_leverage=1,
    )
    assert res.new_balance == Decimal("149.925")
    assert res.new_qty == Decimal("1")
    assert res.realized_pnl == Decimal("49.925")
    assert res.new_leverage == 1
    assert res.liquidation_price is None


def test_apply_sell_2x_correct_balance():
    """
    Buy 1 BTC @ 100 with 2x (cost = 50 + fee 0.05 = 50.05, balance starts 1000 → 949.95).
    Sell 1 BTC @ 110 with pos_leverage=2:
      proceeds = 110 - 110*0.0005 = 110 - 0.055 = 109.945
      balance_change = 109.945 - 100*1*(1 - 1/2) = 109.945 - 50 = 59.945
      realized_pnl = (110-100)*1 - 110*0.0005 = 10 - 0.055 = 9.945
    """
    buy_res = apply_buy(
        balance=Decimal("1000"),
        pos_qty=Decimal("0"),
        pos_avg=Decimal("0"),
        qty=Decimal("1"),
        price=Decimal("100"),
        fee_rate=FEE,
        leverage=2,
    )
    sell_res = apply_sell(
        balance=buy_res.new_balance,
        pos_qty=buy_res.new_qty,
        pos_avg=buy_res.new_avg,
        qty=Decimal("1"),
        price=Decimal("110"),
        fee_rate=FEE,
        pos_leverage=2,
    )
    assert sell_res.new_balance == buy_res.new_balance + Decimal("59.945")
    assert sell_res.realized_pnl == Decimal("9.945")
    assert sell_res.new_qty == Decimal("0")
    assert sell_res.new_leverage == 2


def test_apply_sell_liq_price_clears_on_full_close():
    """After a full sell, liquidation_price must be None regardless of leverage."""
    buy_res = apply_buy(
        balance=Decimal("1000"),
        pos_qty=Decimal("0"),
        pos_avg=Decimal("0"),
        qty=Decimal("1"),
        price=Decimal("100"),
        fee_rate=FEE,
        leverage=3,
    )
    sell_res = apply_sell(
        balance=buy_res.new_balance,
        pos_qty=buy_res.new_qty,
        pos_avg=buy_res.new_avg,
        qty=Decimal("1"),
        price=Decimal("100"),
        fee_rate=FEE,
        pos_leverage=3,
    )
    assert sell_res.new_qty == Decimal("0")
    assert sell_res.liquidation_price is None
