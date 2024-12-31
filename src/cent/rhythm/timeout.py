import time

from cent.rhythm.unit import Seconds


class Timeout:
    def __init__(self, timeout: Seconds, raise_exception: bool = False) -> None:
        self.timeout = timeout
        self.raise_exception = raise_exception
        self.start_time: Seconds = time.monotonic()

    def __bool__(self) -> bool:
        if (time.monotonic() - self.start_time) > self.timeout:
            return False

        if self.raise_exception:
            raise TimeoutError()
        else:
            return True
