"""
Composes camera and inference; runs the capture–detect–display loop.
Camera and inference are separate APIs; this class only orchestrates them.
"""

import cv2
import time

from vision.camera import Camera
from vision.inference import FaceDetectorInference

DEFAULT_FRAME_FPS = 30


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
        frame_fps: int = DEFAULT_FRAME_FPS,
        window_name: str = "Video Feed",
        show_window: bool = True,
    ):
        self._camera = camera
        self._detector = detector
        self._frame_fps = frame_fps
        self._frame_delta_ms = int(1000 / frame_fps)
        self._window_name = window_name
        self._show_window = show_window
        
    def run_pipeline(self, quit_key: str = "q") -> None:
        timestamp_ms = 0
        while True:
            ret, frame = self._camera.read()
            if not ret or frame is None:
                break
            faces = self._detector.detect(frame, timestamp_ms)
            timestamp_ms += self._frame_delta_ms
            for (x1, y1, x2, y2) in faces:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            if self._show_window:
                cv2.imshow(self._window_name, frame)
                if cv2.waitKey(self._frame_delta_ms) == ord(quit_key):
                    break
            time.sleep(self._frame_delta_ms / 1000)
        if self._show_window:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    with Camera() as camera:
        with FaceDetectorInference() as detector:
            pipeline = FaceCameraPipeline(camera, detector)
            pipeline.run_pipeline()