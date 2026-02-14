"""
API to interface with the hardware.
"""

import time

import serial

class HardwareAPI:
    """
    API to interface with the hardware. Handles serial errors (e.g. device
    disconnected) internally; send_message returns False on failure and stops
    attempting writes until the connection is fixed.
    """
    def __init__(self, port: str, baudrate: int, rate_limit_ms: int = 100):
        self.port = port
        self.baudrate = baudrate
        self.ser = serial.Serial(port=self.port, baudrate=self.baudrate)
        self.last_message = time.time()
        self._rate_limit_ms = rate_limit_ms
        self._connected = True
        print("Initialized serial connection. Waiting for arduino to be configured")
        time.sleep(2)
        print("Arduino setup (probably) complete")

    def send_message(self, message: str, verbose: bool = False) -> bool:
        """
        Send a message to the hardware. Returns True if sent, False if the
        device is disconnected or write failed (errors are logged once).
        """
        if not self._connected:
            return False
        if verbose:
            print(f"Sending message: {message}")
        if (time.time() - self.last_message) < self._rate_limit_ms / 1000:
            if verbose:
                print("Rate limited.")
            return True
        try:
            self.ser.write(message.encode("utf-8"))
            self.last_message = time.time()
            return True
        except (serial.SerialException, OSError) as e:
            print(f"Serial error (device disconnected?): {e}")
            self._connected = False
            return False

    def close(self) -> None:
        """Close the serial connection. Safe to call if already disconnected."""
        try:
            self.ser.close()
        except Exception:
            pass