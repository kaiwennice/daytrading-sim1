"""Backend -> frontend account state push (/ws/account).

Auth via ?token= (browsers can't set Authorization on WebSocket). On fills the
matching engine / order route pushes events through services.account_hub.
"""
import asyncio
import uuid

import jwt
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from database import SessionLocal
from models.account import Account
from services.account_hub import hub
from services.auth_service import decode_access_token


async def account_endpoint(ws: WebSocket) -> None:
    token = ws.query_params.get("token", "")
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        await ws.close(code=1008)
        return

    async with SessionLocal() as db:
        account = await db.scalar(select(Account).where(Account.user_id == user_id))
    if account is None:
        await ws.close(code=1008)
        return

    await ws.accept()
    hub.register(account.id, ws)
    try:
        while True:
            await ws.receive_text()  # keep alive; ignore client messages
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        hub.unregister(account.id, ws)
