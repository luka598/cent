import time

from cent.ether.impl.simple import SimpleRoot

if __name__ == "__main__":
    node = SimpleRoot()
    node.start()

    while True:
        time.sleep(1)
