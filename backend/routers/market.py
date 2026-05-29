"""Market data REST endpoints (/market/...).

Implemented in M2. Provides price history, ticker snapshots, and
instrument list endpoints.
"""

from fastapi import APIRouter, HTTPException, Query

from config import settings
from services.market_feed import feed

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/symbols")
async def get_symbols() -> dict:
    return {"symbols": settings.symbols, "timeframes": settings.timeframes}


@router.get("/ticker")
async def get_ticker(symbol: str = Query(...)) -> dict:
    price = feed.get_price(symbol)
    if price is None:
        raise HTTPException(status_code=404, detail="No price for symbol")
    return {"symbol": symbol, "price": price}


@router.get("/candles")
async def get_candles(
    symbol: str = Query(...),
    timeframe: str = Query("1m"),
    limit: int = Query(300, ge=1, le=300),
) -> dict:
    if symbol not in settings.symbols or timeframe not in settings.timeframes:
        raise HTTPException(status_code=400, detail="Unsupported symbol/timeframe")
    candles = await feed.fetch_history(symbol, timeframe, limit)
    return {"symbol": symbol, "timeframe": timeframe, "candles": candles}
