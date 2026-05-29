import asyncio
import logging
from decimal import Decimal

logger = logging.getLogger("uvicorn")


class MarketFeed:
    """Process-wide live market data hub.

    Holds latest ticker price per symbol and a candle pub/sub. Network I/O
    (OKX WebSocket loops) lives in start()/_run_* and is intentionally absent
    from the core so the logic is unit-testable without a connection.
    """

    def __init__(self, symbols, public_ws, business_ws, rest_base):
        self._symbols = list(symbols)
        self._public_ws = public_ws
        self._business_ws = business_ws
        self._rest_base = rest_base

        self._prices: dict[str, Decimal] = {}
        self._price_listeners: list = []
        self._candle_subs: dict[tuple[str, str], set[asyncio.Queue]] = {}
        self._tasks: list[asyncio.Task] = []
        self._started = False

    # ---------- price store ----------
    def get_price(self, symbol: str) -> Decimal | None:
        return self._prices.get(symbol)

    async def set_price(self, symbol: str, price: Decimal) -> None:
        self._prices[symbol] = price
        for cb in list(self._price_listeners):
            await cb(symbol, price)

    def add_price_listener(self, cb) -> None:
        self._price_listeners.append(cb)

    def remove_price_listener(self, cb) -> None:
        if cb in self._price_listeners:
            self._price_listeners.remove(cb)

    # ---------- candle pub/sub ----------
    def subscribe_candles(self, symbol: str, timeframe: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._candle_subs.setdefault((symbol, timeframe), set()).add(q)
        return q

    def unsubscribe_candles(self, symbol: str, timeframe: str, q: asyncio.Queue) -> None:
        subs = self._candle_subs.get((symbol, timeframe))
        if subs:
            subs.discard(q)
            if not subs:
                del self._candle_subs[(symbol, timeframe)]

    async def publish_candle(self, symbol: str, timeframe: str, candle: dict) -> None:
        for q in list(self._candle_subs.get((symbol, timeframe), ())):
            q.put_nowait(candle)
