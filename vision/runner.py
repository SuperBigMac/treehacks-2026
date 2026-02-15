"""
For running vision pipeline in multiprocessing
"""

from multiprocessing import Manager, Process
from vision.pipeline import run_pipeline_in_process

def _default_state() -> dict:
    return {
        "is_running": False,
        "timestamp_ms": 0,
        "num_faces": 0,
        "faces": [],
        "quit_requested": False,
    }


class FacePipelineRunner:
    """Runs FaceCameraPipeline in a subprocess. State is shared via Manager().dict()."""

    def __init__(
        self,
        show_window: bool = True,
        camera_index: int = 0,
        frame_fps: int = 30,
        window_name: str = "Video Feed",
    ):
        self._manager = Manager()
        self._state = self._manager.dict()
        self._state.update(_default_state())
        self._process = Process(
            target=run_pipeline_in_process,
            args=(self._state,),
            kwargs={
                "show_window": show_window,
                "camera_index": camera_index,
                "frame_fps": frame_fps,
                "window_name": window_name,
            },
        )

    def start(self) -> None:
        self._process.start()

    def get_state(self) -> dict:
        """Snapshot of pipeline state (is_running, timestamp_ms, num_faces, faces)."""
        return dict(self._state)

    def update_state(self, **kwargs: object) -> None:
        """Write state from main process; the vision subprocess can read these keys."""
        for k, v in kwargs.items():
            self._state[k] = v

    def request_quit(self) -> None:
        self._state["quit_requested"] = True

    def is_alive(self) -> bool:
        return self._process.is_alive()

    def join(self, timeout: float | None = None) -> None:
        self._process.join(timeout=timeout)