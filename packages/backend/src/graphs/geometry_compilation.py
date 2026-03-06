"""LangGraph workflow: Geometry Compilation.

Responsible for converting validated ProjectJSON into SceneJSON.

Graph structure:
  START → decompose → compile → [agent_refine] → assemble → END

In MVP, the agent_refine node is a passthrough. The deterministic compiler
handles all rectilinear geometry.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from langgraph.graph import END, StateGraph

from ..compiler.geometry import compile_floor_slab, compile_opening, compile_wall
from ..models.scene import (
    Camera,
    Light,
    LightType,
    SceneData,
    SceneJSON,
    SceneObject,
    SceneObjectType,
)
from ..models.state import CompileUnit, GeometryCompilationState


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

async def decompose_node(state: GeometryCompilationState) -> dict[str, Any]:
    """Split project into compilable units (floors, walls, openings)."""
    units: list[CompileUnit] = []

    for floor in state.project.building.floors:
        units.append(CompileUnit(
            element_type="floor_slab",
            element_id=floor.id,
            data=floor.model_dump(),
        ))
        for wall in floor.walls:
            units.append(CompileUnit(
                element_type="wall",
                element_id=wall.id,
                data={"wall": wall.model_dump(), "floor_id": floor.id},
            ))
            for opening in wall.openings:
                units.append(CompileUnit(
                    element_type="opening",
                    element_id=opening.id,
                    data={
                        "opening": opening.model_dump(),
                        "wall": wall.model_dump(),
                        "floor_id": floor.id,
                    },
                ))

    return {"compile_units": units}


async def compile_node(state: GeometryCompilationState) -> dict[str, Any]:
    """Deterministic compilation of each unit into scene objects."""
    objects: list[SceneObject] = []
    floors_by_id = {f.id: f for f in state.project.building.floors}

    # Group objects by floor
    floor_children: dict[str, list[SceneObject]] = {}

    for unit in state.compile_units:
        if unit.element_type == "floor_slab":
            from ..models.project import Floor
            floor = floors_by_id[unit.element_id]
            obj = compile_floor_slab(floor)
            floor_children.setdefault(floor.id, []).append(obj)

        elif unit.element_type == "wall":
            from ..models.project import Wall
            floor = floors_by_id[unit.data["floor_id"]]
            wall = next(w for w in floor.walls if w.id == unit.element_id)
            obj = compile_wall(wall, floor)
            floor_children.setdefault(floor.id, []).append(obj)

        elif unit.element_type == "opening":
            from ..models.project import Opening, Wall
            floor = floors_by_id[unit.data["floor_id"]]
            wall_data = unit.data["wall"]
            wall = next(w for w in floor.walls if w.id == wall_data["id"])
            opening = next(o for o in wall.openings if o.id == unit.element_id)
            obj = compile_opening(opening, wall, floor)
            floor_children.setdefault(floor.id, []).append(obj)

    for floor in state.project.building.floors:
        group = SceneObject(
            id=f"floor-group-{floor.id}",
            source_id=floor.id,
            type=SceneObjectType.group,
            children=floor_children.get(floor.id, []),
        )
        objects.append(group)

    # Build partial scene (lights/camera added in assemble)
    scene = SceneJSON(
        metadata={
            "source_project_id": state.project.id,
            "compiled_at": datetime.utcnow().isoformat(),
        },
        scene=SceneData(objects=objects),
    )
    return {"scene": scene}


async def agent_refine_node(state: GeometryCompilationState) -> dict[str, Any]:
    """Agent-assisted refinement for complex geometry.

    MVP: passthrough. This node is the extension point where a coding agent
    can generate custom geometry for non-rectilinear shapes.

    TODO: Invoke CodingAgentProvider when compile_node flags unsupported geometry.
    """
    return {}


async def assemble_node(state: GeometryCompilationState) -> dict[str, Any]:
    """Final assembly — add lights, camera, finalize scene."""
    if state.scene is None:
        return {"errors": ["No scene produced by compile step."]}

    # Compute camera from project bounds
    all_xs: list[float] = []
    all_ys: list[float] = []
    max_h = 0.0
    for floor in state.project.building.floors:
        for pt in floor.outline.points:
            all_xs.append(pt.x)
            all_ys.append(pt.y)
        top = floor.elevation + floor.height
        if top > max_h:
            max_h = top

    if all_xs:
        cx = (min(all_xs) + max(all_xs)) / 2
        cz = (min(all_ys) + max(all_ys)) / 2
        span = max(max(all_xs) - min(all_xs), max(all_ys) - min(all_ys), max_h)
        dist = span * 1.5
        camera = Camera(
            position=(cx + dist, max_h + dist * 0.5, cz + dist),
            target=(cx, max_h / 2, cz),
        )
    else:
        camera = Camera()

    scene = state.scene
    scene.scene.lights = [
        Light(type=LightType.ambient, intensity=0.4),
        Light(type=LightType.directional, intensity=0.8, position=(10, 20, 10)),
    ]
    scene.scene.camera = camera

    return {"scene": scene}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_geometry_compilation_graph() -> StateGraph:
    """Build and return the compiled geometry compilation LangGraph."""

    graph = StateGraph(GeometryCompilationState)

    graph.add_node("decompose", decompose_node)
    graph.add_node("compile", compile_node)
    graph.add_node("agent_refine", agent_refine_node)
    graph.add_node("assemble", assemble_node)

    graph.set_entry_point("decompose")
    graph.add_edge("decompose", "compile")
    graph.add_edge("compile", "agent_refine")
    graph.add_edge("agent_refine", "assemble")
    graph.add_edge("assemble", END)

    return graph.compile()
