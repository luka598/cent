import asyncio
import os
import ssl
import time
import typing as T

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK

from cent.data import DataException
from cent.data.t import JSONx
from cent.logging import Logger

log = Logger(__name__)

CHANNELS: T.Dict[bytes, T.List[T.Any]] = {}


async def handle(ws) -> None:
    ip, port = ws.remote_address
    log.debug(f"CON: {ip}:{port}")

    try:
        channel_data = await ws.recv()
    except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError):
        log.debug("DC: Connection closed")
        return

    if isinstance(channel_data, bytes):
        log.debug("ERR: Msg not string")
        return

    try:
        channel = bytes.fromhex(channel_data)
    except ValueError:
        log.debug("ERR: Failed to decode channel")
        return

    if len(channel) != 16:
        log.debug("ERR: Invalid channel length")
        return

    log.debug(f"AUTH: {ip}:{port}@{channel.hex()}")

    if channel not in CHANNELS:
        CHANNELS[channel] = []
    CHANNELS[channel].append(ws)

    while True:
        try:
            msg_data = await ws.recv()
            msg = JSONx.load(msg_data)

            tasks = []
            for ws in CHANNELS[channel]:
                tasks.append(asyncio.wait_for(ws.send(msg_data), 10))
            futures = await asyncio.gather(*tasks, return_exceptions=True)
            removed = 0
            for idx, future in enumerate(futures):
                if isinstance(future, Exception):
                    log.debug(
                        f"Failed to exec callback {idx} on channel={channel.hex()}: {future.__class__.__name__} - {future}"
                    )
                    CHANNELS[channel].pop(idx - removed)
                    removed += 1

        except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError):
            log.debug(f"DC: {ip}:{port}@{channel.hex()}")
            break
        except DataException as exc:
            log.debug(f"INV_PKT: {channel.hex()} - {int(time.time())} - {str(exc)}")


async def main() -> None:
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

    server = await serve(handle, addr, port, ssl=ssl_context, ping_interval=20, ping_timeout=20)

    log.info(f"Starting server on {'ws' if ssl_context is None else 'wss'}://{addr}:{port}")
    await server.serve_forever()


def start_server() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    start_server()
