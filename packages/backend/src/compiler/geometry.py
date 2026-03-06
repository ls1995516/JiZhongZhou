"""Deterministic geometry generation from project elements."""

from __future__ import annotations

import math

from ..models.project import Floor, Opening, Wall, Vector2
from ..models.scene import (
    Geometry,
    GeometryPrimitive,
    Material,
    ObjectMetadata,
    SceneObject,
    SceneObjectType,
    Transform,
)


def _wall_length(wall: Wall) -> float:
    dx = wall.end.x - wall.start.x
    dy = wall.end.y - wall.start.y
    return math.sqrt(dx * dx + dy * dy)


def _wall_angle(wall: Wall) -> float:
    dx = wall.end.x - wall.start.x
    dy = wall.end.y - wall.start.y
    return math.atan2(dy, dx)


def compile_floor_slab(floor: Floor) -> SceneObject:
    """Generate a thin box for the floor slab based on the outline bounding box."""
    xs = [p.x for p in floor.outline.points]
    ys = [p.y for p in floor.outline.points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = max_x - min_x
    depth = max_y - min_y
    slab_thickness = 0.2

    return SceneObject(
        id=f"slab-{floor.id}",
        source_id=floor.id,
        type=SceneObjectType.mesh,
        geometry=Geometry(
            primitive=GeometryPrimitive.box,
            params={"width": width, "height": slab_thickness, "depth": depth},
        ),
        material=Material(color="#888888", roughness=0.9),
        transform=Transform(
            position=(
                (min_x + max_x) / 2,
                floor.elevation,
                (min_y + max_y) / 2,
            ),
        ),
        metadata=ObjectMetadata(semantic_type="floor-slab", label=floor.label),
    )


def compile_wall(wall: Wall, floor: Floor) -> SceneObject:
    """Generate a box for a wall segment."""
    length = _wall_length(wall)
    angle = _wall_angle(wall)
    mid_x = (wall.start.x + wall.end.x) / 2
    mid_y = (wall.start.y + wall.end.y) / 2

    return SceneObject(
        id=f"wall-{wall.id}",
        source_id=wall.id,
        type=SceneObjectType.mesh,
        geometry=Geometry(
            primitive=GeometryPrimitive.box,
            params={"width": length, "height": floor.height, "depth": wall.thickness},
        ),
        material=Material(color="#e0e0e0", roughness=0.85),
        transform=Transform(
            position=(mid_x, floor.elevation + floor.height / 2, mid_y),
            rotation=(0, -angle, 0),
        ),
        metadata=ObjectMetadata(semantic_type="wall"),
    )


def compile_opening(opening: Opening, wall: Wall, floor: Floor) -> SceneObject:
    """Generate a placeholder box for a door or window opening."""
    length = _wall_length(wall)
    angle = _wall_angle(wall)

    offset_along = (opening.position - 0.5) * length
    mid_x = (wall.start.x + wall.end.x) / 2 + offset_along * math.cos(angle)
    mid_y = (wall.start.y + wall.end.y) / 2 + offset_along * math.sin(angle)

    color = "#4a90d9" if opening.type.value == "window" else "#8B4513"
    opacity = 0.4 if opening.type.value == "window" else 1.0

    return SceneObject(
        id=f"opening-{opening.id}",
        source_id=opening.id,
        type=SceneObjectType.mesh,
        geometry=Geometry(
            primitive=GeometryPrimitive.box,
            params={
                "width": opening.width,
                "height": opening.height,
                "depth": wall.thickness + 0.02,
            },
        ),
        material=Material(color=color, opacity=opacity, roughness=0.3),
        transform=Transform(
            position=(
                mid_x,
                floor.elevation + opening.sill_height + opening.height / 2,
                mid_y,
            ),
            rotation=(0, -angle, 0),
        ),
        metadata=ObjectMetadata(
            semantic_type=opening.type.value,
            label=f"{opening.type.value}-{opening.id}",
        ),
    )
