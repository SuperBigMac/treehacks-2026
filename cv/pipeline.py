"""
Composes camera and inference; runs the capture–detect–display loop.
Camera and inference are separate APIs; this class only orchestrates them.
"""

import cv2

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
        window_name: str = "Faces",
    ):
        self._camera = camera
        self._detector = detector
        self._frame_delta_ms = frame_delta_ms
        self._window_name = window_name

    def run_until_quit(self, quit_key: str = "q") -> None:
        """Run capture → detect → display until the user presses quit_key."""
        timestamp_ms = 0
        while True:
            ok, frame = self._camera.read()
            if not ok or frame is None:
                print("Camera stopped returning frames. Exiting.")
                break
            for x1, y1, x2, y2 in self._detector.detect(frame, timestamp_ms):
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            timestamp_ms += self._frame_delta_ms
            cv2.imshow(self._window_name, frame)
            if cv2.waitKey(1) & 0xFF == ord(quit_key):
                break
        cv2.destroyAllWindows()

    @classmethod
    def with_defaults(
        cls,
        camera_index: int = 0,
        frame_delta_ms: int = DEFAULT_FRAME_DELTA_MS,
        window_name: str = "Faces",
        **detector_kwargs,
    ) -> "FaceCameraPipeline":
        """Build a pipeline with default Camera and FaceDetectorInference. Caller must close camera and detector when done."""
        camera = Camera(camera_index=camera_index)
        detector = FaceDetectorInference(**detector_kwargs)
        return cls(camera=camera, detector=detector, frame_delta_ms=frame_delta_ms, window_name=window_name)

    @classmethod
    def run_with_defaults(
        cls,
        camera_index: int = 0,
        frame_delta_ms: int = DEFAULT_FRAME_DELTA_MS,
        window_name: str = "Faces",
        **detector_kwargs,
    ) -> None:
        """Create camera and detector, run pipeline until quit, then close both."""
        with Camera(camera_index=camera_index) as camera:
            with FaceDetectorInference(**detector_kwargs) as detector:
                pipeline = cls(camera=camera, detector=detector, frame_delta_ms=frame_delta_ms, window_name=window_name)
                pipeline.run_until_quit()
