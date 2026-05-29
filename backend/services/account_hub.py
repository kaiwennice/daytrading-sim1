import uuid


class AccountHub:
    """In-memory registry of authenticated account WebSocket connections."""

    def __init__(self):
        self._conns: dict[uuid.UUID, set] = {}

    def register(self, account_id: uuid.UUID, ws) -> None:
        self._conns.setdefault(account_id, set()).add(ws)

    def unregister(self, account_id: uuid.UUID, ws) -> None:
        conns = self._conns.get(account_id)
        if conns:
            conns.discard(ws)
            if not conns:
                del self._conns[account_id]

    async def push(self, account_id: uuid.UUID, event: dict) -> None:
        for ws in list(self._conns.get(account_id, ())):
            try:
                await ws.send_json(event)
            except Exception:  # noqa: BLE001
                pass


hub = AccountHub()
