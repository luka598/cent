import threading
import time
import weakref

from cent.ether.main import ConnectorI


class ThreadedConnector(ConnectorI):
    def __init__(self, min_loop_time: float = 0.0) -> None:
        self.incoming = []
        self.outgoing = []

        self.MIN_LOOP_TIME = min_loop_time

        self.thread = threading.Thread(target=self.loop)
        self.stop_event = threading.Event()
        self.main_thread_ref = weakref.ref(threading.main_thread())

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join()

    @property
    def stopped(self) -> bool:
        if not (self.main_thread_ref() and self.main_thread_ref().is_alive()):  # type: ignore
            self.stop_event.set()

        return self.stop_event.is_set()

    @stopped.setter
    def stopped(self, value: bool) -> None:
        if value:
            self.stop_event.set()
        else:
            self.stop_event.clear()

    def loop(self) -> None:
        try:
            self.begin()
        except Exception as e:
            self.stopped = True
            raise e

        while not self.stopped:
            start_time = time.monotonic()

            try:
                self.tick()
            except Exception as e:
                self.stopped = True
                raise e

            diff = time.monotonic() - start_time
            if diff < self.MIN_LOOP_TIME:
                time.sleep(diff)

        try:
            self.end()
        except Exception as e:
            self.stopped = True
            raise e

    def begin(self) -> None:
        raise NotImplementedError

    def tick(self) -> None:
        raise NotImplementedError

    def end(self) -> None:
        raise NotImplementedError


class DumbConnector(ThreadedConnector):
    def __init__(self, other: ThreadedConnector) -> None:
        super().__init__()
        self.other = other

    def begin(self) -> None:
        pass

    def tick(self) -> None:
        if len(self.outgoing) != 0:
            self.other.incoming.append(self.outgoing.pop(0))

        if len(self.outgoing) != 0:
            self.incoming.append(self.other.outgoing.pop(0))

    def end(self) -> None:
        pass
