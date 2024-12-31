import time

from cent.rhythm.unit import Milis, Seconds


class Timeout:
    def __init__(self, timeout: Milis, raise_exception: bool = False) -> None:
        self.timeout: Seconds = timeout / 1000
        self.raise_exception = raise_exception
        self.start_time = time.monotonic()

    def __bool__(self):
        if (time.monotonic() - self.start_time) > self.timeout:
            return None

        if self.raise_exception:
            raise TimeoutError()
        else:
            return True
