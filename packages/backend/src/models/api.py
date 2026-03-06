"""Request/response models for the REST API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from .project import ProjectJSON
from .scene import SceneJSON


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None


class UpdateProjectRequest(BaseModel):
    prompt: str  # natural-language user instruction


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class ProjectResponse(BaseModel):
    project: ProjectJSON


class SceneResponse(BaseModel):
    scene: SceneJSON


class TurnResponse(BaseModel):
    """Full response from an authoring turn: assistant reply + updated artefacts."""

    assistant_message: str
    project: ProjectJSON
    scene: SceneJSON
