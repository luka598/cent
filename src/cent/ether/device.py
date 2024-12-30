import os
import queue
import typing as T

from cent.data import Datum

LOOP_TIME = 1 / int(os.getenv("ETHER_FREQ", 1000))
SLOW_LOOP_TIME = 1 / int(os.getenv("ETHER_SLOW_FREQ", 1))

MSG_t = T.Tuple[bytes, Datum]

TV = T.TypeVar("TV")


class Queue(T.Generic[TV]):
    def __init__(self) -> None:
        self.queue = queue.Queue()

    def put(self, item: TV) -> None:
        self.queue.put(item)

    def get(self, timeout: T.Optional[float] = None) -> TV:
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError


class Device:
    def __init__(self) -> None:
        self.events: Queue[str] = Queue()
        self.active = False

    def add_event(self, event: str) -> None:
        self.events.put(event)

    def stop(self) -> None:
        self.add_event("stop")

    def start(self) -> None:
        raise NotImplementedError
