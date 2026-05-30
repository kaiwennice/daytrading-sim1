from decimal import Decimal

from httpx import AsyncClient

from tests.test_auth import _register_capturing_code, _verify, _login, DEFAULT_EMAIL


async def _auth(client: AsyncClient) -> dict:
    _, code = await _register_capturing_code(client)
    await _verify(client, DEFAULT_EMAIL, code)
    token = (await _login(client)).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _set_price(symbol, price):
    from services.market_feed import feed
    await feed.set_price(symbol, Decimal(price))


async def test_market_buy_fills_and_updates_account(client: AsyncClient):
    headers = await _auth(client)
    await _set_price("BTC-USDT", "100")
    r = await client.post(
        "/orders",
        json={"symbol": "BTC-USDT", "side": "buy", "order_type": "market", "quantity": "1"},
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["status"] == "filled"

    acc = (await client.get("/account", headers=headers)).json()
    # started 10000, cost 100 + fee 0.05
    assert float(acc["balance_usdt"]) == 9899.95


async def test_market_buy_without_price_503(client: AsyncClient):
    headers = await _auth(client)
    # SOL price never set
    r = await client.post(
        "/orders",
        json={"symbol": "SOL-USDT", "side": "buy", "order_type": "market", "quantity": "1"},
        headers=headers,
    )
    assert r.status_code == 503


async def test_market_buy_insufficient_balance_400(client: AsyncClient):
    headers = await _auth(client)
    await _set_price("BTC-USDT", "100")
    r = await client.post(
        "/orders",
        json={"symbol": "BTC-USDT", "side": "buy", "order_type": "market", "quantity": "1000"},
        headers=headers,
    )
    assert r.status_code == 400


async def test_limit_order_rests_open(client: AsyncClient):
    headers = await _auth(client)
    r = await client.post(
        "/orders",
        json={"symbol": "BTC-USDT", "side": "buy", "order_type": "limit",
              "quantity": "1", "price": "50"},
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["status"] == "open"

    open_orders = (await client.get("/orders", headers=headers)).json()
    assert len(open_orders) == 1


async def test_cancel_open_order(client: AsyncClient):
    headers = await _auth(client)
    oid = (await client.post(
        "/orders",
        json={"symbol": "BTC-USDT", "side": "buy", "order_type": "limit",
              "quantity": "1", "price": "50"},
        headers=headers,
    )).json()["id"]
    r = await client.delete(f"/orders/{oid}", headers=headers)
    assert r.status_code == 200
    open_orders = (await client.get("/orders", headers=headers)).json()
    assert open_orders == []


async def test_account_reflects_position_after_buy(client: AsyncClient):
    headers = await _auth(client)
    await _set_price("BTC-USDT", "100")
    await client.post(
        "/orders",
        json={"symbol": "BTC-USDT", "side": "buy", "order_type": "market", "quantity": "1"},
        headers=headers,
    )
    # price moves up to 120
    await _set_price("BTC-USDT", "120")
    acc = (await client.get("/account", headers=headers)).json()
    # cash 9899.95 + position mark 1*120 = 10019.95 ; unrealized = (120-100)*1 = 20
    assert float(acc["total_equity"]) == 10019.95
    assert float(acc["unrealized_pnl"]) == 20.0
