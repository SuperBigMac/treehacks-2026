import time

from hardware.api import HardwareAPI, HardwareDisconnectedError
from hardware.mock_api import MockHardwareAPI
from vision.runner import FacePipelineRunner


# PORT = "COM11"
PORT = "/dev/tty.usbmodem101"
BAUD = 9600
message = "2"

if __name__ == "__main__":
    start_time = time.time()
    pipeline = FacePipelineRunner(show_window=True)
    pipeline.start()
    print("Pipeline running. Check state with pipeline.get_state()")

    try:
        # hardware_api = HardwareAPI(port=PORT, baudrate=BAUD)
        hardware_api = MockHardwareAPI(port=PORT, baudrate=BAUD)
    except Exception as e:
        print(f"Error initializing hardware API: {e}")
        exit(1)

    try:
        timestamp_ms = 0
        delay_seconds = 0.5
        last_message = time.time()
        last_heartbeat = time.time()
        heartbeat_interval = 0.3  # Arduino timeout 500ms; 300ms keeps alive without flooding
        while pipeline.is_alive():
            state = pipeline.get_state()
            timestamp_ms = state["timestamp_ms"]
            if state.get("is_running"):
                if time.time() - last_message > delay_seconds:
                    print(f"State: {state['num_faces']} face(s), ts={timestamp_ms} ms")
                    last_message = time.time()
                    try:
                        if state["num_faces"] > 0:
                            hardware_api.send_message("1", verbose=True)
                        else:
                            hardware_api.send_message("0", verbose=True)
                    except HardwareDisconnectedError as e:
                        print(f"Hardware: {e}")
            if time.time() - last_heartbeat >= heartbeat_interval:
                try:
                    hardware_api.send_heartbeat()
                    last_heartbeat = time.time()
                except HardwareDisconnectedError as e:
                    print(f"Hardware: {e}")
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("Keyboard Interrupt. Shutting down.")
    finally:
        # Always shut down the pipeline before exiting so the Manager stays alive
        # until the child exits. Otherwise the subprocess hits EOFError when it
        # touches the shared state after main (and the Manager) are gone.
        pipeline.request_quit()
        pipeline.join(timeout=2.0)
        hardware_api.close()
