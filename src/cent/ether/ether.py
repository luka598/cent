import asyncio
import time
import typing as T

from cent.data import Datum, DatumType
from cent.logging import Logger

log = Logger(__name__)

ETHER_BRIDGE_ADDR = b"\x00" * 16
ETHER_BROADCAST_ADDR = b"\xff" * 16


class EtherException(Exception):
    reason: str = ""

    def __init__(self, reason: str, message: T.Optional[str] = None) -> None:
        super().__init__(message if message is not None else reason)


class Ether:
    def __init__(self) -> None:
        self.channels: T.Dict[bytes, T.List[T.Callable[[Datum], T.Awaitable[None]]]] = {}

    async def msg(self, channel: bytes, msg: Datum, timeout: int = 10) -> None:
        if len(channel) != 16:
            raise EtherException("channel length")
        if msg.type != DatumType.MAP:
            raise EtherException("message type")

        log.info(f"MSG: {channel.hex()} - {time.time():.3f}")

        callbacks = []
        if channel == ETHER_BRIDGE_ADDR:
            pass
        elif channel == ETHER_BROADCAST_ADDR:
            pass
        elif channel in self.channels:
            for callback in self.channels[channel]:
                callbacks.append(callback)

        tasks = [asyncio.wait_for(callback, timeout) for callback in callbacks]
        futures = await asyncio.gather(*tasks, return_exceptions=True)
        removed = 0
        for idx, future in enumerate(futures):
            if isinstance(future, Exception):
                log.warning(f"Failed to exec callback {idx} on channel={channel.hex()}: {future.__class__.__name__} - {future}")
                self.channels[channel].pop(idx - removed)
                removed += 1

        return

    def add_callback(self, channel: bytes, callback: T.Callable[[Datum], T.Awaitable[None]]) -> None:
        if len(channel) != 16:
            raise EtherException("channel length")

        if channel not in self.channels:
            self.channels[channel] = []

        self.channels[channel].append(callback)
