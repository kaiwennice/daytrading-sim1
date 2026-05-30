from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class BuyResult:
    new_balance: Decimal
    new_qty: Decimal
    new_avg: Decimal
    fee: Decimal
    new_leverage: int
    liquidation_price: Optional[Decimal]


@dataclass
class SellResult:
    new_balance: Decimal
    new_qty: Decimal
    new_avg: Decimal
    fee: Decimal
    realized_pnl: Decimal
    new_leverage: int
    liquidation_price: Optional[Decimal]


def _liquidation_price(avg_cost: Decimal, leverage: int) -> Optional[Decimal]:
    """Return liquidation price for a leveraged position, None for 1x."""
    if leverage <= 1:
        return None
    return avg_cost * (1 - Decimal(1) / Decimal(leverage) + Decimal("0.01"))


def apply_buy(
    *,
    balance,
    pos_qty,
    pos_avg,
    qty,
    price,
    fee_rate,
    leverage: int = 1,
    pos_leverage: int = 1,
) -> BuyResult:
    notional = qty * price
    fee = notional * fee_rate
    margin = notional / Decimal(leverage)
    total_cost = margin + fee
    if total_cost > balance:
        raise ValueError("Insufficient balance")
    new_qty = pos_qty + qty
    new_avg = (pos_qty * pos_avg + notional) / new_qty

    # Blended leverage
    if pos_qty > 0:
        old_margin = pos_avg * pos_qty / Decimal(pos_leverage)
        new_margin = qty * price / Decimal(leverage)
        total_notional = new_avg * new_qty
        blended = int(round(total_notional / (old_margin + new_margin)))
        blended = max(1, blended)
    else:
        blended = leverage

    liq_price = _liquidation_price(new_avg, blended)
    return BuyResult(
        new_balance=balance - total_cost,
        new_qty=new_qty,
        new_avg=new_avg,
        fee=fee,
        new_leverage=blended,
        liquidation_price=liq_price,
    )


def apply_sell(
    *,
    balance,
    pos_qty,
    pos_avg,
    qty,
    price,
    fee_rate,
    pos_leverage: int = 1,
) -> SellResult:
    if qty > pos_qty:
        raise ValueError("Insufficient position")
    notional = qty * price
    fee = notional * fee_rate
    proceeds = notional - fee
    realized_pnl = (price - pos_avg) * qty - fee
    balance_change = proceeds - pos_avg * qty * (1 - Decimal(1) / Decimal(pos_leverage))
    new_qty = pos_qty - qty
    new_avg = pos_avg if new_qty > 0 else Decimal("0")

    if new_qty == 0 or pos_leverage <= 1:
        liq_price = None
    else:
        liq_price = _liquidation_price(new_avg, pos_leverage)

    return SellResult(
        new_balance=balance + balance_change,
        new_qty=new_qty,
        new_avg=new_avg,
        fee=fee,
        realized_pnl=realized_pnl,
        new_leverage=pos_leverage,
        liquidation_price=liq_price,
    )
