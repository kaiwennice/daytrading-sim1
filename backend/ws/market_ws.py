"""Backend -> frontend market data push (/ws/market).

Client connects with ?symbol=BTC-USDT&timeframe=1m. We send a snapshot of
historical candles, then stream live candle updates from the MarketFeed.
"""
import asyncio

from fastapi import WebSocket, WebSocketDisconnect

from config import settings
from services.market_feed import feed


async def market_endpoint(ws: WebSocket) -> None:
    symbol = ws.query_params.get("symbol", "BTC-USDT")
    timeframe = ws.query_params.get("timeframe", "1m")
    if symbol not in settings.symbols or timeframe not in settings.timeframes:
        await ws.close(code=1008)
        return

    await ws.accept()
    try:
        history = await feed.fetch_history(symbol, timeframe, 300)
        await ws.send_json({"type": "snapshot", "candles": history})
    except Exception:  # noqa: BLE001
        await ws.send_json({"type": "snapshot", "candles": []})

    q = feed.subscribe_candles(symbol, timeframe)
    try:
        while True:
            candle = await q.get()
            await ws.send_json({"type": "candle", "candle": candle})
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        feed.unsubscribe_candles(symbol, timeframe, q)
