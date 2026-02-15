"""
Mock hardware API: same interface as api.HardwareAPI but no serial.
Prints when messages are sent and when rate limiting kicks in.
"""

import time

from hardware.api import DEFAULT_RATE_LIMIT_MS, HardwareDisconnectedError


class MockHardwareAPI:
    """
    Drop-in mock for HardwareAPI. No serial port; prints send/rate-limit activity.
    """
    def __init__(self, port: str = "mock", baudrate: int = 9600, rate_limit_ms: int = DEFAULT_RATE_LIMIT_MS):
        self.port = port
        self.baudrate = baudrate
        self._rate_limit_ms = rate_limit_ms
        self._connected = True
        self.last_message = time.time()

    def send_message(self, message: str, verbose: bool = False, rate_limit: bool = True) -> None:
        """Send a message (mock: just print). Prints when rate limited."""
        if rate_limit and (time.time() - self.last_message) < (self._rate_limit_ms / 1000):
            print("[mock hardware] Rate limited.")
            return
        print(f"[mock hardware] Sent: {message!r}")
        if rate_limit:
            self.last_message = time.time()

    def send_heartbeat(self) -> None:
        """Send heartbeat (mock: just print)."""
        print("[mock hardware] Heartbeat sent.")

    def close(self) -> None:
        """No-op for mock."""
        self._connected = False
        print("[mock hardware] Close (no-op).")
