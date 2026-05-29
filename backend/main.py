from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from config import settings
from database import engine
from routers import account, auth, orders, stats
from routers import market as market_router
from services.market_feed import feed
from ws import account_ws, market_ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    from services.matching_engine import MatchingEngine
    engine_inst = MatchingEngine(feed.get_price)
    feed.add_price_listener(engine_inst.on_price)
    await feed.start()
    yield
    await feed.stop()


app = FastAPI(title="DaySim API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(account.router)
app.include_router(market_router.router)
app.include_router(orders.router)
app.include_router(stats.router)

app.add_api_websocket_route("/ws/market", market_ws.market_endpoint)
app.add_api_websocket_route("/ws/account", account_ws.account_endpoint)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok"}
