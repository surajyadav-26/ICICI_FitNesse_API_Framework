import html
from websocket import create_connection
from core.logger import logger

class WebSocketFixture:
    """
    FitNesse SLIM Decision Table fixture for testing WebSockets APIs.
    Allows opening persistent connections, sending, and receiving text messages.
    """
    def __init__(self) -> None:
        self._url: str = ""
        self._ws = None
        self._last_received: str = ""
        self._timeout_seconds: float = 5.0

    def set_url(self, url: str) -> None:
        self._url = html.unescape(url).strip()

    def setUrl(self, url: str) -> None:
        self.set_url(url)

    def set_timeout(self, seconds: float) -> None:
        self._timeout_seconds = float(seconds)

    def setTimeout(self, seconds: float) -> None:
        self.set_timeout(seconds)

    def connect(self) -> bool:
        try:
            logger.info(f"[WebSocket] Connecting to {self._url} (timeout={self._timeout_seconds}s)")
            self._ws = create_connection(self._url, timeout=self._timeout_seconds)
            logger.info("[WebSocket] Connection established successfully.")
            return True
        except Exception as e:
            logger.error(f"[WebSocket] Connection failed: {e}")
            self._ws = None
            return False

    def send_message(self, message: str) -> bool:
        if self._ws is None:
            logger.error("[WebSocket] Cannot send message: Not connected.")
            return False
        try:
            payload = html.unescape(message)
            logger.info(f"[WebSocket] Sending: {payload}")
            self._ws.send(payload)
            return True
        except Exception as e:
            logger.error(f"[WebSocket] Failed to send message: {e}")
            return False

    def sendMessage(self, message: str) -> bool:
        return self.send_message(message)

    def receive_message(self) -> str:
        if self._ws is None:
            logger.error("[WebSocket] Cannot receive: Not connected.")
            return "not connected"
        try:
            logger.info("[WebSocket] Waiting for message...")
            result = self._ws.recv()
            self._last_received = str(result)
            logger.info(f"[WebSocket] Received: {self._last_received}")
            return self._last_received
        except Exception as e:
            logger.error(f"[WebSocket] Failed to receive message: {e}")
            return "error: " + str(e)

    def receiveMessage(self) -> str:
        return self.receive_message()

    def last_received(self) -> str:
        return self._last_received

    def lastReceived(self) -> str:
        return self.last_received()

    def close(self) -> bool:
        if self._ws is not None:
            try:
                self._ws.close()
                logger.info("[WebSocket] Connection closed.")
            except Exception:
                pass
            self._ws = None
        return True
