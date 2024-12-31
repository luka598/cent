import time
import typing as T

from cent.rhythm.unit import Seconds, Timestamp
from cent.rhythm.util import floor_time


class MetronomeException(Exception):
    pass


class Timeout(MetronomeException):
    pass


class Metronome:
    period: Seconds
    skippable: bool
    strict: bool

    start_time: Seconds
    last_time: T.Union[Timestamp, None] = None
    ticks: int

    START_TOLERANCE: Seconds = 0.001

    def __init__(self, period: Seconds, skippable: bool = False, strict: bool = True) -> None:
        self.period = period
        self.skippable = skippable
        self.strict = strict

        self.reset()
        pass

    def _current_time(self) -> Seconds:
        return time.time()

    def reset(self, floor: bool = False) -> None:
        self.start_time: Seconds = self._current_time()
        if floor:
            self.start_time = floor_time(self.start_time, self.period)
        self.last_time = None
        self.ticks = 0

    def tick(self) -> bool:
        current_time = self._current_time()
        start_delta_m = (current_time - self.start_time) % self.period
        sleep_time = max(self.period - start_delta_m, 0)

        # print(
        #     f"SDM: {start_delta_m:.4f} | SD: {current_time - self.start_time:.4f} | ST: {sleep_time:.4f}"
        # )

        if self.last_time is None:
            if start_delta_m > self.START_TOLERANCE:
                # print("Sleeping", sleep_time)
                time.sleep(sleep_time)
        else:
            delta = current_time - self.last_time
            if delta > self.period:
                message = f"Timeout! Got {delta}, expected {self.period}"
                if self.strict:
                    raise Timeout(message)
                else:
                    print(message)

            if not self.skippable:
                time.sleep(sleep_time)

        self.last_time = self._current_time()
        self.ticks += 1
        return True

    @property
    def elapsed(self) -> Seconds:
        return self.ticks * self.period


if __name__ == "__main__":
    import subprocess

    def play_sound():
        subprocess.run(
            ["paplay", "/usr/share/sounds/freedesktop/stereo/message.oga"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    m = Metronome(1 / 2, skippable=False, strict=False)
    m.reset(floor=True)

    while m.tick():
        print(time.time())
        play_sound()
        print(m.ticks, m.elapsed)
