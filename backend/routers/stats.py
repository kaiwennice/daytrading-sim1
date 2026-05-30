from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_user
from models.account import Account
from models.equity_snapshot import EquitySnapshot
from models.trade import Trade
from models.user import User
from schemas.stats import EquityPoint, StatsResponse
from services.stats_calc import compute_stats

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
async def get_stats(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> StatsResponse:
    account = await db.scalar(select(Account).where(Account.user_id == user.id))

    trades = (
        await db.scalars(
            select(Trade).where(Trade.account_id == account.id).order_by(Trade.executed_at)
        )
    ).all()
    metrics = compute_stats([t.realized_pnl for t in trades])

    snapshots = (
        await db.scalars(
            select(EquitySnapshot)
            .where(EquitySnapshot.account_id == account.id)
            .order_by(EquitySnapshot.recorded_at)
        )
    ).all()
    curve = [
        EquityPoint(recorded_at=s.recorded_at, total_equity=s.total_equity)
        for s in snapshots
    ]

    return StatsResponse(equity_curve=curve, **metrics)
