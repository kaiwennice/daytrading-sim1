"""Market data REST endpoints (/market/...).

Implemented in M2. Provides price history, ticker snapshots, and
instrument list endpoints.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/market", tags=["market"])
