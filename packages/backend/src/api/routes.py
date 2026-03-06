"""FastAPI route definitions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models.api import (
    CreateProjectRequest,
    ProjectResponse,
    SceneResponse,
    TurnResponse,
    UpdateProjectRequest,
)
from ..services.project_service import ProjectService
from ..services.scene_service import SceneService

router = APIRouter(prefix="/api")


def create_router(project_service: ProjectService, scene_service: SceneService) -> APIRouter:
    """Factory that creates the router with injected service dependencies."""

    r = APIRouter(prefix="/api")

    @r.post("/projects", response_model=ProjectResponse)
    async def create_project(req: CreateProjectRequest) -> ProjectResponse:
        """Create a new project with a default building."""
        project = await project_service.create_project(
            name=req.name, description=req.description
        )
        return ProjectResponse(project=project)

    @r.get("/projects/{project_id}", response_model=ProjectResponse)
    async def get_project(project_id: str) -> ProjectResponse:
        """Retrieve a project by ID."""
        project = await project_service.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return ProjectResponse(project=project)

    @r.post("/projects/{project_id}/turn", response_model=TurnResponse)
    async def update_project(project_id: str, req: UpdateProjectRequest) -> TurnResponse:
        """Process a user prompt to update the project.

        Runs the project authoring LangGraph workflow, then compiles the
        updated project into a render scene.
        """
        project = await project_service.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        # TODO: Invoke project_authoring_graph with (project, req.prompt)
        # For now, return the project unchanged with a stub message.
        scene = await scene_service.compile(project)

        return TurnResponse(
            assistant_message="[stub] Authoring graph not yet wired. Project unchanged.",
            project=project,
            scene=scene,
        )

    @r.post("/projects/{project_id}/compile", response_model=SceneResponse)
    async def compile_scene(project_id: str) -> SceneResponse:
        """Compile the current project into a render scene (without LLM)."""
        project = await project_service.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        scene = await scene_service.compile(project)
        return SceneResponse(scene=scene)

    @r.get("/projects", response_model=list[str])
    async def list_projects() -> list[str]:
        """List all project IDs."""
        return await project_service.list_projects()

    return r
