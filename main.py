import time

from hardware.api import HardwareAPI
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
        hardware_api = HardwareAPI(port=PORT, baudrate=BAUD)
    except Exception as e:
        print(f"Error initializing hardware API: {e}")
        exit(1)

    try:
        timestamp_ms = 0
        while pipeline.is_alive(): # and (timestamp_ms <= 5000):
            state = pipeline.get_state()
            timestamp_ms = state['timestamp_ms']
            if state.get("is_running"):
                print(f"State: {state['num_faces']} face(s), ts={state['timestamp_ms']} ms")
                if state["num_faces"] > 0:
                    hardware_api.send_message("2", verbose=True)
                else:
                    hardware_api.send_message("0", verbose=True)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Keyboard Interrupt. Shutting down.")
    finally:
        # Always shut down the pipeline before exiting so the Manager stays alive
        # until the child exits. Otherwise the subprocess hits EOFError when it
        # touches the shared state after main (and the Manager) are gone.
        pipeline.request_quit()
        pipeline.join(timeout=2.0)
        hardware_api.close()
