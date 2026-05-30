from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class EquityPoint(BaseModel):
    recorded_at: datetime
    total_equity: Decimal


class StatsResponse(BaseModel):
    equity_curve: list[EquityPoint]
    trade_count: int
    closed_count: int
    win_count: int
    win_rate: float
    avg_win: Decimal
    avg_loss: Decimal
    profit_loss_ratio: float | None
    total_realized_pnl: Decimal
