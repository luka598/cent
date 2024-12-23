import asyncio
import os
import ssl
import time
import typing as T

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK
from websockets.sync.client import connect

from cent.data import DataException
from cent.data.t import JSONx, PyO
from cent.ether import Ether, EtherException
from cent.logging import Logger

log = Logger(__name__)


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

    ssl_cert = os.getenv("ETHER_SSL_CERT")
    ssl_key = os.getenv("ETHER_SSL_KEY")
    if ssl_cert and ssl_key:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(
            certfile=ssl_cert,
            keyfile=ssl_key,
        )
    else:
        ssl_context = None

    addr = "0.0.0.0"
    port = int(os.getenv("ETHER_PORT") or 14320)

    server = await serve(handle, addr, port, ssl=ssl_context, ping_interval=60, ping_timeout=60)

    log.info(f"Started jsonx server on {'ws' if ssl_context is None else 'wss'}://{addr}:{port}")
    await server.serve_forever()


class Client:
    def __init__(self, server_uri: str, channel: bytes) -> None:
        self.channel = channel
        self.server_uri = server_uri

        self.ws: T.Any = None
        self.connect()

    def connect(self) -> None:
        log.debug(f"Connecting to {self.channel.hex()}@{self.server_uri}")
        self.ws = connect(self.server_uri)
        self.ws.send(self.channel.hex())
        log.debug(f"Connected to {self.channel.hex()}@{self.server_uri}")

    def send(self, msg: T.Dict, timeout: T.Optional[float] = None) -> None:
        time_start = time.monotonic()

        def timed_out() -> bool:
            if timeout is not None:
                return (time.monotonic() - time_start) > timeout
            else:
                return False

        while not timed_out():
            if not self.ws:
                self.connect()

            try:
                self.ws.send(JSONx.dump(PyO.load(msg)))
                return
            except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError):
                log.warning("Connection closed.")
                self.ws = None

        raise TimeoutError()

    def recv(self, timeout: T.Optional[float] = None) -> T.Dict:
        time_start = time.monotonic()

        def timed_out() -> bool:
            if timeout is not None:
                return (time.monotonic() - time_start) > timeout
            else:
                return False

        while not timed_out():
            if not self.ws:
                self.connect()

            try:
                msg_data = self.ws.recv(timeout=1)
            except TimeoutError:
                continue
            except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError):
                log.warning("Connection closed.")
                self.ws = None
                raise EtherException("Connection closed.")

            try:
                return PyO.dump(JSONx.load(msg_data))
            except DataException as e:
                log.warning(f"Failed to decode msg: {str(e)}")

        raise TimeoutError()


if __name__ == "__main__":
    e = Ether()
    asyncio.run(main(e))
