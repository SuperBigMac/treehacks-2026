import serial
import time
from multiprocessing import Manager, Process

from hardware.api import HardwareAPI
from vision.pipeline import run_pipeline_in_process

# --- Face pipeline (always runs in a subprocess; state via Manager dict) ---


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

    def request_quit(self) -> None:
        self._state["quit_requested"] = True

    def is_alive(self) -> bool:
        return self._process.is_alive()

    def join(self, timeout: float | None = None) -> None:
        self._process.join(timeout=timeout)


# --- Hardware demo (optional) ---

# PORT = "COM11"
PORT = "/dev/tty.usbmodem101"
BAUD = 9600
message = "2"

if __name__ == "__main__":
    pipeline = FacePipelineRunner(show_window=True)
    pipeline.start()
    print("Pipeline running. Check state with pipeline.get_state()")

    try:
        while pipeline.is_alive():
            state = pipeline.get_state()
            if state.get("is_running") and state.get("num_faces", 0) > 0:
                print(f"State: {state['num_faces']} face(s), ts={state['timestamp_ms']} ms")
            time.sleep(0.5)
    except KeyboardInterrupt:
        pipeline.request_quit()
        pipeline.join(timeout=2.0)

    # Uncomment below to run the hardware serial demo:
    # hardware_api = HardwareAPI(port=PORT, baudrate=BAUD)
    # ser = serial.Serial(port=PORT, baudrate=BAUD)
    # print("Initialized serial connection")
    # time.sleep(2)
    # hardware_api.send_message(message, verbose=True)
    # hardware_api.close()
