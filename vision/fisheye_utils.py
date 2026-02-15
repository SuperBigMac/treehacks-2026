"""
Simple angle geometry for converting pixel positions to angles (pan/tilt).

Viewport = rectangle cutting off a circular fisheye image (equidistant: angle ∝ r).
Circle radius is derived from the actual frame size (video feed / state).
"""

import math
from typing import Tuple

# Angle (deg) from center to edge of the circle (~180° total → 90° to edge)
ANGLE_AT_EDGE_DEG = 90.0
MAX_THETA_DEG = ANGLE_AT_EDGE_DEG

# Circle covers center 2/3 of frame width → radius = frame_width * this fraction
CIRCLE_RADIUS_FRACTION_OF_WIDTH = 1.0 / 3.0

# Legacy / pixel_to_angle default when no frame size given
WIDTH = 3840
HEIGHT = 1920
CENTER_X = WIDTH / 2
CENTER_Y = HEIGHT / 2
RADIUS_PX = WIDTH / 3
RADIUS_X = RADIUS_PX
RADIUS_Y = RADIUS_PX


def circle_radius_px_from_frame(frame_width: int, frame_height: int) -> float:
    """Fisheye circle radius in frame pixels (viewport = cut-off circle)."""
    return frame_width * CIRCLE_RADIUS_FRACTION_OF_WIDTH


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
