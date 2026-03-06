"""FastAPI route definitions."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from ..models.api import (
    CreateProjectRequest,
    ProjectResponse,
    SaveProjectRequest,
    SavedProjectMetadata,
    SavedProjectResponse,
    SceneResponse,
    TurnResponse,
    UpdateProjectRequest,
)
from ..storage.project_store import StoredProjectRecord, StoredProjectSummary
from ..models.state import GeometryCompilationState, ProjectAuthoringState
from ..services.project_service import ProjectService
from ..services.scene_service import SceneService

logger = logging.getLogger(__name__)


def _to_saved_metadata(summary: StoredProjectSummary) -> SavedProjectMetadata:
    return SavedProjectMetadata(
        project_id=summary.project_id,
        name=summary.name,
        description=summary.description,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
        last_saved_at=summary.last_saved_at,
        has_render_scene=summary.has_render_scene,
    )


def _to_saved_response(record: StoredProjectRecord) -> SavedProjectResponse:
    summary = StoredProjectSummary(
        project_id=record.metadata.get("project_id", record.project.id),
        name=record.metadata.get("name", record.project.metadata.name),
        description=record.metadata.get("description", record.project.metadata.description),
        created_at=record.metadata.get("created_at"),
        updated_at=record.metadata.get("updated_at"),
        last_saved_at=record.metadata.get("last_saved_at"),
        has_render_scene=bool(record.metadata.get("has_render_scene", record.scene is not None)),
    )
    return SavedProjectResponse(
        project=record.project,
        scene=record.scene,
        metadata=_to_saved_metadata(summary),
        history=record.history,
    )


def create_router(
    project_service: ProjectService,
    scene_service: SceneService,
    authoring_graph: Any,
    compilation_graph: Any,
) -> APIRouter:
    """Factory that creates the router with injected dependencies.

    Args:
        project_service: Project CRUD operations.
        scene_service: Direct scene compilation (no LangGraph).
        authoring_graph: Compiled LangGraph for project authoring (WF1).
        compilation_graph: Compiled LangGraph for geometry compilation (WF2).
    """

    r = APIRouter(prefix="/api")

    @r.post("/projects", response_model=ProjectResponse)
    async def create_project(req: CreateProjectRequest) -> ProjectResponse:
        """Create a new project with a default building."""
        project = await project_service.create_project(
            name=req.name, description=req.description
        )
        return ProjectResponse(project=project)

    @r.post("/projects/{project_id}/save", response_model=SavedProjectResponse)
    async def save_project(project_id: str, req: SaveProjectRequest) -> SavedProjectResponse:
        """Persist the current project schema and optional render scene."""
        if req.project.id != project_id:
            raise HTTPException(status_code=400, detail="Project ID mismatch")

        errors = await project_service.save_project_bundle(req.project, req.scene)
        if errors:
            raise HTTPException(status_code=400, detail={"validation_errors": errors})

        record = await project_service.get_project_bundle(project_id)
        if record is None:
            raise HTTPException(status_code=500, detail="Project save failed")

        return _to_saved_response(record)

    @r.get("/projects/{project_id}", response_model=SavedProjectResponse)
    async def get_project(project_id: str) -> SavedProjectResponse:
        """Retrieve a persisted project and its saved render scene by ID."""
        record = await project_service.get_project_bundle(project_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return _to_saved_response(record)

    @r.post("/projects/{project_id}/turn", response_model=TurnResponse)
    async def update_project(project_id: str, req: UpdateProjectRequest) -> TurnResponse:
        """Process a user prompt to update the project.

        Runs WF1 (project authoring) → WF2 (geometry compilation) and returns
        the assistant's response, updated project, and compiled scene.
        """
        project = await project_service.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        # --- WF1: Project Authoring ---
        authoring_input = ProjectAuthoringState(
            user_prompt=req.prompt,
            project=project,
        )
        authoring_result = await authoring_graph.ainvoke(authoring_input.model_dump())

        updated_project = project  # fallback
        if authoring_result.get("updated_project"):
            from ..models.project import ProjectJSON
            updated_project = ProjectJSON.model_validate(authoring_result["updated_project"])

        response_text = authoring_result.get("response_text", "Project updated.")

        # --- WF2: Geometry Compilation ---
        compilation_input = GeometryCompilationState(project=updated_project)
        compilation_result = await compilation_graph.ainvoke(compilation_input.model_dump())

        from ..models.scene import SceneJSON
        scene = SceneJSON.model_validate(compilation_result["scene"])

        compilation_errors = compilation_result.get("validation_errors", [])
        if compilation_errors:
            logger.warning("Scene compilation had validation warnings: %s", compilation_errors)

        save_errors = await project_service.save_project_bundle(updated_project, scene)
        if save_errors:
            raise HTTPException(status_code=400, detail={"validation_errors": save_errors})

        return TurnResponse(
            assistant_message=response_text,
            project=updated_project,
            scene=scene,
        )

    @r.post("/projects/{project_id}/compile", response_model=SceneResponse)
    async def compile_scene(project_id: str) -> SceneResponse:
        """Compile the current project into a render scene.

        Uses WF2 (geometry compilation graph) for consistency.
        """
        project = await project_service.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        compilation_input = GeometryCompilationState(project=project)
        compilation_result = await compilation_graph.ainvoke(compilation_input.model_dump())

        from ..models.scene import SceneJSON
        scene = SceneJSON.model_validate(compilation_result["scene"])
        await project_service.save_render_scene(project_id, scene)

        return SceneResponse(scene=scene)

    @r.get("/projects", response_model=list[SavedProjectMetadata])
    async def list_projects() -> list[SavedProjectMetadata]:
        """List all saved projects with lightweight metadata."""
        return [_to_saved_metadata(summary) for summary in await project_service.list_projects()]

    return r
