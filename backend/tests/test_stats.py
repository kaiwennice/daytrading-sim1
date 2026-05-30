from decimal import Decimal

from services.stats_calc import compute_stats


def test_empty():
    s = compute_stats([])
    assert s["trade_count"] == 0
    assert s["closed_count"] == 0
    assert s["win_rate"] == 0.0
    assert s["profit_loss_ratio"] is None


def test_win_rate_and_ratio():
    # realized pnls of closing (sell) trades: +50, -20, +30 ; buys have None
    pnls = [None, Decimal("50"), Decimal("-20"), Decimal("30")]
    s = compute_stats(pnls)
    assert s["trade_count"] == 4
    assert s["closed_count"] == 3
    assert s["win_count"] == 2
    assert round(s["win_rate"], 4) == round(2 / 3, 4)
    assert s["avg_win"] == Decimal("40")          # (50+30)/2
    assert s["avg_loss"] == Decimal("-20")        # (-20)/1
    assert s["profit_loss_ratio"] == 2.0          # 40 / 20
    assert s["total_realized_pnl"] == Decimal("60")


from httpx import AsyncClient

from tests.test_orders import _auth, _set_price


async def test_stats_endpoint_after_round_trip(client: AsyncClient):
    headers = await _auth(client)
    await _set_price("BTC-USDT", "100")
    await client.post("/orders", json={"symbol": "BTC-USDT", "side": "buy",
        "order_type": "market", "quantity": "1"}, headers=headers)
    await _set_price("BTC-USDT", "150")
    await client.post("/orders", json={"symbol": "BTC-USDT", "side": "sell",
        "order_type": "market", "quantity": "1"}, headers=headers)

    r = await client.get("/stats", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["closed_count"] == 1
    assert body["win_count"] == 1
    assert body["win_rate"] == 1.0
    assert len(body["equity_curve"]) >= 2
