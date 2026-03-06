"""Scene service — orchestrates project → scene compilation."""

from __future__ import annotations

from ..compiler.scene_compiler import SceneCompilerBase
from ..models.project import ProjectJSON
from ..models.scene import SceneJSON


class SceneService:
    def __init__(self, compiler: SceneCompilerBase) -> None:
        self._compiler = compiler

    async def compile(self, project: ProjectJSON) -> SceneJSON:
        """Compile a validated project into a render scene."""
        return await self._compiler.compile(project)
