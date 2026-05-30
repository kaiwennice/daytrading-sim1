import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_user
from models.account import Account
from models.equity_snapshot import EquitySnapshot
from models.order import Order
from models.position import Position
from models.trade import Trade
from models.user import User
from services.market_feed import feed

router = APIRouter(prefix="/account", tags=["account"])


class AccountResponse(BaseModel):
    balance_usdt: Decimal
    initial_balance: Decimal
    total_equity: Decimal
    unrealized_pnl: Decimal
    reset_count: int


class ResetRequest(BaseModel):
    initial_balance: Decimal = Field(ge=1000, le=1_000_000)


async def _build_response(db, account: Account) -> AccountResponse:
    positions = (
        await db.scalars(select(Position).where(Position.account_id == account.id))
    ).all()
    market_value = Decimal("0")
    unrealized = Decimal("0")
    for p in positions:
        mark = feed.get_price(p.symbol)
        if mark is None:
            mark = p.avg_cost
        market_value += p.quantity * mark
        unrealized += (mark - p.avg_cost) * p.quantity
    return AccountResponse(
        balance_usdt=account.balance_usdt,
        initial_balance=account.initial_balance,
        total_equity=account.balance_usdt + market_value,
        unrealized_pnl=unrealized,
        reset_count=account.reset_count,
    )


@router.get("", response_model=AccountResponse)
async def get_account(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AccountResponse:
    account = await db.scalar(select(Account).where(Account.user_id == user.id))
    return await _build_response(db, account)


@router.post("/reset", response_model=AccountResponse)
async def reset_account(
    body: ResetRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccountResponse:
    account = await db.scalar(select(Account).where(Account.user_id == user.id))

    for model in (Trade, Order, Position, EquitySnapshot):
        await db.execute(delete(model).where(model.account_id == account.id))

    account.balance_usdt = body.initial_balance
    account.initial_balance = body.initial_balance
    account.reset_count += 1
    await db.commit()
    await db.refresh(account)
    return await _build_response(db, account)


class TradeItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    realized_pnl: Decimal | None
    executed_at: datetime


class PositionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    symbol: str
    side: str
    quantity: Decimal
    avg_cost: Decimal
    leverage: int
    liquidation_price: Decimal | None


@router.get("/trades", response_model=list[TradeItem])
async def list_trades(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Trade]:
    account = await db.scalar(select(Account).where(Account.user_id == user.id))
    return list(
        (
            await db.scalars(
                select(Trade)
                .where(Trade.account_id == account.id)
                .order_by(Trade.executed_at.desc())
                .limit(100)
            )
        ).all()
    )


@router.get("/positions", response_model=list[PositionItem])
async def list_positions(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Position]:
    account = await db.scalar(select(Account).where(Account.user_id == user.id))
    return list(
        (await db.scalars(select(Position).where(Position.account_id == account.id))).all()
    )
