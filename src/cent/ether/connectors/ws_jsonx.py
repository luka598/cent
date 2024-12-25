import ssl
import threading
import typing as T

from cent.data import DataException
from cent.data.t import JSONx
from cent.ether.connectors.simple import ThreadedConnector
from cent.ether.main import Node
from cent.logging import Logger
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK
from websockets.sync.client import connect
from websockets.sync.server import serve

log = Logger(__name__)


class ServerConnector(ThreadedConnector):
    def __init__(
        self, node: Node, addr: str, port: int, ssl_cert: T.Optional[str] = None, ssl_key: T.Optional[str] = None
    ) -> None:
        super().__init__(min_loop_time=1)
        self.node = node

        if ssl_cert and ssl_key:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(
                certfile=ssl_cert,
                keyfile=ssl_key,
            )
        else:
            ssl_context = None

        self.server = serve(self.handler, addr, port, ssl=ssl_context)
        self.server_thread = threading.Thread(target=lambda: self.server.serve_forever())

        log.info(f"Initiated ws_jsonx server | {'ws' if ssl_context is None else 'wss'}://{addr}:{port}")

    def handler(self, ws) -> None:
        connector = HandlerConnector(ws)
        self.node.add_connector(connector)
        connector.stop_event.wait()

    def begin(self) -> None:
        log.info(f"Starting ws_jsonx server | {self.server}")
        self.server_thread.start()

    def tick(self) -> None:
        self.incoming.clear()
        self.outgoing.clear()

    def end(self) -> None:
        self.server.shutdown()
        self.server_thread.join()


class HandlerConnector(ThreadedConnector):
    def __init__(self, ws) -> None:
        super().__init__()
        self.INIT_TIMEOUT = None
        self.SEND_TIMEOUT = 0.01
        self.RECV_TIMEOUT = 0.01

        self.ws = ws

    def begin(self):
        try:
            ip, port = self.ws.socket.getpeername()
            log.info(f"CON: {ip}:{port}")
        except Exception:
            log.info("CON: unknown")

        try:
            channel_data = self.ws.recv()
        except TimeoutError:
            log.warning("DC: timed out")
            self.stopped = True
            return
        except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError) as e:
            log.warning(f"DC: Connection closed | {type(e).__name__} - {e}")
            self.stopped = True
            return

        if isinstance(channel_data, bytes):
            log.warning("ERR: Msg not string")
            self.stopped = True
            return

        try:
            self.channel = bytes.fromhex(channel_data)
        except ValueError:
            log.warning("ERR: Failed to decode channel")
            self.stopped = True
            return

        if len(self.channel) != 16:
            log.warning("ERR: Invalid channel length")
            self.stopped = True
            return

        log.info(f"AUTH: {self.channel.hex()}")

    def tick(self):
        try:
            msg_data = self.ws.recv(self.RECV_TIMEOUT)
            msg = JSONx.load(msg_data)
            self.incoming.append((self.channel, msg))
            log.info(f"MSG: < {self.channel.hex()}")
        except TimeoutError:
            pass
        except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError) as e:
            log.warning(f"DC: {self.channel.hex()}")
            self.stopped = True
        except DataException as exc:
            log.warning(f"INV_PKT: {self.channel.hex()} - {str(exc)}")

        try:
            if len(self.outgoing) != 0:
                channel, msg = self.outgoing.pop(0)
                if channel == self.channel:
                    self.ws.send(JSONx.dump(msg))
                    log.info(f"MSG: > {self.channel.hex()}")
        except TimeoutError:
            pass
        except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError) as e:
            log.warning(f"DC: {self.channel.hex()}")
            self.stopped = True

    def end(self):
        pass


class ClientConnector(ThreadedConnector):
    def __init__(self, uri: str, channel: bytes) -> None:
        super().__init__(min_loop_time=0.01)
        self.RECV_TIMEOUT = 0.01

        self.uri = uri
        self.channel = channel

    def begin(self) -> None:
        log.info(f"Connecting to ws_jsonx server | {self.uri}")
        self.ws = connect(self.uri)
        self.ws.send(self.channel.hex())

    def tick(self) -> None:
        try:
            msg_data = self.ws.recv(self.RECV_TIMEOUT)
            log.info(f"MSG: < {self.channel.hex()}")
            msg = JSONx.load(msg_data)
            self.incoming.append((self.channel, msg))
        except TimeoutError:
            pass
        except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError) as e:
            log.warning(f"DC: {self.channel.hex()}")
            self.stopped = True
        except DataException as exc:
            log.warning(f"INV_PKT: {self.channel.hex()} - {str(exc)}")

        try:
            if len(self.outgoing) != 0:
                channel, msg = self.outgoing.pop(0)
                if channel == self.channel:
                    log.info(f"MSG: > {self.channel.hex()}")
                    self.ws.send(JSONx.dump(msg))
        except TimeoutError:
            pass
        except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError) as e:
            log.warning(f"DC: {self.channel.hex()}")
            self.stopped = True

    def end(self) -> None:
        pass
