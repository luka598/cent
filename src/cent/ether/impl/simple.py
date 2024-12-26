import typing as T

from cent.data.t import PyO
from cent.ether.impl.root import Root


class SimpleRoot(Root):
    def send(self, channel: bytes, value: T.Dict) -> None:
        return super().send(channel, PyO.load(value))

    def recv(self, timeout: T.Optional[float] = None) -> T.Tuple[bytes, T.Dict]:
        return PyO.dump(super().recv(timeout))
