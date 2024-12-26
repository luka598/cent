import ssl
import threading
import typing as T

from cent.data import DataException
from cent.data.t import JSONx
from cent.ether.impl.root import LOOP_TIME, Com, Root
from cent.logging import Logger
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK
from websockets.sync.client import connect
from websockets.sync.server import serve

log = Logger(__name__)


class ServerCom(Com):
    def __init__(
        self, parent: Root, addr: str, port: int, ssl_cert: T.Optional[str] = None, ssl_key: T.Optional[str] = None
    ) -> None:
        super().__init__(parent)

        if ssl_cert and ssl_key:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(
                certfile=ssl_cert,
                keyfile=ssl_key,
            )
        else:
            ssl_context = None

        log.info(f"Initiated ws_jsonx server | {'ws' if ssl_context is None else 'wss'}://{addr}:{port}")
        self.server = serve(self.handler, addr, port, ssl=ssl_context)

    def start(self) -> None:
        self.active = True
        log.info("Starting ws_jsonx server")
        self.thread_a = threading.Thread(target=self.loop)
        self.thread_b = threading.Thread(target=lambda: self.server.serve_forever())
        self.thread_a.start()
        self.thread_b.start()

    def handler(self, ws) -> None:
        handler = HandlerCom(self.parent, ws)
        self.parent.add_com(handler)
        handler.start()

    def loop(self) -> None:
        while self.active:
            try:
                event = self.events.get(timeout=LOOP_TIME)
            except TimeoutError:
                continue

            if event == "stop":
                self.active = False
                self.server.shutdown()
                self.parent.add_event("com_stopped")


class HandlerCom(Com):
    def __init__(self, parent: Root, ws) -> None:
        super().__init__(parent)
        self.ws = ws

    def start(self):
        self.active = True
        self.main()

    def main(self):
        self._init_con()

        while self.active:
            try:
                event = self.events.get(timeout=LOOP_TIME)
            except TimeoutError:
                event = None

            if event == "stop":
                self.active = False
                self.ws.close()
                self.parent.add_event("com_stopped")

            elif event == "new_outgoing":
                self._send()

            elif event is None:
                self._recv()

    def _init_con(self):
        try:
            ip, port = self.ws.socket.getpeername()
            log.info(f"CON: {ip}:{port}")
        except Exception:
            log.info("CON: unknown")

        try:
            channel_data = self.ws.recv()
        except TimeoutError:
            log.warning("DC: timed out")
            self.stop()
            return
        except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError) as e:
            log.warning(f"DC: Connection closed | {type(e).__name__} - {e}")
            self.stop()
            return

        if isinstance(channel_data, bytes):
            log.warning("ERR: Msg not string")
            self.stop()
            return

        try:
            self.channel = bytes.fromhex(channel_data)
        except ValueError:
            log.warning("ERR: Failed to decode channel")
            self.stop()
            return

        if len(self.channel) != 16:
            log.warning("ERR: Invalid channel length")
            self.stop()
            return

        log.info(f"AUTH: {self.channel.hex()}")

    def _send(self):
        try:
            channel, value = self.outgoing.get(0)
            if channel == self.channel:
                self.ws.send(JSONx.dump(value))
                log.info(f"MSG: > {self.channel.hex()}")
        except TimeoutError:
            log.warning("No messages")
        except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError) as e:
            log.warning(f"DC: {self.channel.hex()}")
            self.stop()

    def _recv(self):
        try:
            msg_data = self.ws.recv(LOOP_TIME)
            msg = JSONx.load(msg_data)
            self.incoming.put((self.channel, msg))
            self.parent.add_event("new_incoming")
            log.info(f"MSG: < {self.channel.hex()}")
        except TimeoutError:
            pass
        except DataException as exc:
            log.warning(f"INV_PKT: {self.channel.hex()} - {str(exc)}")
        except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError) as e:
            log.warning(f"DC: {self.channel.hex()}")
            self.stop()


class ClientCom(Com):
    def __init__(self, parent: Root, uri: str, channel: bytes) -> None:
        super().__init__(parent)
        self.uri = uri
        self.channel = channel

    def start(self):
        self.active = True
        log.info(f"Connecting to ws_jsonx server | {self.uri}")
        self.ws = connect(self.uri)
        self.ws.send(self.channel.hex())

        self.thread = threading.Thread(target=self.loop)
        self.thread.start()

    def loop(self):
        while self.active:
            try:
                event = self.events.get(timeout=LOOP_TIME)
            except TimeoutError:
                event = None

            if event == "stop":
                self.active = False
                self.ws.close()
                self.parent.add_event("com_stopped")

            elif event == "new_outgoing":
                self._send()

            elif event is None:
                self._recv()

    def _send(self):
        try:
            channel, value = self.outgoing.get(0)
            if channel == self.channel:
                self.ws.send(JSONx.dump(value))
                log.info(f"MSG: > {self.channel.hex()}")
        except TimeoutError:
            log.warning("No messages")
        except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError) as e:
            log.warning(f"DC: {self.channel.hex()}")
            self.stop()

    def _recv(self):
        try:
            msg_data = self.ws.recv(LOOP_TIME)
            msg = JSONx.load(msg_data)
            self.incoming.put((self.channel, msg))
            self.parent.add_event("new_incoming")
            log.info(f"MSG: < {self.channel.hex()}")
        except TimeoutError:
            pass
        except DataException as exc:
            log.warning(f"INV_PKT: {self.channel.hex()} - {str(exc)}")
        except (ConnectionClosed, ConnectionClosedOK, ConnectionClosedError) as e:
            log.warning(f"DC: {self.channel.hex()}")
            self.stop()
