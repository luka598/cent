import atexit
import logging as py_logging
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


class ANSICode:
    RESET = "\033[0m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BG_RED = "\033[41m"


class Printer:
    def start(self) -> None:
        raise NotImplementedError()

    def stop(self) -> None:
        raise NotImplementedError()

    def add_log(self, *args: T.Any, meta: T.Dict[str, T.Any], log_level: LOG_LEVEL_t) -> None:
        raise NotImplementedError()

    def _log(self, *args: T.Any, meta: T.Dict[str, T.Any], log_level: LOG_LEVEL_t) -> None:
        log_level = interpret_log_level(log_level)

        # Filters

        if log_level < LOG_LEVEL:
            return

        if "name" in meta:
            name = meta["name"]

        if "thread_name" in meta:
            thread_marker = meta["thread_name"]
        else:
            thread_marker = "?"

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

        if log_level < 10:
            color = ANSICode.MAGENTA
        elif log_level < 20:
            color = ANSICode.BLUE
        elif log_level < 30:
            color = ANSICode.GREEN
        elif log_level < 40:
            color = ANSICode.YELLOW
        elif log_level < 50:
            color = ANSICode.RED
        else:
            color = ANSICode.BG_RED

        output = "%s[%s][%s@%s]:%s %s" % (
            color,
            log_level,
            name,
            thread_marker,
            ANSICode.RESET,
            " ".join([str(item) for item in args]),
        )
        print(output, flush=True)


class ClassicPrinter(Printer):
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def add_log(self, *args: T.Any, meta: T.Dict[str, T.Any], log_level: LOG_LEVEL_t) -> None:
        self._log(*args, meta=meta, log_level=log_level)


class ThreadedPrinter(Printer):
    def __init__(self) -> None:
        self.deque = deque()
        self.wait_time = 0.10
        self.stop_event = threading.Event()
        self.main_thread_ref = weakref.ref(threading.main_thread())
        self.thread = threading.Thread(name="Printer", target=self.worker, daemon=False)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def add_log(self, *args: T.Any, meta: T.Dict[str, T.Any], log_level: LOG_LEVEL_t) -> None:
        if self.stop_event.is_set():
            raise RuntimeError("Printer stopped")
        self.deque.append((args, meta, log_level))

    @property
    def _stop_condtion(self) -> bool:
        return (
            self.stop_event.is_set() or not (self.main_thread_ref() and self.main_thread_ref().is_alive())  # type: ignore
        ) and len(self.deque) == 0

    def worker(self) -> None:
        while not self._stop_condtion:
            try:
                args, meta, log_level = self.deque.popleft()
                self._log(*args, meta=meta, log_level=log_level)
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

    def release_printer(self) -> None:
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

    def log(self, *args: T.Any, log_level: LOG_LEVEL_t = "NOTSET") -> None:
        if interpret_log_level(log_level) < LOG_LEVEL:  # NOTE: Pre-filter
            return

        self.printer.add_log(
            *args,
            meta={
                "name": self.name,
                "thread_name": threading.current_thread().name,
            },
            log_level=log_level,
        )

    def debug(self, *args: T.Any) -> None:
        return self.log(*args, log_level="DEBUG")

    def info(self, *args: T.Any) -> None:
        return self.log(*args, log_level="INFO")

    def warning(self, *args: T.Any) -> None:
        return self.log(*args, log_level="WARNING")

    def error(self, *args: T.Any) -> None:
        return self.log(*args, log_level="ERROR")

    def critical(self, *args: T.Any) -> None:
        return self.log(*args, log_level="CRITICAL")


# ---


class CustomHandler(py_logging.Handler):
    def __init__(self, level: int = py_logging.NOTSET):
        super().__init__(level)
        self.printer = PRINTER_MANAGER.capture_printer()

    def emit(self, record: py_logging.LogRecord) -> None:
        log_entry = self.format(record)

        self.printer.add_log(log_entry, meta={"name": record.name}, log_level=record.levelno)


root_py_logger = py_logging.getLogger()
root_py_logger.addHandler(CustomHandler())
