from cent.call import CallServer

CURRENT = 0


def reset():
    global CURRENT

    CURRENT = 0


def validate(x: int):
    global CURRENT

    res = CURRENT == x
    CURRENT += 1

    return res, x, CURRENT - 1


if __name__ == "__main__":
    call = CallServer("_", "wss://do.1222001.xyz:10000", b"\x00" * 16)
    # call = CallServer("_", "ws://0.0.0.0:10000", b"\x00" * 16)
    call.register("reset", reset)
    call.register("validate", validate)
    call.start()
