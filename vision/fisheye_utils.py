"""
Simple angle geometry for converting pixel positions to angles (pan/tilt).

- theta: 0° at center, 100° at edge (200° total FOV).
- phi: 0°–360° azimuth.

Used by Brain for camera pan/tilt from normalized frame coords (crop/resize only, no calibration).
"""

import math
from typing import Tuple

# Default frame size (Brain uses for normalized 0–1 → virtual pixel space)
WIDTH = 3840
HEIGHT = 1920

# Center of frame; radius from center to edge of useful FOV
CENTER_X = 1920  # WIDTH / 2
CENTER_Y = 960   # HEIGHT / 2
RADIUS_PX = 960  # pixels from center to edge
MAX_THETA_DEG = 100  # polar angle at edge (100° from center → 200° total)


def pixel_to_angle(
    x: float,
    y: float,
    center_x: float = CENTER_X,
    center_y: float = CENTER_Y,
    radius_px: float = RADIUS_PX,
    max_theta_deg: float = MAX_THETA_DEG,
    crop_fraction: float | None = None,
) -> Tuple[float, float]:
    """
    Convert pixel (x, y) to angles.
    Returns (theta_deg, phi_deg): theta 0° at center, phi 0°–360°.
    When center_crop_fraction is used, the visible FOV is smaller; pass
    crop_fraction (e.g. 0.6) so angle scale matches the cropped image.
    """
    f = crop_fraction if crop_fraction is not None else 1.0
    effective_max_theta = max_theta_deg * f
    dx = x - center_x
    dy = y - center_y
    r_pixel = math.sqrt(dx * dx + dy * dy)
    theta = (r_pixel / radius_px) * effective_max_theta if radius_px > 0 else 0.0
    phi_rad = math.atan2(dy, dx)
    phi = math.degrees(phi_rad)
    if phi < 0:
        phi += 360.0
    return theta, phi


def face_box_to_angle(
    box: Tuple[float, float, float, float],
    center_x: float = CENTER_X,
    center_y: float = CENTER_Y,
    radius_px: float = RADIUS_PX,
    max_theta_deg: float = MAX_THETA_DEG,
    crop_fraction: float | None = None,
) -> Tuple[float, float]:
    """Convert face bbox (x1, y1, x2, y2) to (theta_deg, phi_deg) using box center."""
    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    return pixel_to_angle(
        cx, cy, center_x, center_y, radius_px, max_theta_deg, crop_fraction
    )


def offset_to_angle(
    delta_pixels: float,
    radius_px: float = RADIUS_PX,
    max_theta_deg: float = MAX_THETA_DEG,
    crop_fraction: float | None = None,
) -> float:
    """Convert radial pixel offset to angle in degrees.
    Pass crop_fraction when using a center-cropped image so scale matches FOV."""
    f = crop_fraction if crop_fraction is not None else 1.0
    effective_max_theta = max_theta_deg * f
    return (delta_pixels / radius_px) * effective_max_theta if radius_px > 0 else 0.0
