import asyncio
from utils import to_str
from framework import ws

class Websocket(ws.RedisChannelWebsocket):
    async def pre_send(self, msg):
        return to_str(msg)

class EchoHandler(ws.WsSendMixin):
    def __init__(self, ws) -> None:
        self.ws = ws

    async def __call__(self, msg):
        await self.send(msg)

async def echo(request, ws):
    try:
        handler = EchoHandler(ws)
        coro = Websocket(request, ws, handler, channel_names='justecho')()
        await asyncio.shield(coro)
    except:
        pass
    finally:
        pass
