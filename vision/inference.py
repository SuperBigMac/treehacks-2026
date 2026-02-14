"""
Face detection inference using MediaPipe.
"""

import os
import urllib.request

import cv2
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import FaceDetector, FaceDetectorOptions, RunningMode
from mediapipe.tasks.python.vision.core.image import Image as MpImage
from mediapipe.tasks.python.vision.core.image import ImageFormat

MODEL_FILENAME = "face_detection_short_range.tflite"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_detector/"
    "blaze_face_short_range/float16/latest/blaze_face_short_range.tflite"
)


def _default_model_path() -> str:
    return os.path.join(os.path.dirname(__file__), MODEL_FILENAME)


def _ensure_model(path: str) -> None:
    if os.path.exists(path):
        return
    print("Downloading face detection model...")
    urllib.request.urlretrieve(MODEL_URL, path)


class FaceDetectorInference:
    """
    Runs face detection on video frames using a MediaPipe BlazeFace model.
    Use as a context manager so the detector is closed properly.
    """

    def __init__(
        self,
        model_path: str | None = None,
        min_detection_confidence: float = 0.5,
        delegate: BaseOptions.Delegate = BaseOptions.Delegate.CPU,
    ):
        self._model_path = model_path or _default_model_path()
        _ensure_model(self._model_path)
        options = FaceDetectorOptions(
            base_options=BaseOptions(
                model_asset_path=self._model_path,
                delegate=delegate,
            ),
            running_mode=RunningMode.VIDEO,
            min_detection_confidence=min_detection_confidence,
        )
        self._detector = FaceDetector.create_from_options(options)

    def detect(
        self,
        frame_bgr: cv2.typing.MatLike,
        timestamp_ms: int,
    ) -> list[tuple[int, int, int, int]]:
        """
        Run face detection on a single frame.

        Args:
            frame_bgr: BGR image (e.g. from cv2.VideoCapture).
            timestamp_ms: Frame timestamp in milliseconds (used for video mode).

        Returns:
            List of bounding boxes as (x1, y1, x2, y2) in image coordinates.
        """
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = MpImage(ImageFormat.SRGB, rgb.copy())
        results = self._detector.detect_for_video(mp_image, timestamp_ms)
        boxes = []
        if results.detections:
            for d in results.detections:
                b = d.bounding_box
                x1 = int(b.origin_x)
                y1 = int(b.origin_y)
                x2 = x1 + int(b.width)
                y2 = y1 + int(b.height)
                boxes.append((x1, y1, x2, y2))
        return boxes

    def close(self) -> None:
        self._detector.close()

    def __enter__(self) -> "FaceDetectorInference":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
