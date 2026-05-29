from decimal import Decimal

from httpx import AsyncClient


async def test_symbols(client: AsyncClient):
    r = await client.get("/market/symbols")
    assert r.status_code == 200
    body = r.json()
    assert "BTC-USDT" in body["symbols"]
    assert "1m" in body["timeframes"]


async def test_ticker_returns_price(client: AsyncClient):
    from services.market_feed import feed
    await feed.set_price("BTC-USDT", Decimal("123.45"))
    r = await client.get("/market/ticker", params={"symbol": "BTC-USDT"})
    assert r.status_code == 200
    assert float(r.json()["price"]) == 123.45


async def test_ticker_unknown_symbol_404(client: AsyncClient):
    r = await client.get("/market/ticker", params={"symbol": "DOGE-USDT"})
    assert r.status_code == 404
