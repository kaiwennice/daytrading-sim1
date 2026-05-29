import asyncio
from decimal import Decimal

import pytest

from services.market_feed import MarketFeed


@pytest.fixture
def feed():
    return MarketFeed(
        symbols=["BTC-USDT"],
        public_ws="wss://x",
        business_ws="wss://y",
        rest_base="https://x",
    )


async def test_set_and_get_price(feed):
    await feed.set_price("BTC-USDT", Decimal("100"))
    assert feed.get_price("BTC-USDT") == Decimal("100")


async def test_get_price_unknown_symbol_is_none(feed):
    assert feed.get_price("ETH-USDT") is None


async def test_price_listener_called(feed):
    seen = []

    async def listener(symbol, price):
        seen.append((symbol, price))

    feed.add_price_listener(listener)
    await feed.set_price("BTC-USDT", Decimal("42"))
    assert seen == [("BTC-USDT", Decimal("42"))]


async def test_candle_subscribe_receives_published(feed):
    q = feed.subscribe_candles("BTC-USDT", "1m")
    await feed.publish_candle("BTC-USDT", "1m", {"close": "1"})
    assert q.get_nowait() == {"close": "1"}


async def test_candle_unsubscribe_stops_delivery(feed):
    q = feed.subscribe_candles("BTC-USDT", "1m")
    feed.unsubscribe_candles("BTC-USDT", "1m", q)
    await feed.publish_candle("BTC-USDT", "1m", {"close": "1"})
    assert q.empty()
