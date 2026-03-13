import websockets
import json
from .const import WS_BASE

class MyRideWebsocket:

    def __init__(self, token, callback):
        self.token = token
        self.callback = callback

    async def start(self):

        url = f"{WS_BASE}?access_token={self.token}"

        async with websockets.connect(url) as ws:

            await ws.send('{"protocol":"json","version":1}\x1e')

            while True:

                msg = await ws.recv()

                messages = msg.split("\x1e")

                for m in messages:

                    if not m:
                        continue

                    data = json.loads(m)

                    await self.callback(data)