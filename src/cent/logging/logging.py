import atexit
import os
import threading
import time
import typing as T
import weakref
from collections import deque

LOG_LEVEL_t = T.Union[
    T.Literal[
        "NOTSET",
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ],
    int,
    str,
]


def interpret_log_level(log_level: T.Any) -> int:
    if isinstance(log_level, int):
        return log_level
    elif isinstance(log_level, str):
        if log_level == "NOTSET":
            return 0
        elif log_level == "DEBUG":
            return 10
        elif log_level == "INFO":
            return 20
        elif log_level == "WARNING":
            return 30
        elif log_level == "ERROR":
            return 40
        elif log_level == "CRITICAL":
            return 50
        else:
            try:
                return int(log_level)
            except ValueError:
                return 0
    else:
        return 0


LOG_LEVEL = interpret_log_level(os.getenv("LOG_LEVEL") or "INFO")
LOG_IGNORE = os.getenv("LOG_IGNORE")
LOG_FOCUS = os.getenv("LOG_FOCUS")
LOG_THREADED = bool(os.getenv("LOG_THREADED") or True)


class Printer:
    def start(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def add_log(self, *args, **kwargs):
        raise NotImplementedError()

    def log(self, *args, name: str = "", log_level: LOG_LEVEL_t, **kwargs):
        log_level = interpret_log_level(log_level)

        # Filters

        if log_level < LOG_LEVEL:
            return

        if LOG_IGNORE:
            for ignore in LOG_IGNORE.split(","):
                if ignore[-1] == "*" and name.startswith(ignore[:-1]):
                    return
                elif ignore == name:
                    return

        if LOG_FOCUS:
            for focus in LOG_FOCUS.split(","):
                if focus[-1] == "*" and not name.startswith(ignore[:-1]):
                    return
                elif focus != name:
                    return

        output = "[%s][%s]: %s" % (
            name,
            log_level,
            " ".join([str(item) for item in args]),
        )
        print(output, flush=True)


class ClassicPrinter(Printer):
    def start(self):
        pass

    def stop(self):
        pass

    def add_log(self, *args, **kwargs):
        self.log(*args, **kwargs)


class ThreadedPrinter(Printer):
    def __init__(self) -> None:
        self.deque = deque()
        self.wait_time = 0.10
        self.stop_event = threading.Event()
        self.main_thread_ref = weakref.ref(threading.main_thread())
        self.thread = threading.Thread(name="Printer", target=self.worker, daemon=False)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def add_log(self, *args, **kwargs):
        if self.stop_event.is_set():
            raise RuntimeError("Printer stopped")
        self.deque.append((args, kwargs))

    @property
    def _stop_condtion(self):
        return (
            self.stop_event.is_set()
            or not (self.main_thread_ref() and self.main_thread_ref().is_alive())  # type: ignore
        ) and len(self.deque) == 0

    def worker(self):
        while not self._stop_condtion:
            try:
                args, kwargs = self.deque.popleft()
                self.log(*args, **kwargs)
            except IndexError:
                time.sleep(self.wait_time)


class PrinterManager:
    def __init__(self) -> None:
        self.ref_count = 0
        self.printer: T.Optional[Printer] = None

    def capture_printer(self) -> Printer:
        if self.ref_count == 0:
            if LOG_THREADED:
                self.printer = ThreadedPrinter()
            else:
                self.printer = ClassicPrinter()
            self.printer.start()
        self.ref_count += 1
        return self.printer  # type: ignore

    def release_printer(self):
        self.ref_count -= 1
        if self.ref_count == 0:
            self.printer.stop()  # type: ignore
            del self.printer
        elif self.ref_count < 0:
            raise RuntimeError("Ref count less than 0")


PRINTER_MANAGER = PrinterManager()


class Logger:
    def __init__(self, name: str) -> None:
        self.name = name
        self.printer = PRINTER_MANAGER.capture_printer()
        atexit.register(lambda: PRINTER_MANAGER.release_printer())

    def log(self, *args, log_level: LOG_LEVEL_t = "NOTSET"):
        if interpret_log_level(log_level) < LOG_LEVEL:  # NOTE: Pre-filter
            return

        self.printer.add_log(*args, name=self.name, log_level=log_level)

    def debug(self, *args):
        return self.log(*args, log_level="DEBUG")

    def info(self, *args):
        return self.log(*args, log_level="INFO")

    def warning(self, *args):
        return self.log(*args, log_level="WARNING")

    def error(self, *args):
        return self.log(*args, log_level="ERROR")

    def critical(self, *args):
        return self.log(*args, log_level="CRITICAL")
