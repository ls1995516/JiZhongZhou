"""Project persistence — abstract interface + local file-based implementation."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from ..models.project import ProjectJSON


class ProjectStore(ABC):
    """Abstract interface for project persistence.

    Implementations must support CRUD by project ID.
    """

    @abstractmethod
    async def save(self, project: ProjectJSON) -> None: ...

    @abstractmethod
    async def load(self, project_id: str) -> ProjectJSON | None: ...

    @abstractmethod
    async def delete(self, project_id: str) -> bool: ...

    @abstractmethod
    async def list_ids(self) -> list[str]: ...


class FileProjectStore(ProjectStore):
    """Stores each project as a JSON file on disk.

    Layout: <base_dir>/<project_id>.json
    """

    def __init__(self, base_dir: str | Path = "data/projects") -> None:
        self._dir = Path(base_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, project_id: str) -> Path:
        return self._dir / f"{project_id}.json"

    async def save(self, project: ProjectJSON) -> None:
        path = self._path(project.id)
        path.write_text(project.model_dump_json(indent=2), encoding="utf-8")

    async def load(self, project_id: str) -> ProjectJSON | None:
        path = self._path(project_id)
        if not path.exists():
            return None
        raw = path.read_text(encoding="utf-8")
        return ProjectJSON.model_validate_json(raw)

    async def delete(self, project_id: str) -> bool:
        path = self._path(project_id)
        if path.exists():
            path.unlink()
            return True
        return False

    async def list_ids(self) -> list[str]:
        return [p.stem for p in self._dir.glob("*.json")]
