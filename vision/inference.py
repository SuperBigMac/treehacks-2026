"""
Face detection inference using YOLOv8m (Ultralytics).
"""

import os
import urllib.request

import cv2
from ultralytics import YOLO

# Face-trained YOLOv8m weights (Bingsu/adetailer on Hugging Face)
MODEL_FILENAME = "face_yolov8m.pt"
MODEL_URL = (
    "https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov8m.pt"
)


def _default_model_path() -> str:
    return os.path.join(os.path.dirname(__file__), MODEL_FILENAME)


def _ensure_model(path: str) -> None:
    if os.path.exists(path):
        return
    print("Downloading YOLOv8m face detection model...")
    urllib.request.urlretrieve(MODEL_URL, path)


class FaceDetectorInference:
    """
    Runs face detection on video frames using YOLOv8m (face-trained).
    Use as a context manager so the detector is closed properly.
    """

    def __init__(
        self,
        model_path: str | None = None,
        min_detection_confidence: float = 0.5,
        **kwargs,
    ):
        self._model_path = model_path or _default_model_path()
        _ensure_model(self._model_path)
        self._model = YOLO(self._model_path)
        self._conf = min_detection_confidence
        self._kwargs = kwargs

    def detect(
        self,
        frame_bgr: cv2.typing.MatLike,
        timestamp_ms: int,
    ) -> list[tuple[int, int, int, int]]:
        """
        Run face detection on a single frame.

        Args:
            frame_bgr: BGR image (e.g. from cv2.VideoCapture).
            timestamp_ms: Frame timestamp in milliseconds (unused; for API compatibility).

        Returns:
            List of bounding boxes as (x1, y1, x2, y2) in image coordinates.
        """
        results = self._model.predict(
            frame_bgr,
            conf=self._conf,
            verbose=False,
            **self._kwargs,
        )
        boxes = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                xyxy = box.xyxy[0]
                x1 = int(xyxy[0].item())
                y1 = int(xyxy[1].item())
                x2 = int(xyxy[2].item())
                y2 = int(xyxy[3].item())
                boxes.append((x1, y1, x2, y2))
        return boxes

    def close(self) -> None:
        # Ultralytics YOLO doesn't require explicit close; no-op for API compatibility
        pass

    def __enter__(self) -> "FaceDetectorInference":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
