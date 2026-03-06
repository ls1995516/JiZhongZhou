"""Default material assignment by semantic type."""

from __future__ import annotations

from ..models.scene import Material

# Mapping from semantic_type to default material
DEFAULT_MATERIALS: dict[str, Material] = {
    "floor-slab": Material(color="#888888", roughness=0.9),
    "wall": Material(color="#e0e0e0", roughness=0.85),
    "window": Material(color="#4a90d9", opacity=0.4, roughness=0.3),
    "door": Material(color="#8B4513", roughness=0.7),
    "roof": Material(color="#a05030", roughness=0.8),
    "ground": Material(color="#4a7c4f", roughness=1.0),
}


def get_material(semantic_type: str) -> Material:
    """Return the default material for a given semantic type, or a gray fallback."""
    return DEFAULT_MATERIALS.get(semantic_type, Material())
