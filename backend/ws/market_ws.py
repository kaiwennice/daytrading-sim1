"""Backend -> frontend market data push (/ws/market).

Implemented in M2. Relays OKX candle/ticker data (via services/market_feed.py)
to subscribed frontend clients.
"""


async def market_endpoint(websocket):
    """Placeholder for market WebSocket endpoint."""
    pass
