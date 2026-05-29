import asyncio
import json
import logging
from decimal import Decimal

import httpx
import websockets

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

    async def fetch_history(self, symbol: str, timeframe: str, limit: int = 300) -> list[dict]:
        url = f"{self._rest_base}/api/v5/market/candles"
        params = {"instId": symbol, "bar": timeframe, "limit": str(limit)}
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.get(url, params=params)
            resp.raise_for_status()
            rows = resp.json().get("data", [])
        out = []
        for row in reversed(rows):
            out.append({
                "time": int(row[0]) // 1000,
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
            })
        return out

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._tasks.append(asyncio.create_task(self._run_public()))
        self._tasks.append(asyncio.create_task(self._run_business()))
        logger.info("MarketFeed started for %s", self._symbols)

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        self._tasks.clear()
        self._started = False

    async def _run_public(self) -> None:
        sub = {
            "op": "subscribe",
            "args": [{"channel": "tickers", "instId": s} for s in self._symbols],
        }
        while True:
            try:
                async with websockets.connect(self._public_ws, ping_interval=20) as ws:
                    await ws.send(json.dumps(sub))
                    async for raw in ws:
                        msg = json.loads(raw)
                        if msg.get("arg", {}).get("channel") != "tickers":
                            continue
                        for d in msg.get("data", []):
                            await self.set_price(d["instId"], Decimal(d["last"]))
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning("public ws error, reconnecting: %s", exc)
                await asyncio.sleep(2)

    async def _run_business(self) -> None:
        while True:
            try:
                async with websockets.connect(self._business_ws, ping_interval=20) as ws:
                    sent: set[tuple[str, str]] = set()
                    while True:
                        wanted = set(self._candle_subs.keys())
                        new = wanted - sent
                        if new:
                            await ws.send(json.dumps({
                                "op": "subscribe",
                                "args": [
                                    {"channel": f"candle{tf}", "instId": sym}
                                    for (sym, tf) in new
                                ],
                            }))
                            sent |= new
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        except asyncio.TimeoutError:
                            continue
                        msg = json.loads(raw)
                        ch = msg.get("arg", {}).get("channel", "")
                        inst = msg.get("arg", {}).get("instId", "")
                        if not ch.startswith("candle"):
                            continue
                        tf = ch.removeprefix("candle")
                        for row in msg.get("data", []):
                            await self.publish_candle(inst, tf, {
                                "time": int(row[0]) // 1000,
                                "open": float(row[1]),
                                "high": float(row[2]),
                                "low": float(row[3]),
                                "close": float(row[4]),
                            })
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning("business ws error, reconnecting: %s", exc)
                await asyncio.sleep(2)


from config import settings  # noqa: E402

feed = MarketFeed(
    symbols=settings.symbols,
    public_ws=settings.okx_public_ws,
    business_ws=settings.okx_business_ws,
    rest_base=settings.okx_rest_base,
)
