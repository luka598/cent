import time
import typing as T

from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK
from websockets.sync.client import connect

from cent.data import DataException
from cent.data.t import JSONx, PyO
from cent.logging import Logger

log = Logger(__name__)


class Client:
    class Exception(Exception):
        pass

    def __init__(self, server_uri: str, channel: bytes) -> None:
        self.server_uri = server_uri
        self.channel = channel

        self.ws: T.Any = None

    def start(self) -> None:
        self.ws = connect(self.server_uri)
        self.ws.send(self.channel.hex())

    def send(self, msg: T.Dict) -> None:
        if self.ws is None:
            self.start()

        try:
            self.ws.send(JSONx.dump(PyO.load(msg)))
            return
        except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError):
            log.warning("Connection closed.")
            self.ws = None

    def recv(self, timeout: T.Optional[float] = None) -> T.Dict:
        if self.ws is None:
            self.start()

        time_start = time.monotonic()

        def timed_out() -> bool:
            if timeout is not None:
                return (time.monotonic() - time_start) > timeout
            else:
                return False

        while not timed_out():
            if not self.ws:
                self.start()

            try:
                msg_data = self.ws.recv(timeout=None if timeout is None else timeout / 10)
            except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError):
                log.warning("Connection closed.")
                self.ws = None
                continue

            try:
                return PyO.dump(JSONx.load(msg_data))
            except DataException as e:
                log.warning(f"Failed to decode msg: {str(e)}")
                continue

        raise TimeoutError()
