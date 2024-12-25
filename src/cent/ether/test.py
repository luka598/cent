import time

from cent.ether.connectors.dumb import DumbConnector as Connector
from cent.ether.main import Node

if __name__ == "__main__":
    con_1 = Connector(None)
    con_2 = Connector(None)
    con_1.other = con_2
    con_2.other = con_1

    n_1 = Node()
    n_1.add_connector(con_1)

    n_2 = Node()
    n_2.add_connector(con_2)

    n_1.send("Hello from node 1")
    n_2.send("Hello from node 2")

    for _ in range(5):
        time.sleep(1)
        print(f"{n_1.incoming=} {n_1.outgoing=} |===| {con_1.incoming=} {con_1.outgoing=}")
        print(f"{n_2.incoming=} {n_2.outgoing=} |===| {con_2.incoming=} {con_2.outgoing=}")
        print("=== TICK ===")
        n_1.tick()
        n_2.tick()

    print(n_1.recv())
    print(n_2.recv())

    con_1.stop()
    con_2.stop()
