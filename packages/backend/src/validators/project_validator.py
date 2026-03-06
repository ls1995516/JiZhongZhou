"""Deterministic validation of ProjectJSON beyond what Pydantic enforces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.project import ProjectJSON


class ProjectValidator(ABC):
    """Abstract validator interface.

    Returns a list of human-readable error strings. Empty list = valid.
    """

    @abstractmethod
    def validate(self, project: ProjectJSON) -> list[str]: ...


class DefaultProjectValidator(ProjectValidator):
    """MVP validator — checks structural invariants that Pydantic can't express."""

    def validate(self, project: ProjectJSON) -> list[str]:
        errors: list[str] = []

        if not project.building.floors:
            errors.append("Building must have at least one floor.")

        seen_floor_ids: set[str] = set()
        for floor in project.building.floors:
            if floor.id in seen_floor_ids:
                errors.append(f"Duplicate floor id: {floor.id}")
            seen_floor_ids.add(floor.id)

            if floor.height <= 0:
                errors.append(f"Floor {floor.id}: height must be positive, got {floor.height}")

            if len(floor.outline.points) < 3:
                errors.append(f"Floor {floor.id}: outline must have >= 3 points")

            seen_wall_ids: set[str] = set()
            for wall in floor.walls:
                if wall.id in seen_wall_ids:
                    errors.append(f"Floor {floor.id}: duplicate wall id {wall.id}")
                seen_wall_ids.add(wall.id)

                if wall.start == wall.end:
                    errors.append(f"Wall {wall.id}: start and end points are identical")

                for opening in wall.openings:
                    if opening.position < 0 or opening.position > 1:
                        errors.append(
                            f"Opening {opening.id} in wall {wall.id}: "
                            f"position must be in [0,1], got {opening.position}"
                        )

        return errors
