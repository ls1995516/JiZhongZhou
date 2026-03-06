"""Render scene Pydantic models — geometry-oriented output consumed by the frontend 3D viewer."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

class GeometryPrimitive(str, Enum):
    box = "box"
    cylinder = "cylinder"
    extrusion = "extrusion"
    custom = "custom"


class Geometry(BaseModel):
    primitive: GeometryPrimitive
    params: dict[str, Any] = Field(default_factory=dict)
    vertices: Optional[list[list[float]]] = None  # for custom only
    indices: Optional[list[int]] = None


# ---------------------------------------------------------------------------
# Material
# ---------------------------------------------------------------------------

class Material(BaseModel):
    color: str = "#cccccc"
    opacity: float = 1.0
    metalness: float = 0.0
    roughness: float = 0.8


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

class Transform(BaseModel):
    position: tuple[float, float, float] = (0, 0, 0)
    rotation: tuple[float, float, float] = (0, 0, 0)
    scale: tuple[float, float, float] = (1, 1, 1)


# ---------------------------------------------------------------------------
# Scene objects
# ---------------------------------------------------------------------------

class SceneObjectType(str, Enum):
    mesh = "mesh"
    group = "group"


class ObjectMetadata(BaseModel):
    semantic_type: Optional[str] = None  # "wall", "floor-slab", "window", etc.
    label: Optional[str] = None


class SceneObject(BaseModel):
    id: str
    source_id: Optional[str] = None  # back-reference to project element
    type: SceneObjectType
    geometry: Optional[Geometry] = None
    material: Optional[Material] = None
    transform: Transform = Field(default_factory=Transform)
    children: list[SceneObject] = Field(default_factory=list)
    metadata: ObjectMetadata = Field(default_factory=ObjectMetadata)


# ---------------------------------------------------------------------------
# Lights & camera
# ---------------------------------------------------------------------------

class LightType(str, Enum):
    ambient = "ambient"
    directional = "directional"
    point = "point"


class Light(BaseModel):
    type: LightType
    color: str = "#ffffff"
    intensity: float = 1.0
    position: Optional[tuple[float, float, float]] = None


class Camera(BaseModel):
    position: tuple[float, float, float] = (20, 20, 20)
    target: tuple[float, float, float] = (0, 0, 0)
    fov: float = 50


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------

class SceneData(BaseModel):
    objects: list[SceneObject] = Field(default_factory=list)
    lights: list[Light] = Field(default_factory=lambda: [
        Light(type=LightType.ambient, intensity=0.4),
        Light(type=LightType.directional, intensity=0.8, position=(10, 20, 10)),
    ])
    camera: Camera = Field(default_factory=Camera)


class SceneJSON(BaseModel):
    """Complete render scene — the compiled artifact for the 3D viewer."""

    version: str = "0.1.0"
    metadata: dict[str, Any] = Field(default_factory=dict)
    scene: SceneData = Field(default_factory=SceneData)
