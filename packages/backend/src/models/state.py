"""LangGraph workflow state definitions."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Optional

from langgraph.graph import MessagesState
from pydantic import BaseModel, Field

from .project import ProjectJSON
from .scene import SceneJSON


# ---------------------------------------------------------------------------
# WF1: Project Authoring graph state
# ---------------------------------------------------------------------------

class AuthorPlan(str, Enum):
    create = "create"
    edit = "edit"
    clarify = "clarify"


class ProjectAuthoringState(MessagesState):
    """State flowing through the project authoring LangGraph workflow.

    Extends MessagesState so `messages` is managed automatically with
    the LangGraph message-list reducer.
    """

    project: Optional[ProjectJSON] = None
    plan: Optional[AuthorPlan] = None
    validation_errors: list[str] = Field(default_factory=list)
    retry_count: int = 0
    response_text: Optional[str] = None


# ---------------------------------------------------------------------------
# WF2: Geometry Compilation graph state
# ---------------------------------------------------------------------------

class CompileUnit(BaseModel):
    """A single compilable element extracted from the project."""

    element_type: str  # "floor_slab", "wall", "opening", "roof"
    element_id: str
    data: dict  # raw dict from the project element


class GeometryCompilationState(BaseModel):
    """State flowing through the geometry compilation LangGraph workflow."""

    project: ProjectJSON
    compile_units: list[CompileUnit] = Field(default_factory=list)
    scene: Optional[SceneJSON] = None
    errors: list[str] = Field(default_factory=list)
