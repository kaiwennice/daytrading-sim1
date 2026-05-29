import uuid

from services.account_hub import hub


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send_json(self, data):
        self.sent.append(data)


async def test_push_delivers_to_registered_socket():
    acc = uuid.uuid4()
    ws = FakeWS()
    hub.register(acc, ws)
    await hub.push(acc, {"type": "fill", "x": 1})
    assert ws.sent == [{"type": "fill", "x": 1}]
    hub.unregister(acc, ws)


async def test_push_to_unknown_account_is_noop():
    await hub.push(uuid.uuid4(), {"type": "fill"})  # should not raise
