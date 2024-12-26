import os

from cent.ether.impl.root import Root
from cent.ether.impl.ws_jsonx import ServerCom

if __name__ == "__main__":
    root = Root()
    com = ServerCom(root, "0.0.0.0", 10_000, os.getenv("ETHER_SSL_CERT"), os.getenv("ETHER_SSL_KEY"))
    root.add_com(com)
    com.start()
    root.start()

    while True:
        try:
            msg = root.recv(1)
            root.send(*msg)
        except TimeoutError:
            pass
