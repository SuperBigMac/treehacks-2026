import time

from hardware.api import HardwareAPI, HardwareDisconnectedError
from hardware.mock_api import MockHardwareAPI
from vision.runner import FacePipelineRunner
from brain import Brain


PORT = "COM10"
# PORT = "/dev/tty.usbmodem101"
BAUD = 9600
message = "2"

target_x = 0.52
target_y = 0.45

if __name__ == "__main__":
    start_time = time.time()
    pipeline = FacePipelineRunner(
        show_window=True,
        camera_index=1,
        rotate_180=True,
        center_crop_fraction=1,
    )
    pipeline.start()
    print("Pipeline running. Check state with pipeline.get_state()")

    # display dummy point
    pipeline.update_state(pause_detection=False, target_x=target_x, target_y=target_y)

    try:
        hardware_api = HardwareAPI(port=PORT, baudrate=BAUD)
        # hardware_api = MockHardwareAPI(port=PORT, baudrate=BAUD)
    except Exception as e:
        print(f"Error initializing hardware API: {e}")
        exit(1)

    # initialize the brain (gain_deg: scale on fisheye angle, 1.0=use as-is; bias: mechanical offset)
    # Lower Kp and gain_deg to reduce oscillation so crosshair can settle on face
    brain = Brain(hardware_api, target_x, target_y, gain_deg=0.7, Kp=0.4)

    try:
        timestamp_ms = 0
        print_interval = 0.3
        last_print = time.time()
        last_heartbeat = time.time()
        heartbeat_interval = 0.3  # Arduino timeout 500ms; 300ms keeps alive without flooding
        while pipeline.is_alive():
            state = pipeline.get_state()
            timestamp_ms = state["timestamp_ms"]
            if state.get("is_running"):
                faces = state.get("faces", [])
                fw, fh = state.get("frame_width"), state.get("frame_height")
                if len(faces) > 0 and fw is not None and fh is not None:
                    try:
                        brain.run(
                            faces,
                            frame_width=fw,
                            frame_height=fh,
                            center_crop_fraction=state.get("center_crop_fraction")
                        )
                    except HardwareDisconnectedError as e:
                        print(f"Hardware: {e}")
                if time.time() - last_print >= print_interval:
                    n = state["num_faces"]
                    print(f"State: {n} face(s), ts={timestamp_ms} ms")
                    for i, (x1, y1, x2, y2) in enumerate(faces):
                        print(f"  face[{i}] box=({x1}, {y1}, {x2}, {y2})")
                    if len(faces) > 0:
                        print(f"arm_x: {brain.arm_x}, arm_y: {brain.arm_y}")
                    last_print = time.time()
            if time.time() - last_heartbeat >= heartbeat_interval:
                try:
                    hardware_api.send_heartbeat()
                    last_heartbeat = time.time()
                except HardwareDisconnectedError as e:
                    print(f"Hardware: {e}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        brain.hardware_api.send_message("x 0", rate_limit=False)
        brain.hardware_api.send_message("y 0", rate_limit=False)
        brain.hardware_api.send_message("0", rate_limit=False)
        print("Keyboard Interrupt. Shutting down.")
    finally:
        # Always shut down the pipeline before exiting so the Manager stays alive
        # until the child exits. Otherwise the subprocess hits EOFError when it
        # touches the shared state after main (and the Manager) are gone.
        pipeline.request_quit()
        pipeline.join(timeout=2.0)
        hardware_api.close()
