import time

from cent.ether.main import Node

if __name__ == "__main__":
    node = Node()
    node.start()

    while True:
        time.sleep(1)
