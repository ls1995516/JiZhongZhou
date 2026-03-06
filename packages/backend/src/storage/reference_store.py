"""Reference library persistence — abstract interface + local file-based implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ..models.project import ProjectJSON
from ..models.reference import ReferenceMetadata


@dataclass
class StoredReferenceRecord:
    metadata: ReferenceMetadata
    project: ProjectJSON


class ReferenceStore(ABC):
    """Abstract interface for reusable reference persistence."""

    @abstractmethod
    async def list_references(self) -> list[ReferenceMetadata]: ...

    @abstractmethod
    async def load_reference(self, reference_id: str) -> StoredReferenceRecord | None: ...

    @abstractmethod
    async def save_reference(
        self,
        metadata: ReferenceMetadata,
        project: ProjectJSON,
    ) -> StoredReferenceRecord: ...


class FileReferenceStore(ReferenceStore):
    """Stores references as curated folders on disk.

    Layout:
      <base_dir>/<reference_id>/
        - metadata.json
        - project_schema.json
    """

    def __init__(self, base_dir: str | Path = "data/references") -> None:
        self._dir = Path(base_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _reference_dir(self, reference_id: str) -> Path:
        return self._dir / reference_id

    def _metadata_path(self, reference_id: str) -> Path:
        return self._reference_dir(reference_id) / "metadata.json"

    def _project_schema_path(self, reference_id: str) -> Path:
        return self._reference_dir(reference_id) / "project_schema.json"

    async def list_references(self) -> list[ReferenceMetadata]:
        references: list[ReferenceMetadata] = []
        for reference_dir in sorted(self._dir.iterdir()):
            if not reference_dir.is_dir():
                continue

            metadata_path = self._metadata_path(reference_dir.name)
            if not metadata_path.exists():
                continue

            references.append(ReferenceMetadata.model_validate_json(metadata_path.read_text()))

        return references

    async def load_reference(self, reference_id: str) -> StoredReferenceRecord | None:
        metadata_path = self._metadata_path(reference_id)
        project_path = self._project_schema_path(reference_id)
        if not metadata_path.exists() or not project_path.exists():
            return None

        metadata = ReferenceMetadata.model_validate_json(metadata_path.read_text())
        project = ProjectJSON.model_validate_json(project_path.read_text())
        return StoredReferenceRecord(metadata=metadata, project=project)

    async def save_reference(
        self,
        metadata: ReferenceMetadata,
        project: ProjectJSON,
    ) -> StoredReferenceRecord:
        reference_dir = self._reference_dir(metadata.id)
        reference_dir.mkdir(parents=True, exist_ok=True)

        self._metadata_path(metadata.id).write_text(
            metadata.model_dump_json(indent=2),
            encoding="utf-8",
        )
        self._project_schema_path(metadata.id).write_text(
            project.model_dump_json(indent=2),
            encoding="utf-8",
        )

        return StoredReferenceRecord(metadata=metadata, project=project)
