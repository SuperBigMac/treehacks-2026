"""
Composes camera and inference; runs the capture–detect–display loop.
Camera and inference are separate APIs; this class only orchestrates them.
"""

import cv2
import time

from cv.camera import Camera
from cv.inference import FaceDetectorInference

DEFAULT_FRAME_DELTA_MS = 33  # ~30 fps


class FaceCameraPipeline:
    """
    Runs a loop: read frame from camera → run face detection → draw boxes and show.
    Does not own camera or inference lifecycle; use as context manager with
    pre-constructed Camera and FaceDetectorInference, or use the class method
    that creates them.
    """

    def __init__(
        self,
        camera: Camera,
        detector: FaceDetectorInference,
        frame_delta_ms: int = DEFAULT_FRAME_DELTA_MS,
        window_name: str = "Video Feed",
        show_window: bool = True,
    ):
        self._camera = camera
        self._detector = detector
        self._frame_delta_ms = frame_delta_ms
        self._window_name = window_name
        self._show_window = show_window
        
    def run_pipeline(self, quit_key: str = "q") -> None:
        while True:
            ret, frame = self._camera.read()
            if not ret:
                break
            faces = self._detector.detect(frame)
            if faces:
                print(f"Found {len(faces)} faces")
            if self._show_window:
                cv2.imshow(self._window_name, frame)
                if cv2.waitKey(self._frame_delta_ms) == ord(quit_key):
                    break
            time.sleep(self._frame_delta_ms / 1000)