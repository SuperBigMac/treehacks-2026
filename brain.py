"""
Orchestrates hardware and vision: move camera so face centroid aligns with target.

- Offset = derivative (we integrate to get position); plus P term so we don't miss the target.
- Command = integral + Kp * offset + bias (P+I).
"""
import math
from typing import List, Tuple

# Consider "on target" when crosshair is within this many pixels of face centroid (so small oscillations still fire)
ON_TARGET_RADIUS_PX = 40

from hardware.api import HardwareAPI
from vision.fisheye_utils import circle_radius_px_from_frame, offset_to_angle


class Brain:
    # Servo bounds (degrees); firmware uses x in [-45, 45], y in [-20, 30]
    ARM_X_BOUNDS = (-45, 45)
    ARM_Y_BOUNDS = (-20, 30)

    def __init__(
        self,
        hardware_api: HardwareAPI,
        target_x: float,
        target_y: float,
        gain_deg: float = 1.0,
        max_step_deg: float = 2.0,
        Kp: float = 0.4,
        dead_zone_deg: float = 1.5,
        arm_x_bias_deg: float = 0.0,
        arm_y_bias_deg: float = 0.0,
    ):
        self.hardware_api = hardware_api
        self.target_x = float(target_x)
        self.target_y = float(target_y)
        self.gain_deg = gain_deg
        self.max_step_deg = max_step_deg
        self.Kp = Kp  # proportional term so we don't overshoot / miss target
        self.dead_zone_deg = dead_zone_deg  # no correction when |pan_deg| and |tilt_deg| both below this
        self.arm_x_bias_deg = arm_x_bias_deg
        self.arm_y_bias_deg = arm_y_bias_deg
        self.is_shooting = False
        self.arm_x = 0.0
        self.arm_y = 0.0

    def _largest_face(
        self,
        detections: List[Tuple[int, int, int, int]],
    ) -> Tuple[int, int, int, int]:
        """Face bbox (x1, y1, x2, y2) with largest area."""
        def area(box: Tuple[int, int, int, int]) -> int:
            x1, y1, x2, y2 = box
            return (x2 - x1) * (y2 - y1)
        return max(detections, key=area)

    def run(
        self,
        detections: List[Tuple[int, int, int, int]],
        frame_width: int | None = None,
        frame_height: int | None = None,
        center_crop_fraction: float | None = None,
    ) -> None:
        if len(detections) == 0:
            self.arm_x = 0.0
            self.arm_y = 0.0
            return

        w = frame_width if frame_width is not None else 640
        h = frame_height if frame_height is not None else 480
        box = self._largest_face(detections)
        x1, y1, x2, y2 = box
        centroid_x = ((x1 + x2) / 2) / w
        centroid_y = ((y1 + y2) / 2) / h

        # Work in frame pixel space (from video feed / state)
        centroid_x_px = centroid_x * w
        centroid_y_px = centroid_y * h
        target_x_px = self.target_x * w if self.target_x <= 1.0 else self.target_x
        target_y_px = self.target_y * h if self.target_y <= 1.0 else self.target_y

        # Fisheye circle radius from current frame size (viewport = cut-off circle)
        circle_r = circle_radius_px_from_frame(w, h)
        pan_deg = offset_to_angle(
            centroid_x_px - target_x_px,
            radius_px=circle_r,
            crop_fraction=center_crop_fraction,
        )
        tilt_deg = offset_to_angle(
            centroid_y_px - target_y_px,
            radius_px=circle_r,
            crop_fraction=center_crop_fraction,
        )

        # Dead zone: when error is small, don't integrate or apply P so the arm can settle
        in_dead_zone = abs(pan_deg) < self.dead_zone_deg and abs(tilt_deg) < self.dead_zone_deg

        # Offset = derivative; integrate (accumulate) to get position. Positive y = tilt up so flip tilt.
        if not in_dead_zone:
            step_x = max(-self.max_step_deg, min(self.max_step_deg, self.gain_deg * pan_deg))
            step_y = max(-self.max_step_deg, min(self.max_step_deg, -self.gain_deg * tilt_deg))
            self.arm_x += step_x
            self.arm_y += step_y
        lo_x, hi_x = self.ARM_X_BOUNDS
        lo_y, hi_y = self.ARM_Y_BOUNDS
        self.arm_x = max(lo_x, min(hi_x, self.arm_x))
        self.arm_y = max(lo_y, min(hi_y, self.arm_y))

        # P + I: integral (arm_x/y) + proportional term so we pull toward target and don't miss
        p_x = 0.0 if in_dead_zone else self.Kp * pan_deg
        p_y = 0.0 if in_dead_zone else self.Kp * tilt_deg
        x_cmd = self.arm_x + p_x + self.arm_x_bias_deg
        y_cmd = self.arm_y - p_y + self.arm_y_bias_deg
        x_deg = int(round(max(lo_x, min(hi_x, x_cmd))))
        y_deg = int(round(max(lo_y, min(hi_y, y_cmd))))
        self.hardware_api.send_message(f"x {x_deg}", rate_limit=False)
        self.hardware_api.send_message(f"y {y_deg}", rate_limit=False)

        # Shoot when target point is inside face box or within ON_TARGET_RADIUS_PX of face centroid
        tx_frame = self.target_x * w if self.target_x <= 1.0 else self.target_x
        ty_frame = self.target_y * h if self.target_y <= 1.0 else self.target_y
        inside_box = x1 <= tx_frame <= x2 and y1 <= ty_frame <= y2
        dist_to_centroid = math.sqrt((tx_frame - centroid_x_px) ** 2 + (ty_frame - centroid_y_px) ** 2)
        on_target = inside_box or dist_to_centroid <= ON_TARGET_RADIUS_PX
        self.is_shooting = on_target
        self.hardware_api.send_message("1" if on_target else "0", rate_limit=False)
