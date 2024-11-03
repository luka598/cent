import asyncio
import time
import typing as T

import logigng
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK
from websockets.sync.client import connect

from cent.data import JSONx, Py
from cent.data.meta import DataException
from cent.ether import Ether, EtherException

log = logigng.Logger(__name__)


async def main(e: Ether) -> None:
    async def handle(ws) -> None:
        try:
            channel_data = await ws.recv()
        except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError):
            log.warning(f"DC: {int(time.time())}")
            return
        if isinstance(channel_data, bytes):
            log.warning(f"ERR: {int(time.time())} - Msg not string")
            return
        try:
            channel = bytes.fromhex(channel_data)
        except ValueError:
            log.warning(f"ERR: {int(time.time())} - Failed to decode channel")
            return
        if len(channel) != 16:
            log.warning(f"ERR: {int(time.time())} - Invalid channel length")
            return

        e.add_callback(channel, lambda msg: ws.send(JSONx.dump(msg)))

        while True:
            try:
                msg_data = await ws.recv()
            except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError):
                log.warning(f"DC: {channel.hex()} - {int(time.time())}")
                break

            try:
                msg = JSONx.load(msg_data)
                await e.msg(channel, msg)
            except DataException as exc:
                log.warning(f"INV_PKT: {channel.hex()} - {int(time.time())} - {str(exc)}")

    server_jsonx = await serve(handle, "0.0.0.0", 14320, ping_interval=60, ping_timeout=60)
    log.info("Started jsonx server on 0.0.0.0:14320")
    await server_jsonx.serve_forever()


class Client:
    def __init__(
        self,
        server_uri: str,
        channel: bytes,
    ) -> None:
        self.channel = channel
        self.server_uri = server_uri

        self.connect()

    def connect(self) -> None:
        self.ws = connect(self.server_uri)
        self.ws.send(self.channel.hex())

    def send(self, msg: T.Dict) -> None:
        try:
            self.ws.send(JSONx.dump(Py.load(msg)))
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
                return Py.dump(JSONx.load(msg_data))
            except DataException as e:
                log.warning(f"Failed to decode msg: {str(e)}")


if __name__ == "__main__":
    e = Ether()
    asyncio.run(main(e))
