from dataclasses import dataclass
from decimal import Decimal


@dataclass
class BuyResult:
    new_balance: Decimal
    new_qty: Decimal
    new_avg: Decimal
    fee: Decimal


@dataclass
class SellResult:
    new_balance: Decimal
    new_qty: Decimal
    new_avg: Decimal
    fee: Decimal
    realized_pnl: Decimal


def apply_buy(*, balance, pos_qty, pos_avg, qty, price, fee_rate) -> BuyResult:
    notional = qty * price
    fee = notional * fee_rate
    total_cost = notional + fee
    if total_cost > balance:
        raise ValueError("Insufficient balance")
    new_qty = pos_qty + qty
    new_avg = (pos_qty * pos_avg + notional) / new_qty
    return BuyResult(
        new_balance=balance - total_cost, new_qty=new_qty, new_avg=new_avg, fee=fee
    )


def apply_sell(*, balance, pos_qty, pos_avg, qty, price, fee_rate) -> SellResult:
    if qty > pos_qty:
        raise ValueError("Insufficient position")
    notional = qty * price
    fee = notional * fee_rate
    proceeds = notional - fee
    realized_pnl = (price - pos_avg) * qty - fee
    new_qty = pos_qty - qty
    new_avg = pos_avg if new_qty > 0 else Decimal("0")
    return SellResult(
        new_balance=balance + proceeds,
        new_qty=new_qty,
        new_avg=new_avg,
        fee=fee,
        realized_pnl=realized_pnl,
    )
