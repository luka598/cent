import os
import threading
import typing as T

from cent.data import Datum

LOOP_TIME = 1 / int(os.getenv("ETHER_FREQ", 1000))
SLOW_LOOP_TIME = 1 / int(os.getenv("ETHER_SLOW_FREQ", 1))

MSG_t = T.Tuple[bytes, Datum]

TV = T.TypeVar("TV")


class Queue(T.Generic[TV]):
    def __init__(self, max_size: int = 1000) -> None:
        self.lock = threading.Lock()
        self.not_empty = threading.Event()

        self.store = []
        self.n = 0
        self.max_size = max_size

    def put(self, item: TV) -> None:
        with self.lock:
            if self.n == self.max_size:
                self.store.pop(0)
                self.store.append(item)
            else:
                self.store.append(item)
                self.n += 1
                self.not_empty.set()

    def get(self, timeout: T.Optional[float] = None) -> TV:
        self.not_empty.wait(timeout=timeout)
        with self.lock:
            if self.n == 0:
                raise RuntimeError
            elif self.n == 1:
                self.not_empty.clear()

            self.n -= 1

            return self.store.pop(0)


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
