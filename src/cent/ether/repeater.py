import os

from cent.ether.connectors.ws_jsonx import ServerConnector
from cent.ether.main import Node

if __name__ == "__main__":
    node = Node()
    con = ServerConnector(node, "0.0.0.0", 10_000, os.getenv("ETHER_SSL_CERT"), os.getenv("ETHER_SSL_KEY"))
    node.add_connector(con)
    node.start()

    while True:
        try:
            msg = node.recv(1)
            node.send(*msg)
        except TimeoutError:
            pass
