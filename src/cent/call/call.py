import time
import typing as T
from uuid import uuid4

from cent.ether import EtherException
from cent.ether.ws_jsonx import Client
from cent.logging import Logger

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
        for key, value in self.cache.items():
            if time.monotonic() - value > self.ttl:
                del self.cache[key]
                self.n -= 1


class CallServer:
    def __init__(self, service: str, server_uri: str, channel: bytes) -> None:
        self.service = service
        self.funcs = {}
        self.client = Client(server_uri, channel)

    def register(self, name: str, f: T.Callable) -> None:
        self.funcs[name] = f
        log.debug(f"Registered {name} for {self.service}")

    def start(self) -> None:  # noqa: C901
        call_ids = BoundSet(ttl=60 * 5, max_size=10_00)
        log.debug(f"Started call server for {self.service}")
        while True:
            msg = self.client.recv()

            # ---
            try:
                call_id = msg["call_id"]
                service = msg["service"]
                func = msg["func"]
                args = msg["args"]
                no_ret = msg["no_ret"]
            except KeyError:
                log.debug("Got invalid message")
                continue
            # ---
            if not isinstance(call_id, bytes):
                log.debug("Got invalid call_id; not bytes")
                continue
            if len(call_id) != 16:
                log.debug("Got invalid call_id; invalid length")
                continue
            if call_ids.check(call_id):
                log.debug("Got invalid call_id; duplicate")
                continue

            if not isinstance(service, str):
                log.debug("Got invalid service name; not str")
                continue
            if service != self.service:
                log.debug("Got invalid service name; mismatch")
                continue

            if not isinstance(func, str):
                log.debug("Got invalid func name; not str")
                continue
            if func not in self.funcs:
                log.debug("Got invalid func name; not registered")
                continue

            if not isinstance(args, dict):
                log.debug("Got invalid args; not dict")
                continue

            if not isinstance(no_ret, bool):
                log.debug("Got invalid no_ret; not bool")
                continue
            # ---
            try:
                log.debug(f"Got request for {func} with call_id {call_id}")
                ret = self.funcs[func](**args)
                if not isinstance(ret, tuple):
                    ret = (ret,)
                if no_ret:
                    continue
                self.client.send(
                    {
                        "call_id": call_id,
                        "success": True,
                        "ret": list(ret),
                    }
                )
                log.debug(f"Sent response for {func}")
            except Exception as e:
                log.debug(f"Failed to execute {func} - {e}")
                if no_ret:
                    continue
                self.client.send(
                    {
                        "call_id": call_id,
                        "success": False,
                        "ret": [e.__class__.__name__, str(e)],
                    }
                )
                log.debug(f"Sent error response for {func}")


class CallClient:
    class Exception(Exception):
        pass

    def __init__(self, server_uri: str, channel: bytes) -> None:
        self.client = Client(server_uri, channel)

    def call(self, service: str, func: str, args: T.Dict) -> T.Tuple:
        call_id = uuid4().bytes
        log.debug(f"Calling {func} with call_id {call_id}")
        self.client.send(
            {
                "call_id": call_id,
                "service": service,
                "func": func,
                "args": args,
                "no_ret": False,
            }
        )
        log.debug(f"Sent request for {func}")

        for _ in range(5):
            try:
                msg = self.client.recv()
            except EtherException as e:
                log.error(f"Failed to receive message: {type(e)} - {e}")
            # ---
            try:
                ret_call_id = msg["call_id"]
                success = msg["success"]
                ret = msg["ret"]
            except KeyError:
                log.debug("Got invalid message")
                continue
            # ---
            if not isinstance(call_id, bytes):
                log.debug("Got invalid call_id; not bytes")
                continue
            if call_id != ret_call_id:
                log.debug("Got invalid call_id; mismatch")
                continue

            if not isinstance(success, bool):
                log.debug("Got invalid success; not bool")
                continue

            if not isinstance(ret, list):
                log.debug("Got invalid ret; not list")
                continue
            ret = tuple(ret)
            # ---
            log.debug(f"Got response for {func} - {success}")
            if success:
                return ret
            else:
                raise CallClient.Exception(f"{ret[0]} - {ret[1]}")

        log.warning(f"Failed to get response for {func}, resending.")

        return self.call(service, func, args)

    def call_noret(self, service: str, func: str, args: T.Dict) -> None:
        call_id = uuid4().bytes
        log.debug(f"Calling {func} with call_id {call_id}; noret")
        self.client.send(
            {
                "call_id": call_id,
                "service": service,
                "func": func,
                "args": args,
                "no_ret": True,
            }
        )
        log.debug(f"Sent request for {func}; noret")
