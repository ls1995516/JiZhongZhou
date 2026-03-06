"""Request/response models for the REST API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .project import ProjectJSON
from .reference import ReferenceMetadata
from .scene import SceneJSON


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None


class UpdateProjectRequest(BaseModel):
    prompt: str  # natural-language user instruction


class SaveProjectRequest(BaseModel):
    project: ProjectJSON
    scene: Optional[SceneJSON] = None


class CreateReferenceRequest(BaseModel):
    metadata: ReferenceMetadata
    source_project_id: str


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class ProjectResponse(BaseModel):
    project: ProjectJSON


class SavedProjectMetadata(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_saved_at: Optional[str] = None
    has_render_scene: bool = False


class SavedProjectResponse(BaseModel):
    project: ProjectJSON
    scene: Optional[SceneJSON] = None
    metadata: SavedProjectMetadata
    history: list[dict] = Field(default_factory=list)


class ReferenceResponse(BaseModel):
    metadata: ReferenceMetadata
    project: ProjectJSON


class SceneResponse(BaseModel):
    scene: SceneJSON


class TurnResponse(BaseModel):
    """Full response from an authoring turn: assistant reply + updated artefacts."""

    assistant_message: str
    project: ProjectJSON
    scene: SceneJSON
