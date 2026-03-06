"""Project service — orchestrates create / get / update operations."""

from __future__ import annotations

import uuid
from datetime import datetime

from ..models.project import BuildingInfo, Floor, Polygon, ProjectJSON, ProjectMetadata, Vector2
from ..models.scene import SceneJSON
from ..storage.project_store import ProjectStore, StoredProjectRecord, StoredProjectSummary
from ..validators.project_validator import ProjectValidator


class ProjectService:
    def __init__(self, store: ProjectStore, validator: ProjectValidator) -> None:
        self._store = store
        self._validator = validator

    async def create_project(self, name: str, description: str | None = None) -> ProjectJSON:
        """Create a new empty project with a single default floor."""
        project = ProjectJSON(
            id=str(uuid.uuid4()),
            metadata=ProjectMetadata(
                name=name,
                description=description,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            building=BuildingInfo(
                floors=[
                    Floor(
                        id="floor-1",
                        label="Ground Floor",
                        elevation=0,
                        height=3.0,
                        outline=Polygon(
                            points=[
                                Vector2(x=0, y=0),
                                Vector2(x=10, y=0),
                                Vector2(x=10, y=10),
                                Vector2(x=0, y=10),
                            ]
                        ),
                    )
                ]
            ),
        )

        errors = self._validator.validate(project)
        if errors:
            raise ValueError(f"Default project failed validation: {errors}")

        await self._store.save_project_schema(project)
        return project

    async def get_project(self, project_id: str) -> ProjectJSON | None:
        return await self._store.load_project_schema(project_id)

    async def get_project_bundle(self, project_id: str) -> StoredProjectRecord | None:
        return await self._store.load_bundle(project_id)

    async def save_project(self, project: ProjectJSON) -> list[str]:
        """Validate and save. Returns validation errors (empty = success)."""
        errors = self._validator.validate(project)
        if not errors:
            project.metadata.updated_at = datetime.utcnow()
            await self._store.save_project_schema(project)
        return errors

    async def save_project_bundle(
        self,
        project: ProjectJSON,
        scene: SceneJSON | None,
    ) -> list[str]:
        """Validate and save the project schema and optional render scene."""
        errors = self._validator.validate(project)
        if not errors:
            project.metadata.updated_at = datetime.utcnow()
            await self._store.save_bundle(project, scene)
        return errors

    async def save_render_scene(self, project_id: str, scene: SceneJSON) -> None:
        await self._store.save_render_scene(project_id, scene)

    async def list_projects(self) -> list[StoredProjectSummary]:
        return await self._store.list_projects()
