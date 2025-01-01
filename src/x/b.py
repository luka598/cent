import time

from cent.call import CallClient
from cent.logging import Logger

log = Logger(__name__)

if __name__ == "__main__":
    call = CallClient("wss://do.1222001.xyz:10000", b"\x00" * 16)
    # call = CallClient("ws://0.0.0.0:10000", b"\x00" * 16)
    call.call("_", "reset", {})
    for i in range(1000):
        call.call("_", "validate", {"x": i}, buffer=True)
        if i % 10 == 0:
            log.info(round(time.time(), 3), i, call.exec().all())
    call.exec().all()
