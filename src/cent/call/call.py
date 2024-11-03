import typing as T
from uuid import uuid4

from cent.ether.ws_jsonx import Client


class CallServer:
    def __init__(self, service: str, server_uri: str, channel: bytes) -> None:
        self.service = service
        self.funcs = {}
        self.client = Client(server_uri, channel)

    def register(self, name: str, f: T.Callable) -> None:
        self.funcs[name] = f

    def start(self) -> None:  # noqa: C901
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
                continue
            # ---
            if not isinstance(call_id, bytes):
                continue
            if len(call_id) != 16:
                continue

            if not isinstance(service, str):
                continue
            if service != self.service:
                continue

            if not isinstance(func, str):
                continue
            if func not in self.funcs:
                continue

            if not isinstance(args, dict):
                continue

            if not isinstance(no_ret, bool):
                continue
            # ---
            try:
                ret = self.funcs[func](**args)
                if not isinstance(ret, tuple):
                    ret = (ret,)
                if no_ret:
                    continue
                self.client.send(
                    {
                        "call_id": call_id,
                        "success": True,
                        "ret": ret,
                    }
                )
            except Exception as e:
                if no_ret:
                    continue
                self.client.send(
                    {
                        "call_id": call_id,
                        "success": False,
                        "ret": [e.__class__.__name__, str(e)],
                    }
                )


class CallClient:
    class Exception(Exception):
        pass

    def __init__(self, server_uri: str, channel: bytes) -> None:
        self.client = Client(server_uri, channel)

    def call(self, service: str, func: str, args: T.Dict) -> T.Tuple:
        call_id = uuid4().bytes
        self.client.send(
            {
                "call_id": call_id,
                "service": service,
                "func": func,
                "args": args,
                "no_ret": False,
            }
        )

        while True:
            msg = self.client.recv()
            # ---
            try:
                ret_call_id = msg["call_id"]
                success = msg["success"]
                ret = msg["ret"]
            except KeyError:
                continue
            # ---
            if not isinstance(call_id, bytes):
                continue
            if call_id != ret_call_id:
                continue

            if not isinstance(success, bool):
                continue

            if not isinstance(ret, list):
                continue
            ret = tuple(ret)
            # ---
            if success:
                return ret
            else:
                raise CallClient.Exception(f"{ret[0]} - {ret[1]}")

    def call_noret(self, service: str, func: str, args: T.Dict) -> None:
        call_id = uuid4().bytes
        self.client.send(
            {
                "call_id": call_id,
                "service": service,
                "func": func,
                "args": args,
                "no_ret": True,
            }
        )
