"""Project JSON Pydantic models — the semantic source of truth for a building."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

class Vector2(BaseModel):
    x: float
    y: float


class Vector3(BaseModel):
    x: float
    y: float
    z: float


class Polygon(BaseModel):
    points: list[Vector2] = Field(..., min_length=3)


# ---------------------------------------------------------------------------
# Building elements
# ---------------------------------------------------------------------------

class OpeningType(str, Enum):
    door = "door"
    window = "window"


class Opening(BaseModel):
    id: str
    type: OpeningType
    position: float = Field(..., ge=0, le=1, description="Normalized offset along wall")
    width: float
    height: float
    sill_height: float = Field(default=0, description="Height of sill above floor")


class Wall(BaseModel):
    id: str
    start: Vector2
    end: Vector2
    thickness: float = 0.2
    openings: list[Opening] = Field(default_factory=list)


class Room(BaseModel):
    id: str
    label: str
    outline: Polygon
    function: Optional[str] = None


class RoofType(str, Enum):
    flat = "flat"
    gable = "gable"
    hip = "hip"


class Floor(BaseModel):
    id: str
    label: Optional[str] = None
    elevation: float = Field(..., description="Meters above ground")
    height: float = Field(..., description="Floor-to-floor height in meters")
    outline: Polygon
    walls: list[Wall] = Field(default_factory=list)
    rooms: list[Room] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------

class SiteInfo(BaseModel):
    dimensions: Vector2 = Field(default_factory=lambda: Vector2(x=50, y=50))
    elevation: float = 0


class BuildingInfo(BaseModel):
    floors: list[Floor]
    roof_type: RoofType = RoofType.flat


class ProjectMetadata(BaseModel):
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectJSON(BaseModel):
    """Complete project document — the semantic representation of a building."""

    version: str = "0.1.0"
    id: str
    metadata: ProjectMetadata
    site: SiteInfo = Field(default_factory=SiteInfo)
    building: BuildingInfo
