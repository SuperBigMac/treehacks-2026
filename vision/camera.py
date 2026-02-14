"""
Camera capture API. No inference or display logic.
"""

import time
from typing import Tuple

import cv2
import numpy as np

DEFAULT_READ_RETRIES = 5
DEFAULT_RETRY_DELAY_SEC = 0.05
DEFAULT_RECONNECT_DELAY_SEC = 0.5


class Camera:
    """
    Camera capture with retries and reconnection. Use as context manager.
    """

    def __init__(
        self,
        camera_index: int = 0,
        read_retries: int = DEFAULT_READ_RETRIES,
        retry_delay_sec: float = DEFAULT_RETRY_DELAY_SEC,
        reconnect_delay_sec: float = DEFAULT_RECONNECT_DELAY_SEC,
    ):
        self._index = camera_index
        self._read_retries = read_retries
        self._retry_delay_sec = retry_delay_sec
        self._reconnect_delay_sec = reconnect_delay_sec
        self._cap = self._open()
        if not self._cap.isOpened():
            raise RuntimeError(
                f"Could not open camera (index={camera_index}). "
                "In use, no permission, or wrong index?"
            )

    def _open(self) -> cv2.VideoCapture:
        cap = cv2.VideoCapture(self._index)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def read(self) -> Tuple[bool, np.ndarray | None]:
        """
        Read one frame. Retries on failure, then tries one reconnect.

        Returns:
            (True, frame) on success, (False, None) if still no frame after retries and reconnect.
        """
        ret, frame = self._cap.read()
        if ret:
            return True, frame
        for _ in range(self._read_retries):
            time.sleep(self._retry_delay_sec)
            ret, frame = self._cap.read()
            if ret:
                return True, frame
        # Reconnect once
        self._cap.release()
        time.sleep(self._reconnect_delay_sec)
        self._cap = self._open()
        if not self._cap.isOpened():
            return False, None
        ret, frame = self._cap.read()
        return ret, frame if ret else None

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self) -> "Camera":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
