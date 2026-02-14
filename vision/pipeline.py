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
        shared_state: dict | None = None,
    ):
        self._camera = camera
        self._detector = detector
        self._frame_fps = frame_fps
        self._frame_delta_ms = int(1000 / frame_fps)
        self._window_name = window_name
        self._show_window = show_window
        self._shared_state = shared_state  # When set, updated each frame for cross-process reads
        self._state = {
            "is_running": False,
            "timestamp_ms": 0,
            "num_faces": 0,
            "faces": [],
        }
        
    def _write_state(self, **kwargs: object) -> bool:
        """Update state; write to shared_state if present. Returns False if Manager connection is dead (parent exited)."""
        self._state.update(kwargs)
        if self._shared_state is not None:
            try:
                for k, v in kwargs.items():
                    self._shared_state[k] = v
            except (EOFError, ConnectionError, OSError):
                return False
        return True

    def _should_quit(self) -> bool:
        """True if quit_requested or shared_state connection is dead (parent exited)."""
        if self._shared_state is None:
            return False
        try:
            return bool(self._shared_state.get("quit_requested"))
        except (EOFError, ConnectionError, OSError):
            return True  # parent gone, exit cleanly

    def run_pipeline(self, quit_key: str = "q") -> None:
        start_time_sec = time.time()
        if not self._write_state(is_running=True):
            return
        while True:
            try:
                if self._should_quit():
                    break
                curr_time_ms = int((time.time() - start_time_sec) * 1000)
                ret, frame = self._camera.read()
                if not ret or frame is None:
                    break
                faces = self._detector.detect(frame, curr_time_ms)

                if not self._write_state(
                    timestamp_ms=curr_time_ms,
                    num_faces=len(faces),
                    faces=list(faces),
                ):
                    break
                for (x1, y1, x2, y2) in faces:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                if self._show_window:
                    cv2.imshow(self._window_name, frame)
                    if cv2.waitKey(self._frame_delta_ms) == ord(quit_key):
                        break
                time.sleep(self._frame_delta_ms / 1000)
            except KeyboardInterrupt:
                break
        if self._show_window:
            cv2.destroyAllWindows()
        self._write_state(is_running=False)
    
    def getState(self) -> dict[str, any]:
        """
        Get the state of the pipeline.
        """
        return self._state


def run_pipeline_in_process(
    shared_state: dict,
    *,
    show_window: bool = True,
    camera_index: int = 0,
    frame_fps: int = DEFAULT_FRAME_FPS,
    window_name: str = "Video Feed",
) -> None:
    """Entry point for a subprocess: runs the pipeline on this process's main thread (required for cv2.imshow on macOS)."""
    try:
        with Camera(camera_index=camera_index) as camera:
            with FaceDetectorInference() as detector:
                pipeline = FaceCameraPipeline(
                    camera,
                    detector,
                    frame_fps=frame_fps,
                    window_name=window_name,
                    show_window=show_window,
                    shared_state=shared_state,
                )
                pipeline.run_pipeline()
    except KeyboardInterrupt:
        print("Keyboard Interrupt. Shutting down.")  # Ctrl+C in subprocess: exit quietly so main can join()


if __name__ == "__main__":
    with Camera() as camera:
        with FaceDetectorInference() as detector:
            pipeline = FaceCameraPipeline(camera, detector)
            pipeline.run_pipeline()