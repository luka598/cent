def str_to_channel(x: str) -> bytes:
    return x.encode("utf-8")[:16].ljust(16, b"\x00")
