import time
import typing as T
from uuid import uuid4

from cent.ether.impl.simple import SimpleRoot
from cent.ether.impl.ws_jsonx import ClientCom
from cent.logging import Logger
from cent.rhythm.timeout import Timeout

log = Logger(__name__)


class BoundSet:
    def __init__(self, ttl: int, max_size: int) -> None:
        self.ttl = ttl
        self.max_size = max_size
        self.cache = {}
        self.n = 0

    def check(self, key: bytes) -> bool:
        if key not in self.cache:
            self.cache[key] = time.monotonic()
            self.n += 1
            if self.n > self.max_size:
                self.clean()
            return False
        else:
            self.cache[key] = time.monotonic()
            return True

    def clean(self) -> None:
        keys = []
        for key, value in self.cache.items():
            if time.monotonic() - value > self.ttl:
                keys.append(key)
        for key in keys:
            del self.cache[key]
            self.n -= 1


class CallServer:
    def __init__(self, service: str, server_uri: str, channel: bytes) -> None:
        self.service = service
        self.funcs = {}

        self.channel = channel
        self.root = SimpleRoot()
        self.com = ClientCom(self.root, server_uri, channel)

        self.root.add_com(self.com)
        self.com.start()
        self.root.start()

    def register(self, name: str, f: T.Callable) -> None:
        self.funcs[name] = f
        log.debug(f"Registered {name} for {self.service}")

    def start(self) -> None:  # noqa: C901
        msg_ids = BoundSet(ttl=60 * 5, max_size=10_00)
        log.debug(f"Started call server for {self.service}")
        while True:
            _, msg = self.root.recv()
            try:
                msg_id = msg["msg_id"]
                service = msg["service"]
                no_ret = msg["no_ret"]
                calls = msg["calls"]

                assert isinstance(msg_id, bytes), "Got invalid call_id; not bytes"
                assert len(msg_id) == 16, "Got invalid call_id; invalid length"
                assert not msg_ids.check(msg_id), "Got invalid call_id; duplicate"

                assert isinstance(service, str), "Got invalid service name; not str"
                assert service == self.service, "Got invalid service name; mismatch"

                assert isinstance(no_ret, bool), "Got invalid no_ret; not bool"

                assert isinstance(calls, list), ""

                rets = []
                for call in calls:
                    func, args = call

                    assert isinstance(func, str), "Got invalid func name; not str"
                    assert func in self.funcs, "Got invalid func name; not registered"
                    assert isinstance(args, dict), "Got invalid args; not dict"

                    try:
                        ret = self.funcs[func](**args)
                        success = True
                    except Exception as e:
                        ret = (e.__class__.__name__, str(e))
                        success = False

                    if not isinstance(ret, tuple):
                        ret = (ret,)

                    if not no_ret:
                        rets.append([success, list(ret)])

            except (AssertionError, KeyError, ValueError) as e:
                continue

            if no_ret:
                continue

            self.root.send(
                self.channel,
                {
                    "msg_id": msg_id,
                    "rets": rets,
                },
            )


class CallClient:
    class Exception(Exception):
        pass

    class Ret:
        def __init__(self, rets: T.Optional[T.List] = None) -> None:
            if rets:
                self.rets = rets
            else:
                self.rets = []

        def capture(self) -> T.Tuple:
            if len(self.rets) == 0:
                raise RuntimeError("No rets")

            success, value = self.rets.pop(0)
            if success:
                return tuple(value)
            else:
                raise CallClient.Exception(f"{value[0]} - {value[1]}")

        def all(self) -> T.List[T.Tuple]:
            rets = []
            while len(self.rets) > 0:
                rets.append(self.capture())
            return rets

    def __init__(self, server_uri: str, channel: bytes) -> None:
        self.channel = channel
        self.root = SimpleRoot()
        self.com = ClientCom(self.root, server_uri, channel)

        self.root.add_com(self.com)
        self.com.start()
        self.root.start()

        self.buffered_msg = None

    def __del__(self) -> None:
        self.root.stop()

    def call(self, service: str, func: str, args: T.Dict, no_ret: bool = False, buffer: bool = False) -> "CallClient.Ret":
        msg_id = uuid4().bytes
        if self.buffered_msg is None:
            self.buffered_msg = {"msg_id": msg_id, "service": service, "no_ret": no_ret, "calls": []}
        else:
            self.buffered_msg["msg_id"] = msg_id
            self.buffered_msg["service"] = service
            self.buffered_msg["no_ret"] = no_ret

        self.buffered_msg["calls"].append([func, args])

        if buffer:
            return CallClient.Ret()
        else:
            return self.exec()

    def exec(self) -> "CallClient.Ret":
        msg = self.buffered_msg
        self.buffered_msg = None
        while True:
            if msg is None:
                return CallClient.Ret()

            self.root.send(self.channel, msg)

            if msg["no_ret"]:
                return CallClient.Ret([(True, ())] * len(msg["calls"]))

            timeout = Timeout(5)
            while not timeout:
                try:
                    _, ret_msg = self.root.recv(timeout=1)

                    msg_id = ret_msg["msg_id"]
                    rets = ret_msg["rets"]

                    assert isinstance(msg_id, bytes), "Invalid msg_id; not bytes"
                    assert msg["msg_id"] == msg_id, "Invalid msg_id; mismatch"

                    assert isinstance(rets, list), "Invalid ret; not list"

                    return CallClient.Ret(rets)

                except (KeyError, AssertionError):
                    log.debug("Invalid msg")
                except TimeoutError:
                    log.warning("Failed to receive message; timed out")
