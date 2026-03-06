"""Deterministic validation of SceneJSON beyond what Pydantic enforces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.scene import SceneJSON, SceneObject


class SceneValidator(ABC):
    """Abstract scene validator. Returns list of error strings."""

    @abstractmethod
    def validate(self, scene: SceneJSON) -> list[str]: ...


class DefaultSceneValidator(SceneValidator):
    """MVP scene validator — checks structural invariants."""

    def validate(self, scene: SceneJSON) -> list[str]:
        errors: list[str] = []

        if not scene.scene.objects:
            errors.append("Scene has no objects.")

        seen_ids: set[str] = set()
        self._check_objects(scene.scene.objects, seen_ids, errors)

        if not scene.scene.lights:
            errors.append("Scene has no lights.")

        return errors

    def _check_objects(
        self,
        objects: list[SceneObject],
        seen_ids: set[str],
        errors: list[str],
    ) -> None:
        for obj in objects:
            if obj.id in seen_ids:
                errors.append(f"Duplicate scene object id: {obj.id}")
            seen_ids.add(obj.id)

            if obj.type == "mesh" and obj.geometry is None:
                errors.append(f"Mesh object {obj.id} has no geometry.")

            self._check_objects(obj.children, seen_ids, errors)
