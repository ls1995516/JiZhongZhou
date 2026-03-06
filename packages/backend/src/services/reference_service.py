"""Reference library service — orchestrates reusable curated examples."""

from __future__ import annotations

import uuid
from datetime import datetime

from ..models.project import ProjectJSON
from ..models.reference import ReferenceMetadata
from ..services.project_service import ProjectService
from ..storage.reference_store import ReferenceStore, StoredReferenceRecord


class ReferenceService:
    def __init__(
        self,
        store: ReferenceStore,
        project_service: ProjectService,
    ) -> None:
        self._store = store
        self._project_service = project_service

    async def list_references(self) -> list[ReferenceMetadata]:
        return await self._store.list_references()

    async def get_reference(self, reference_id: str) -> StoredReferenceRecord | None:
        return await self._store.load_reference(reference_id)

    async def create_reference_from_project(
        self,
        metadata: ReferenceMetadata,
        source_project_id: str,
    ) -> StoredReferenceRecord:
        project = await self._project_service.get_project(source_project_id)
        if project is None:
            raise FileNotFoundError(f"Project {source_project_id} not found")
        return await self._store.save_reference(metadata, project)

    async def instantiate_reference(self, reference_id: str) -> ProjectJSON | None:
        record = await self._store.load_reference(reference_id)
        if record is None:
            return None

        now = datetime.utcnow()
        project = record.project.model_copy(deep=True)
        project.id = str(uuid.uuid4())
        project.metadata.created_at = now
        project.metadata.updated_at = now

        errors = await self._project_service.save_project(project)
        if errors:
            raise ValueError(f"Reference project failed validation: {errors}")

        return project
