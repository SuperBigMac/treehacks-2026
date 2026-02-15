"""
orchestrates the hardware and vision pipeline

- receives face detections from vision pipeline
- calculates the arm position to move the camera to the target
- sends the arm position to the hardware
- sends the shooting command to the hardware
- repeats the process
"""
from typing import List, Tuple

from hardware.api import HardwareAPI
from vision.fisheye_utils import (
    WIDTH,
    HEIGHT,
    offset_to_angle,
    pixel_to_angle,
)

class Brain:
    def __init__(
        self,
        hardware_api: HardwareAPI,
        target_x: float,
        target_y: float,
    ):
        self.is_shooting = False
        self.arm_x = 0
        self.arm_y = 0
        self.hardware_api = hardware_api
        self.target_x = target_x
        self.target_y = target_y
        # Set in run(): face/target angles (deg), deltas, and pixel-offset → angle deltas
        self.face_theta_deg: float | None = None
        self.face_phi_deg: float | None = None
        self.target_theta_deg: float | None = None
        self.target_phi_deg: float | None = None
        self.delta_theta_deg: float | None = None
        self.delta_phi_deg: float | None = None
        self.angle_delta_x_deg: float | None = None
        self.angle_delta_y_deg: float | None = None
        # Camera move to align centroid with target (deg): pan = azimuth, tilt = polar
        self.camera_pan_deg: float | None = None   # + = pan right
        self.camera_tilt_deg: float | None = None  # + = tilt down
        # Centroid in normalized coords (0–1, % of screen)
        self.centroid_x: float | None = None
        self.centroid_y: float | None = None
        self._arm_x_bounds = (-180, 180)
        self._arm_y_bounds = (-20, 90)

    def _target_px(self) -> Tuple[float, float]:
        """Target in pixel coords (normalized 0–1 or already pixels)."""
        tx = self.target_x * WIDTH if self.target_x <= 1.0 else self.target_x
        ty = self.target_y * HEIGHT if self.target_y <= 1.0 else self.target_y
        return tx, ty

    def fix_arm_positions(self) -> None:
        """Wrap arm positions into [low, high) so they stay within bounds."""
        lo, hi = self._arm_x_bounds
        r = hi - lo
        self.arm_x = ((self.arm_x - lo) % r) + lo
        if self.arm_y < self._arm_y_bounds[0]:
            self.arm_y = self._arm_y_bounds[0]
        elif self.arm_y > self._arm_y_bounds[1]:
            self.arm_y = self._arm_y_bounds[1]
    

    def send_arm_positions(self) -> None:
        """Send arm positions to hardware."""
        self.hardware_api.send_message(f"x {self.arm_x}", rate_limit=False)
        self.hardware_api.send_message(f"y {self.arm_y}", rate_limit=False)

    def _clear_state(self) -> None:
        """Clear angle, centroid, and camera-move state (no detections)."""
        self.face_theta_deg = self.face_phi_deg = None
        self.target_theta_deg = self.target_phi_deg = None
        self.delta_theta_deg = self.delta_phi_deg = None
        self.angle_delta_x_deg = self.angle_delta_y_deg = None
        self.camera_pan_deg = self.camera_tilt_deg = None
        self.centroid_x = self.centroid_y = None

    def _most_central_face(
        self,
        detections: List[Tuple[int, int, int, int]],
        frame_width: int,
        frame_height: int,
    ) -> Tuple[int, int, int, int]:
        """Return the face bbox (x1, y1, x2, y2) whose center is closest to frame center."""
        cx_center = frame_width / 2
        cy_center = frame_height / 2
        best = detections[0]
        best_cx = (best[0] + best[2]) / 2
        best_cy = (best[1] + best[3]) / 2
        best_d2 = (best_cx - cx_center) ** 2 + (best_cy - cy_center) ** 2
        for det in detections[1:]:
            cx = (det[0] + det[2]) / 2
            cy = (det[1] + det[3]) / 2
            d2 = (cx - cx_center) ** 2 + (cy - cy_center) ** 2
            if d2 < best_d2:
                best_d2 = d2
                best = det
        return best

    def _update_angles(
        self,
        centroid_x: float,
        centroid_y: float,
        tx_px: float,
        ty_px: float,
        center_crop_fraction: float | None = None,
    ) -> None:
        """Set angle state and camera pan/tilt. centroid_x/y are normalized 0–1.
        Uses virtual fisheye space (WIDTH×HEIGHT) so angles are correct for both
        raw fisheye and rectilinear (e.g. 640×480) inference frames.
        center_crop_fraction (e.g. 0.6) scales angle conversion when using a cropped image."""
        centroid_x_px = centroid_x * WIDTH
        centroid_y_px = centroid_y * HEIGHT
        crop = center_crop_fraction
        self.face_theta_deg, self.face_phi_deg = pixel_to_angle(
            centroid_x_px, centroid_y_px, crop_fraction=crop
        )
        self.target_theta_deg, self.target_phi_deg = pixel_to_angle(
            tx_px, ty_px, crop_fraction=crop
        )
        self.delta_theta_deg = self.face_theta_deg - self.target_theta_deg
        self.delta_phi_deg = self.face_phi_deg - self.target_phi_deg
        self.angle_delta_x_deg = offset_to_angle(
            centroid_x_px - tx_px, crop_fraction=crop
        )
        self.angle_delta_y_deg = offset_to_angle(
            centroid_y_px - ty_px, crop_fraction=crop
        )
        self.camera_pan_deg = self.angle_delta_x_deg
        self.camera_tilt_deg = self.angle_delta_y_deg
        print(f"camera move: pan={self.camera_pan_deg:+.2f}° tilt={self.camera_tilt_deg:+.2f}°")

    def _step_arm(self, pan_deg: float, tilt_deg: float) -> None:
        """Update arm by pan/tilt deltas, clamp to bounds, send to hardware."""
        self.arm_x += pan_deg
        self.arm_y += tilt_deg
        self.fix_arm_positions()
        self.send_arm_positions()

    def _update_shooting(
        self,
        box: Tuple[int, int, int, int],
        tx_px: float,
        ty_px: float,
    ) -> None:
        """Set is_shooting when target is inside the face bbox shrunk to 0.8x (same center)."""
        x1, y1, x2, y2 = box
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        w_box = x2 - x1
        h_box = y2 - y1
        half_w = 0.4 * w_box
        half_h = 0.4 * h_box
        on_target = (
            abs(tx_px - cx) <= half_w
            and abs(ty_px - cy) <= half_h
        )
        self.is_shooting = on_target
        print(f"shooting: {on_target}")
        self.hardware_api.send_message("1" if on_target else "0", rate_limit=False)

    def run(
        self,
        detections: List[Tuple[int, int, int, int]],
        frame_width: int | None = None,
        frame_height: int | None = None,
        center_crop_fraction: float | None = None,
    ) -> None:
        if len(detections) == 0:
            self._clear_state()
            return

        # Use actual frame size for normalization so centroid is 0–1 (% of screen)
        w = frame_width if frame_width is not None else WIDTH
        h = frame_height if frame_height is not None else HEIGHT

        box = self._most_central_face(detections, w, h)
        x1, y1, x2, y2 = box
        self.centroid_x = ((x1 + x2) / 2) / w
        self.centroid_y = ((y1 + y2) / 2) / h
        tx_px, ty_px = self._target_px()
        # Target in frame pixel coords (same space as box) for shoot check
        tx_frame = self.target_x * w if self.target_x <= 1.0 else self.target_x
        ty_frame = self.target_y * h if self.target_y <= 1.0 else self.target_y

        self._update_angles(
            self.centroid_x,
            self.centroid_y,
            tx_px,
            ty_px,
            center_crop_fraction=center_crop_fraction,
        )
        # Negate tilt so hardware "up" matches view (face above target → tilt up)
        self._step_arm(self.angle_delta_x_deg, -self.angle_delta_y_deg)
        self._update_shooting(box, tx_frame, ty_frame)