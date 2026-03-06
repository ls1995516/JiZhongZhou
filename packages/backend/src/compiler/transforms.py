"""Spatial transform utilities."""

from __future__ import annotations

import math

from ..models.scene import Transform


def translate(t: Transform, dx: float = 0, dy: float = 0, dz: float = 0) -> Transform:
    px, py, pz = t.position
    return t.model_copy(update={"position": (px + dx, py + dy, pz + dz)})


def rotate_y(t: Transform, angle_rad: float) -> Transform:
    rx, ry, rz = t.rotation
    return t.model_copy(update={"rotation": (rx, ry + angle_rad, rz)})


def degrees_to_radians(deg: float) -> float:
    return deg * math.pi / 180.0
