"""
API to interface with the hardware.
"""

import serial

class HardwareAPI:
    """
    API to interface with the hardware.
    """
    def __init__(self, port: str, baudrate: int):
        self.port = port
        self.baudrate = baudrate
        self.ser = serial.Serial(port=self.port, baudrate=self.baudrate)
    
    def send_message(self, message: str, verbose: bool = False):
        """
        Send a message to the hardware.
        """
        if verbose:
            print(f"Sending message: {message}")
        self.ser.write(message.encode("utf-8"))
    
    def close(self):
        """
        Close the serial connection.
        """
        self.ser.close()