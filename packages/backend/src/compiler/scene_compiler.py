"""SceneCompiler — converts validated ProjectJSON into SceneJSON deterministically."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ..models.project import ProjectJSON
from ..models.scene import (
    Camera,
    Light,
    LightType,
    SceneData,
    SceneJSON,
    SceneObject,
    SceneObjectType,
)
from .geometry import compile_floor_slab, compile_opening, compile_wall


class SceneCompilerBase(ABC):
    """Abstract interface for scene compilation."""

    @abstractmethod
    async def compile(self, project: ProjectJSON) -> SceneJSON: ...


class DefaultSceneCompiler(SceneCompilerBase):
    """Deterministic compiler that converts project elements to scene primitives.

    This handles rectilinear buildings entirely with box primitives.
    A future agent-assisted compiler can extend this for complex geometry.
    """

    async def compile(self, project: ProjectJSON) -> SceneJSON:
        objects: list[SceneObject] = []

        for floor in project.building.floors:
            floor_group_children: list[SceneObject] = []

            # Floor slab
            floor_group_children.append(compile_floor_slab(floor))

            # Walls + openings
            for wall in floor.walls:
                floor_group_children.append(compile_wall(wall, floor))
                for opening in wall.openings:
                    floor_group_children.append(compile_opening(opening, wall, floor))

            floor_group = SceneObject(
                id=f"floor-group-{floor.id}",
                source_id=floor.id,
                type=SceneObjectType.group,
                children=floor_group_children,
            )
            objects.append(floor_group)

        scene = SceneJSON(
            metadata={
                "source_project_id": project.id,
                "compiled_at": datetime.utcnow().isoformat(),
            },
            scene=SceneData(
                objects=objects,
                lights=[
                    Light(type=LightType.ambient, intensity=0.4),
                    Light(type=LightType.directional, intensity=0.8, position=(10, 20, 10)),
                ],
                camera=self._compute_camera(project),
            ),
        )
        return scene

    def _compute_camera(self, project: ProjectJSON) -> Camera:
        """Place camera to frame the building based on its bounding box."""
        all_xs: list[float] = []
        all_ys: list[float] = []
        max_h = 0.0

        for floor in project.building.floors:
            for pt in floor.outline.points:
                all_xs.append(pt.x)
                all_ys.append(pt.y)
            top = floor.elevation + floor.height
            if top > max_h:
                max_h = top

        if not all_xs:
            return Camera()

        cx = (min(all_xs) + max(all_xs)) / 2
        cz = (min(all_ys) + max(all_ys)) / 2
        span = max(max(all_xs) - min(all_xs), max(all_ys) - min(all_ys), max_h)
        dist = span * 1.5

        return Camera(
            position=(cx + dist, max_h + dist * 0.5, cz + dist),
            target=(cx, max_h / 2, cz),
        )
