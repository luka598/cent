import asyncio
import typing as T
from uuid import uuid4

import logigng
from tuil.env import get_var
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK
from websockets.sync.client import connect

from cent.data.jsonx import JSONX
from cent.ether import Ether, EtherException

log = logigng.Logger(__name__)


async def main(e: Ether):
    async def handle(ws):
        try:
            channel_data = await ws.recv()
        except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError):
            return
        if isinstance(channel_data, bytes):
            return
        try:
            channel = bytes.fromhex(channel_data)
        except ValueError:
            return
        if len(channel) != 16:
            return

        e.add_callback(channel, lambda msg: ws.send(JSONX.dump(msg)))

        while True:
            try:
                msg_data = await ws.recv()
            except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError):
                return

            try:
                msg = JSONX.load(msg_data)
                await e.msg(channel, msg)
            except JSONX.Exception:
                pass

    server_jsonx = await serve(handle, "0.0.0.0", 14320, ping_interval=60, ping_timeout=60)
    log.info("Started jsonx server on 0.0.0.0:14320")
    await server_jsonx.serve_forever()


DEFAULT_CHANNEL = bytes.fromhex(get_var("ETHER_CHANNEL", uuid4().bytes.hex()))
DEFAULT_SERVER_URI = get_var("ETHER_SERVER_URI", "ws://localhost:14320")


class Client:
    def __init__(
        self, server_uri: T.Optional[str] = None, channel: T.Optional[bytes] = None
    ) -> None:
        self.channel = channel or DEFAULT_CHANNEL
        self.server_uri = server_uri or DEFAULT_SERVER_URI

        self.connect()

    def connect(self) -> None:
        self.ws = connect(self.server_uri)
        self.ws.send(self.channel.hex())

    def send(self, msg: T.Dict) -> None:
        try:
            self.ws.send(JSONX.dump(msg))
        except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError):
            log.warning("Connection closed, trying to reconnect.")
            try:
                self.connect()
            except Exception:
                raise EtherException("Connection closed")

    def recv(self) -> T.Dict:
        while True:
            try:
                msg_data = self.ws.recv()
            except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError):
                try:
                    self.connect()
                    continue
                except Exception:
                    raise EtherException("Connection closed")

            try:
                return JSONX.load(msg_data)
            except JSONX.Exception:
                pass


if __name__ == "__main__":
    e = Ether()
    asyncio.run(main(e))
