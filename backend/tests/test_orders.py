from decimal import Decimal

import pytest
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


async def test_limit_buy_triggers_on_price(client: AsyncClient):
    from services.matching_engine import MatchingEngine
    from services.market_feed import feed
    from tests.conftest import TestSession

    headers = await _auth(client)
    # resting buy limit @ 90
    oid = (await client.post(
        "/orders",
        json={"symbol": "BTC-USDT", "side": "buy", "order_type": "limit",
              "quantity": "1", "price": "90"},
        headers=headers,
    )).json()["id"]

    await feed.set_price("BTC-USDT", Decimal("89"))
    engine = MatchingEngine(feed.get_price, session_factory=TestSession)
    await engine.on_price("BTC-USDT", Decimal("89"))

    # order should now be filled and gone from open list
    open_orders = (await client.get("/orders", headers=headers)).json()
    assert open_orders == []
    acc = (await client.get("/account", headers=headers)).json()
    # filled 1 @ 89, fee 89*0.0005=0.0445 -> balance 10000 - 89.0445
    assert float(acc["balance_usdt"]) == 9910.9555


async def test_leveraged_buy_uses_margin_only(client: AsyncClient):
    """Leverage=2 should deduct margin (notional/2) + fee, not full notional."""
    headers = await _auth(client)
    await _set_price("BTC-USDT", "100")
    r = await client.post(
        "/orders",
        json={"symbol": "BTC-USDT", "side": "buy", "order_type": "market",
              "quantity": "1", "leverage": 2},
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["status"] == "filled"
    assert r.json()["leverage"] == 2

    acc = (await client.get("/account", headers=headers)).json()
    # notional=100, margin=50, fee=100*0.0005=0.05, total_cost=50.05
    # new_balance = 10000 - 50.05 = 9949.95
    assert float(acc["balance_usdt"]) == 9949.95

    positions = (await client.get("/account/positions", headers=headers)).json()
    assert len(positions) == 1
    pos = positions[0]
    assert pos["leverage"] == 2
    # liquidation_price = 100 * (1 - 1/2 + 0.01) = 100 * 0.51 = 51
    assert float(pos["liquidation_price"]) == pytest.approx(51.0, rel=1e-4)


async def test_leveraged_sell_uses_position_leverage(client: AsyncClient):
    """Selling a 2x leveraged position should return margin+pnl, not full proceeds."""
    headers = await _auth(client)
    await _set_price("BTC-USDT", "100")

    # Buy 1 BTC @ 100 with 2x leverage: cost = 50 + 0.05 = 50.05
    await client.post(
        "/orders",
        json={"symbol": "BTC-USDT", "side": "buy", "order_type": "market",
              "quantity": "1", "leverage": 2},
        headers=headers,
    )
    acc = (await client.get("/account", headers=headers)).json()
    assert float(acc["balance_usdt"]) == pytest.approx(9949.95, rel=1e-6)

    # Sell 1 BTC @ 100 (same price): balance_change = 99.95 - 100*0.5 = 49.95
    # Net from round trip = -50.05 + 49.95 = -0.10 (fees only)
    await client.post(
        "/orders",
        json={"symbol": "BTC-USDT", "side": "sell", "order_type": "market", "quantity": "1"},
        headers=headers,
    )
    acc = (await client.get("/account", headers=headers)).json()
    # Correct (2x leverage): 9949.95 + 49.95 = 9999.90
    # WRONG (1x fallback):   9949.95 + 99.95 = 10049.90
    assert float(acc["balance_usdt"]) == pytest.approx(9999.90, rel=1e-6)
    # position should be gone
    positions = (await client.get("/account/positions", headers=headers)).json()
    assert positions == []


async def test_liquidation_triggers_on_price_drop(client: AsyncClient):
    """A 10x leveraged position should be liquidated when price drops to liq price."""
    from services.matching_engine import MatchingEngine
    from services.market_feed import feed
    from tests.conftest import TestSession

    headers = await _auth(client)
    await feed.set_price("BTC-USDT", Decimal("100"))

    # Buy 1 BTC @ 100 with leverage=10
    r = await client.post(
        "/orders",
        json={"symbol": "BTC-USDT", "side": "buy", "order_type": "market",
              "quantity": "1", "leverage": 10},
        headers=headers,
    )
    assert r.status_code == 201

    positions = (await client.get("/account/positions", headers=headers)).json()
    assert len(positions) == 1
    # liquidation_price = 100 * (1 - 0.1 + 0.01) = 91
    assert float(positions[0]["liquidation_price"]) == pytest.approx(91.0, rel=1e-4)

    # Trigger price drop to 90, below liquidation price of 91
    engine = MatchingEngine(feed.get_price, session_factory=TestSession)
    await engine.on_price("BTC-USDT", Decimal("90"))

    # Position should be liquidated (deleted)
    positions_after = (await client.get("/account/positions", headers=headers)).json()
    assert positions_after == []
