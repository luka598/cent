import threading
import time
import typing as T

from cent.data import Datum
from cent.data.t import PyO
from cent.logging import Logger

log = Logger(__name__)

MESSAGE_t = T.Tuple[bytes, Datum]


class ConnectorI:
    incoming: T.List[MESSAGE_t]
    outgoing: T.List[MESSAGE_t]
    stopped: bool

    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def loop(self, min_time: float = 0) -> None:
        raise NotImplementedError

    def begin(self) -> None:
        raise NotImplementedError

    def tick(self) -> None:
        raise NotImplementedError

    def end(self) -> None:
        raise NotImplementedError


class Node:
    def __init__(self) -> None:
        self.incoming: T.List[MESSAGE_t] = []  # Connector.incoming -> Node.incoming
        self.outgoing: T.List[MESSAGE_t] = []  # Node.outgoing -> Connector.outgoing
        self.connectors: T.List[ConnectorI] = []

        self.thread = threading.Thread(target=self.tick, daemon=True)  # TODO: Move threading stuff in another file

    def add_connector(self, connector: ConnectorI) -> None:
        log.debug(f"Adding connector: {len(self.connectors)} | {type(connector).__name__} - {connector}")
        self.connectors.append(connector)
        connector.start()  # NOTE: Order matters; handle does not need another thread

    def start(self) -> None:
        self.thread.start()

    def tick(self) -> None:
        while True:
            # Remove stopped connectors
            removed = 0
            for idx in range(len(self.connectors)):
                if self.connectors[idx - removed].stopped:
                    log.debug(f"Removing stopped connector: {idx - removed} | {self.connectors[idx - removed]}")
                    self.connectors.pop(idx - removed)
                    removed += 1

            # Push all outgoing to connectors
            for connector in self.connectors:
                for msg in self.outgoing:
                    connector.outgoing.append(msg)
            self.outgoing.clear()

            # Fetch all incoming to node
            for connector in self.connectors:
                for msg in connector.incoming:
                    self.incoming.append(msg)
                connector.incoming.clear()

        # NOTE: Clears might cause race conditions

    def send(self, channel: bytes, msg: T.Any) -> None:
        self.outgoing.append((channel, PyO.load(msg)))

    def recv(self, timeout: T.Optional[float] = None) -> T.Tuple[bytes, T.Any]:
        time_start = time.monotonic()

        def timed_out() -> bool:
            if timeout is not None:
                return (time.monotonic() - time_start) > timeout
            else:
                return False

        while not timed_out():
            if len(self.incoming) != 0:
                channel, msg_datum = self.incoming.pop(0)
                return channel, PyO.dump(msg_datum)  # NOTE: Potentially strips data from datum if re-broadcasted

        raise TimeoutError
