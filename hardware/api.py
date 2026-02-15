"""
API to interface with the hardware.

Safe send rate (9600 baud, 1-byte messages): up to ~100–200/sec; Arduino RX buffer
is 64 bytes so avoid bursts over ~50. Use rate_limit_ms (default 100 → 10/sec) or
SAFE_RATE_LIMIT_MS (20 → 50/sec) to throttle.

Why disconnects happen: Opening/closing the serial port can toggle DTR on many
Arduinos, which triggers a hardware reset. We open with dsrdtr=False to avoid
resetting on connect; closing during reconnect can still reset the board.
"""

import time

import serial

# After closing the port, many Arduinos reset (DTR toggle). The device disappears
# for 1–2s, so we retry opening with delay. Minimum wait before trying reconnect again.
RECONNECT_RETRY_DELAY_SEC = 2.0
RECONNECT_MAX_ATTEMPTS = 5
RECONNECT_BACKOFF_SEC = 5.0

# Safe send rate at 9600 baud: ~960 bytes/sec theoretical; Arduino RX buffer is 64 bytes.
# Keep under ~100–200 one-byte messages/sec to be safe; bursts must stay under ~50 bytes.
DEFAULT_RATE_LIMIT_MS = 100  # 10/sec, very conservative

# Retry writes many times before reconnect — reconnect closes the port and resets the Arduino
WRITE_RETRIES = 10
WRITE_RETRY_DELAY_SEC = 0.2


class HardwareDisconnectedError(serial.SerialException):
    """Raised when the device disconnects. Reconnection was attempted; caller may retry."""


class HardwareAPI:
    """
    API to interface with the hardware. On write failure (e.g. device disconnected),
    attempts to reconnect and then raises HardwareDisconnectedError so the caller
    can handle or retry.
    """
    def __init__(self, port: str, baudrate: int, rate_limit_ms: int = DEFAULT_RATE_LIMIT_MS):
        self.port = port
        self.baudrate = baudrate
        self._rate_limit_ms = rate_limit_ms
        self._connected = False
        self.ser = None
        self.last_message = 0.0
        self._last_reconnect_attempt = 0.0
        self._reconnect()

    def _reconnect(self) -> None:
        """
        Close existing port (if any) and open a new serial connection.
        Closing the port can reset the Arduino (DTR), so we retry opening with
        delay until the device reappears.
        """
        try:
            if self.ser is not None:
                self.ser.close()
        except Exception:
            pass
        self.ser = None
        last_err = None
        for attempt in range(RECONNECT_MAX_ATTEMPTS):
            if attempt > 0:
                time.sleep(RECONNECT_RETRY_DELAY_SEC)
                print("Waiting for device to reappear...")
            try:
                self.ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    dsrdtr=False,
                )
                # Also clear DTR after open (macOS/Linux); reduces chance of Arduino reset
                try:
                    self.ser.dtr = False
                except Exception:
                    pass
                break
            except Exception as e:
                last_err = e
        else:
            err_str = str(last_err).lower()
            if "busy" in err_str or "errno 16" in err_str:
                raise serial.SerialException(
                    f"Port {self.port} is in use. Close Arduino Serial Monitor (or any other app using the port) and try again. Original: {last_err}"
                ) from last_err
            raise last_err
        self._connected = True
        self.last_message = time.time()
        self._last_reconnect_attempt = time.time()
        print("Serial reconnected. Waiting for arduino to be configured")
        time.sleep(2.5)
        print("Arduino setup (probably) complete")

    def send_message(self, message: str, verbose: bool = False, rate_limit: bool = True) -> None:
        """
        Send a message to the hardware. On failure (e.g. device disconnected),
        attempts reconnect and raises HardwareDisconnectedError. Caller can retry.
        """
        if not self._connected:
            now = time.time()
            if now - self._last_reconnect_attempt < RECONNECT_BACKOFF_SEC:
                raise HardwareDisconnectedError(
                    "Device disconnected; next reconnect in a few seconds."
                )
            try:
                print("Reconnecting...")
                self._reconnect()
            except Exception as e:
                self._last_reconnect_attempt = time.time()
                raise HardwareDisconnectedError(
                    f"Reconnect failed (device unplugged?): {e}"
                ) from e
        if verbose:
            print(f"Sending message: {message}")
        if rate_limit and (time.time() - self.last_message) < (self._rate_limit_ms / 1000):
            if verbose:
                print("Rate limited.")
            return

        data = message.encode("utf-8")
        last_err = None
        for attempt in range(WRITE_RETRIES):
            try:
                self.ser.write(data)
                if rate_limit:
                    self.last_message = time.time()
                if verbose:
                    print(f"Message {message} sent.")
                return
            except (serial.SerialException, OSError) as e:
                last_err = e
                if attempt < WRITE_RETRIES - 1:
                    time.sleep(WRITE_RETRY_DELAY_SEC)
        # All retries failed — only then reconnect (reconnect closes port and resets Arduino)
        self._connected = False
        try:
            self._reconnect()
            time.sleep(0.3)
            self.ser.write(data)
            # Don't update last_message here — this was a retry; let the next normal send from main not be rate-limited
        except (serial.SerialException, OSError):
            self._connected = False
            raise HardwareDisconnectedError(
                "Device disconnected; reconnected but write still failed. Retry later."
            ) from last_err
        except HardwareDisconnectedError:
            raise
        except Exception as reconnect_err:
            self._last_reconnect_attempt = time.time()
            raise HardwareDisconnectedError(
                f"Device disconnected; reconnect failed. Retry when reconnected: {reconnect_err}"
            ) from last_err

    def send_heartbeat(self) -> None:
        """
        Send a heartbeat message to the hardware.
        """
        self.send_message("3", verbose=False, rate_limit=False)

    def close(self) -> None:
        """Close the serial connection. Safe to call if already disconnected."""
        self._connected = False
        try:
            if self.ser is not None:
                self.ser.close()
                self.ser = None
        except Exception:
            pass
