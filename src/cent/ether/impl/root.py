import threading
import time
import typing as T
import weakref

from cent.data import Datum
from cent.ether.device import LOOP_TIME, SLOW_LOOP_TIME, Device, MSG_t, Queue
from cent.logging import Logger

log = Logger(__name__)


class Com(Device):
    def __init__(self, parent: "Root") -> None:
        super().__init__()
        self.parent_ref: weakref.ReferenceType[Root] = weakref.ref(parent)
        self.incoming: Queue[MSG_t] = Queue()
        self.outgoing: Queue[MSG_t] = Queue()

    @property
    def parent(self) -> "Root":
        parent = self.parent_ref()
        if parent is None:
            raise RuntimeError
        else:
            return parent


class Root(Device):
    def __init__(self) -> None:
        super().__init__()
        self.incoming: Queue[MSG_t] = Queue()
        self.outgoing: Queue[MSG_t] = Queue()

        self.coms: T.List[Com] = []

        self.main_thread_ref = weakref.ref(threading.main_thread())
        weakref.finalize(self, self.cleanup)

    def cleanup(self) -> None:
        pass

    def start(self) -> None:
        self.active = True
        self.thread_a = threading.Thread(target=self.main_loop, name="root_device|main_loop")
        self.thread_b = threading.Thread(target=self.is_active_loop, name="root_device|is_active_loop")
        self.thread_a.start()
        self.thread_b.start()

    def stop(self) -> None:
        self.add_event("stop")

    def is_active_loop(self) -> None:
        while self.active:
            time.sleep(SLOW_LOOP_TIME)

            main_thread = self.main_thread_ref()
            if main_thread is None:
                self.stop()
                continue
            if not main_thread.is_alive():
                self.stop()
                continue

    def main_loop(self) -> None:
        while self.active:
            try:
                event = self.events.get(timeout=LOOP_TIME)
            except TimeoutError:
                continue

            if event == "stop":
                self._stop()

            elif event == "com_stopped":
                self._remove_inactive()

            elif event == "new_incoming":
                self._fetch_incoming()

            elif event == "new_outgoing":
                self._push_outgoing()

    def _stop(self) -> None:
        self.active = False
        for child in self.coms:
            child.add_event("stop")

    def _remove_inactive(self) -> None:
        removed = 0
        for idx in range(len(self.coms)):
            if not self.coms[idx - removed].active:
                log.debug(f"Removing stopped com: {idx - removed} | {self.coms[idx - removed]}")
                self.coms.pop(idx - removed)
                removed += 1

    def _fetch_incoming(self) -> None:
        for child in self.coms:
            try:
                self.incoming.put(child.incoming.get(0))
            except TimeoutError:
                pass

    def _push_outgoing(self) -> None:
        try:
            msg = self.outgoing.get(LOOP_TIME)
        except TimeoutError:
            return

        for child in self.coms:
            child.outgoing.put(msg)
            child.add_event("new_outgoing")

    def add_com(self, com: Com) -> None:
        log.debug(f"Adding com: {len(self.coms)} | {type(com).__name__} - {com}")
        self.coms.append(com)

    def send(self, channel: bytes, value: Datum) -> None:
        self.outgoing.put((channel, value))
        self.add_event("new_outgoing")

    def recv(self, timeout: T.Optional[float] = None) -> MSG_t:
        return self.incoming.get(timeout=timeout)
