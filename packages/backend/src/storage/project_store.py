"""Project persistence — abstract interface + local file-based implementation."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models.project import ProjectJSON
from ..models.scene import SceneJSON


@dataclass
class StoredProjectSummary:
    project_id: str
    name: str
    description: str | None
    created_at: str | None
    updated_at: str | None
    last_saved_at: str | None
    has_render_scene: bool


@dataclass
class StoredProjectRecord:
    project: ProjectJSON
    scene: SceneJSON | None
    metadata: dict[str, Any]
    history: list[dict[str, Any]]


class ProjectStore(ABC):
    """Abstract interface for filesystem-backed project persistence."""

    @abstractmethod
    async def save_project_schema(self, project: ProjectJSON) -> None: ...

    @abstractmethod
    async def save_render_scene(self, project_id: str, scene: SceneJSON) -> None: ...

    @abstractmethod
    async def save_bundle(self, project: ProjectJSON, scene: SceneJSON | None) -> None: ...

    @abstractmethod
    async def load_project_schema(self, project_id: str) -> ProjectJSON | None: ...

    @abstractmethod
    async def load_render_scene(self, project_id: str) -> SceneJSON | None: ...

    @abstractmethod
    async def load_bundle(self, project_id: str) -> StoredProjectRecord | None: ...

    @abstractmethod
    async def delete(self, project_id: str) -> bool: ...

    @abstractmethod
    async def list_projects(self) -> list[StoredProjectSummary]: ...


class FileProjectStore(ProjectStore):
    """Stores each project as a directory with separate schema and scene files.

    Layout:
      <base_dir>/<project_id>/
        - project_schema.json
        - render_scene.json
        - metadata.json
        - history.json
    """

    def __init__(self, base_dir: str | Path = "data/projects") -> None:
        self._dir = Path(base_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _project_dir(self, project_id: str) -> Path:
        return self._dir / project_id

    def _project_schema_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "project_schema.json"

    def _render_scene_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "render_scene.json"

    def _metadata_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "metadata.json"

    def _history_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "history.json"

    def _ensure_project_dir(self, project_id: str) -> Path:
        project_dir = self._project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def _write_json(self, path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _read_json_object(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _read_json_array(self, path: Path) -> list[dict[str, Any]]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _build_metadata(
        self,
        project: ProjectJSON,
        existing: dict[str, Any] | None = None,
        *,
        has_render_scene: bool,
    ) -> dict[str, Any]:
        now = datetime.utcnow().isoformat()
        return {
            "project_id": project.id,
            "name": project.metadata.name,
            "description": project.metadata.description,
            "created_at": existing.get("created_at") if existing else project.metadata.created_at.isoformat(),
            "updated_at": project.metadata.updated_at.isoformat(),
            "last_saved_at": now,
            "has_render_scene": has_render_scene,
        }

    def _append_history(
        self,
        project: ProjectJSON,
        scene: SceneJSON | None,
    ) -> None:
        history_path = self._history_path(project.id)
        history = self._read_json_array(history_path) if history_path.exists() else []
        history.append(
            {
                "saved_at": datetime.utcnow().isoformat(),
                "project_version": project.version,
                "scene_version": scene.version if scene is not None else None,
                "has_render_scene": scene is not None,
            }
        )
        self._write_json(history_path, history)

    async def save_project_schema(self, project: ProjectJSON) -> None:
        self._ensure_project_dir(project.id)
        existing_metadata = None
        metadata_path = self._metadata_path(project.id)
        if metadata_path.exists():
            existing_metadata = self._read_json_object(metadata_path)

        self._project_schema_path(project.id).write_text(
            project.model_dump_json(indent=2),
            encoding="utf-8",
        )
        metadata = self._build_metadata(
            project,
            existing_metadata,
            has_render_scene=self._render_scene_path(project.id).exists(),
        )
        self._write_json(metadata_path, metadata)

    async def save_render_scene(self, project_id: str, scene: SceneJSON) -> None:
        project = await self.load_project_schema(project_id)
        if project is None:
            raise FileNotFoundError(f"Project {project_id} does not exist")

        self._ensure_project_dir(project_id)
        self._render_scene_path(project_id).write_text(
            scene.model_dump_json(indent=2),
            encoding="utf-8",
        )

        metadata_path = self._metadata_path(project_id)
        existing_metadata = self._read_json_object(metadata_path) if metadata_path.exists() else None
        metadata = self._build_metadata(project, existing_metadata, has_render_scene=True)
        self._write_json(metadata_path, metadata)

    async def save_bundle(self, project: ProjectJSON, scene: SceneJSON | None) -> None:
        await self.save_project_schema(project)
        if scene is not None:
            await self.save_render_scene(project.id, scene)
        self._append_history(project, scene)

    async def load_project_schema(self, project_id: str) -> ProjectJSON | None:
        path = self._project_schema_path(project_id)
        if not path.exists():
            return None
        raw = path.read_text(encoding="utf-8")
        return ProjectJSON.model_validate_json(raw)

    async def load_render_scene(self, project_id: str) -> SceneJSON | None:
        path = self._render_scene_path(project_id)
        if not path.exists():
            return None
        raw = path.read_text(encoding="utf-8")
        return SceneJSON.model_validate_json(raw)

    async def load_bundle(self, project_id: str) -> StoredProjectRecord | None:
        project = await self.load_project_schema(project_id)
        if project is None:
            return None

        scene = await self.load_render_scene(project_id)
        metadata_path = self._metadata_path(project_id)
        history_path = self._history_path(project_id)
        metadata = self._read_json_object(metadata_path) if metadata_path.exists() else {}
        history = self._read_json_array(history_path) if history_path.exists() else []
        return StoredProjectRecord(
            project=project,
            scene=scene,
            metadata=metadata,
            history=history,
        )

    async def delete(self, project_id: str) -> bool:
        project_dir = self._project_dir(project_id)
        if project_dir.exists():
            for path in project_dir.iterdir():
                path.unlink()
            project_dir.rmdir()
            return True
        return False

    async def list_projects(self) -> list[StoredProjectSummary]:
        summaries: list[StoredProjectSummary] = []

        for project_dir in self._dir.iterdir():
            if not project_dir.is_dir():
                continue

            project_id = project_dir.name
            metadata_path = self._metadata_path(project_id)
            if metadata_path.exists():
                metadata = self._read_json_object(metadata_path)
                summaries.append(
                    StoredProjectSummary(
                        project_id=project_id,
                        name=metadata.get("name", project_id),
                        description=metadata.get("description"),
                        created_at=metadata.get("created_at"),
                        updated_at=metadata.get("updated_at"),
                        last_saved_at=metadata.get("last_saved_at"),
                        has_render_scene=bool(metadata.get("has_render_scene")),
                    )
                )
                continue

            project = await self.load_project_schema(project_id)
            if project is None:
                continue

            summaries.append(
                StoredProjectSummary(
                    project_id=project_id,
                    name=project.metadata.name,
                    description=project.metadata.description,
                    created_at=project.metadata.created_at.isoformat(),
                    updated_at=project.metadata.updated_at.isoformat(),
                    last_saved_at=None,
                    has_render_scene=self._render_scene_path(project_id).exists(),
                )
            )

        summaries.sort(key=lambda item: item.last_saved_at or item.updated_at or "", reverse=True)
        return summaries
