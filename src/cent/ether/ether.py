import asyncio
import time
import typing as T

from cent.data import Datum, DatumType
from cent.logging import Logger

log = Logger(__name__)

ETHER_BROADCAST_ADDR = b"\xff" * 16
ETHER_BRIDGE_ADDR = b"\x00" * 16


class EtherException(Exception):
    pass


class Ether:
    def __init__(self) -> None:
        self.channels: T.Dict[bytes, T.List[T.Callable[[Datum], T.Any]]] = {}
        self.callback_iota = 0

        self.channels[ETHER_BRIDGE_ADDR] = []
        self.channels[ETHER_BROADCAST_ADDR] = []

    async def msg_channel(self, channel: bytes, msg: Datum) -> None:
        tasks = []
        for callback in self.channels[channel]:
            tasks.append(callback(msg))

        futures = await asyncio.gather(*tasks, return_exceptions=True)
        removed = 0
        for idx, future in enumerate(futures):
            if isinstance(future, Exception):
                log.warning(f"Failed to exec callback {idx} on channel={channel.hex()}: {future.__class__.__name__} - {future}")
                self.channels[channel].pop(idx - removed)
                removed += 1

    async def msg(
        self,
        channel: bytes,
        msg: Datum,
    ) -> None:
        if len(channel) != 16:
            return
        if channel not in self.channels:
            return
        if msg.type != DatumType.MAP:
            return

        log.info(f"MSG: {channel.hex()} - {int(time.time())}")

        if channel == ETHER_BRIDGE_ADDR:
            pass
        elif channel == ETHER_BROADCAST_ADDR:
            for channel in self.channels:
                await self.msg_channel(channel, msg)
        else:
            await self.msg_channel(channel, msg)

    def add_callback(
        self,
        channel: bytes,
        callback: T.Callable[[Datum], T.Any],
    ) -> None:
        if len(channel) != 16:
            return
        if channel not in self.channels:
            self.channels[channel] = []

        log.info(f"CON: {channel.hex()} - {int(time.time())}")

        self.channels[channel].append(callback)
