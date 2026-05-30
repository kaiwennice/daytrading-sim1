"""Matching engine: fills market orders immediately and triggers resting
limit/stop_loss/take_profit orders on incoming prices (PRD 4.2)."""
import asyncio
import logging
import uuid
from decimal import Decimal

from sqlalchemy import select

from config import settings
from database import SessionLocal
from models.account import Account
from models.equity_snapshot import EquitySnapshot
from models.order import Order
from models.position import Position
from models.trade import Trade
from services.account_hub import hub
from services.fills import apply_buy, apply_sell

logger = logging.getLogger("uvicorn")


async def _get_position(db, account_id, symbol):
    return await db.scalar(
        select(Position)
        .where(Position.account_id == account_id, Position.symbol == symbol)
        .with_for_update()
    )


async def _record_equity(db, account: Account, get_price) -> None:
    """Snapshot total equity = cash + sum(position mark value)."""
    positions = (
        await db.scalars(select(Position).where(Position.account_id == account.id))
    ).all()
    equity = account.balance_usdt
    for p in positions:
        mark = get_price(p.symbol)
        if mark is None:
            mark = p.avg_cost
        equity += p.quantity * mark
    db.add(EquitySnapshot(account_id=account.id, total_equity=equity))


async def fill_order(db, account: Account, order: Order, price: Decimal, get_price) -> Trade:
    """Settle one order at `price`. Caller commits."""
    pos = await _get_position(db, account.id, order.symbol)
    pos_qty = pos.quantity if pos else Decimal("0")
    pos_avg = pos.avg_cost if pos else Decimal("0")

    if order.side == "buy":
        order_leverage = order.leverage if order.leverage is not None else 1
        pos_leverage = pos.leverage if (pos is not None and pos.leverage is not None) else 1
        res = apply_buy(
            balance=account.balance_usdt,
            pos_qty=pos_qty,
            pos_avg=pos_avg,
            qty=order.quantity,
            price=price,
            fee_rate=settings.taker_fee,
            leverage=order_leverage,
            pos_leverage=pos_leverage,
        )
        account.balance_usdt = res.new_balance
        if pos is None:
            new_pos = Position(
                account_id=account.id,
                symbol=order.symbol,
                side="long",
                quantity=res.new_qty,
                avg_cost=res.new_avg,
                leverage=res.new_leverage,
                liquidation_price=res.liquidation_price,
            )
            db.add(new_pos)
        else:
            pos.quantity = res.new_qty
            pos.avg_cost = res.new_avg
            pos.leverage = res.new_leverage
            pos.liquidation_price = res.liquidation_price
        fee, realized = res.fee, None
    else:
        pos_leverage = pos.leverage if (pos is not None and pos.leverage is not None) else 1
        res = apply_sell(
            balance=account.balance_usdt,
            pos_qty=pos_qty,
            pos_avg=pos_avg,
            qty=order.quantity,
            price=price,
            fee_rate=settings.taker_fee,
            pos_leverage=pos_leverage,
        )
        account.balance_usdt = res.new_balance
        if res.new_qty == 0 and pos is not None:
            await db.delete(pos)
        elif pos is not None:
            pos.quantity = res.new_qty
            if res.new_qty > 0:
                pos.liquidation_price = res.liquidation_price
        fee, realized = res.fee, res.realized_pnl

    order.status = "filled"
    trade = Trade(
        account_id=account.id,
        order_id=order.id,
        symbol=order.symbol,
        side=order.side,
        quantity=order.quantity,
        price=price,
        fee=fee,
        realized_pnl=realized,
    )
    db.add(trade)
    await db.flush()
    await _record_equity(db, account, get_price)
    return trade


def _should_fill(order: Order, price: Decimal) -> bool:
    if order.order_type == "limit":
        if order.side == "buy":
            return price <= order.price
        return price >= order.price
    if order.order_type == "stop_loss":
        return price <= order.trigger_price
    if order.order_type == "take_profit":
        return price >= order.trigger_price
    return False


class MatchingEngine:
    def __init__(self, get_price, session_factory=None):
        self._get_price = get_price
        self._session_factory = session_factory or SessionLocal
        self._lock = asyncio.Lock()

    async def on_price(self, symbol: str, price: Decimal) -> None:
        async with self._lock:
            async with self._session_factory() as db:
                orders = (
                    await db.scalars(
                        select(Order).where(
                            Order.symbol == symbol,
                            Order.status == "open",
                            Order.order_type != "market",
                        )
                    )
                ).all()
                fired: list[tuple[uuid.UUID, Trade]] = []
                for order in orders:
                    if not _should_fill(order, price):
                        continue
                    account = await db.scalar(
                        select(Account)
                        .where(Account.id == order.account_id)
                        .with_for_update()
                    )
                    try:
                        trade = await fill_order(db, account, order, price, self._get_price)
                        fired.append((account.id, trade))
                    except ValueError as exc:
                        logger.warning("order %s cancelled during fill: %s", order.id, exc)
                        order.status = "cancelled"

                # Check liquidations for leveraged long positions
                liq_positions = (
                    await db.scalars(
                        select(Position).where(
                            Position.symbol == symbol,
                            Position.leverage > 1,
                            Position.liquidation_price.isnot(None),
                            Position.liquidation_price >= price,
                        ).with_for_update()
                    )
                ).all()
                for lpos in liq_positions:
                    liq_account = await db.scalar(
                        select(Account).where(Account.id == lpos.account_id).with_for_update()
                    )
                    liq_order = Order(
                        id=uuid.uuid4(),
                        account_id=lpos.account_id,
                        symbol=lpos.symbol,
                        side="sell",
                        order_type="market",
                        quantity=lpos.quantity,
                        status="open",
                        leverage=1,
                    )
                    db.add(liq_order)
                    await db.flush()
                    try:
                        trade = await fill_order(db, liq_account, liq_order, price, self._get_price)
                        fired.append((lpos.account_id, trade))
                        logger.warning("liquidated position %s at %s", lpos.id, price)
                    except ValueError as exc:
                        logger.error("liquidation failed for position %s: %s", lpos.id, exc)

                await db.commit()

            for account_id, trade in fired:
                await hub.push(
                    account_id,
                    {
                        "type": "fill",
                        "symbol": trade.symbol,
                        "side": trade.side,
                        "quantity": str(trade.quantity),
                        "price": str(trade.price),
                    },
                )
