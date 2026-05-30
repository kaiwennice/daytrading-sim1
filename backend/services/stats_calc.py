from decimal import Decimal


def compute_stats(realized_pnls: list[Decimal | None]) -> dict:
    """realized_pnls: one entry per trade (None for opening buys, a number for
    closing sells)."""
    trade_count = len(realized_pnls)
    closed = [p for p in realized_pnls if p is not None]
    wins = [p for p in closed if p > 0]
    losses = [p for p in closed if p < 0]

    closed_count = len(closed)
    win_count = len(wins)
    win_rate = (win_count / closed_count) if closed_count else 0.0
    avg_win = (sum(wins) / len(wins)) if wins else Decimal("0")
    avg_loss = (sum(losses) / len(losses)) if losses else Decimal("0")
    ratio = float(avg_win / abs(avg_loss)) if losses and avg_loss != 0 else None
    total = sum(closed) if closed else Decimal("0")

    return {
        "trade_count": trade_count,
        "closed_count": closed_count,
        "win_count": win_count,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_loss_ratio": ratio,
        "total_realized_pnl": total,
    }
