import time

from cent.data.t import PyO
from cent.ether.connectors.ws_jsonx import ServerConnector
from cent.ether.main import Node

if __name__ == "__main__":
    n_1 = Node()
    con_1 = ServerConnector(n_1, "0.0.0.0", 10_000)
    n_1.add_connector(con_1)

    n_1.send(b"123", "Hello from node 1")

    while True:
        time.sleep(0.001)
        # print(f"{n_1.incoming=} {n_1.outgoing=} |===| {con_1.incoming=} {con_1.outgoing=}")
        # print("=== TICK ===")
        n_1.tick()

    print(n_1.recv())
