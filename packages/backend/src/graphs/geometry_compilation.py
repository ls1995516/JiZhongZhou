"""LangGraph workflow: Geometry Compilation.

Responsible for converting validated ProjectJSON into SceneJSON.

Graph structure:
  START → decompose → compile → agent_refine → assemble → validate_scene → END
"""

from __future__ import annotations

import logging
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
from ..services.agent_provider import CodingAgentProvider
from ..validators.scene_validator import SceneValidator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Node factory — closures over injected dependencies
# ---------------------------------------------------------------------------

def make_nodes(
    agent: CodingAgentProvider,
    scene_validator: SceneValidator,
) -> dict[str, Any]:
    """Create node functions with injected dependencies."""

    async def decompose(state: GeometryCompilationState) -> dict[str, Any]:
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

        logger.info("Decomposed project into %d compile units", len(units))
        return {"compile_units": units}

    async def compile_geometry(state: GeometryCompilationState) -> dict[str, Any]:
        """Deterministic compilation of each unit into scene objects."""
        floors_by_id = {f.id: f for f in state.project.building.floors}
        floor_children: dict[str, list[SceneObject]] = {}

        for unit in state.compile_units:
            try:
                if unit.element_type == "floor_slab":
                    floor = floors_by_id[unit.element_id]
                    obj = compile_floor_slab(floor)
                    floor_children.setdefault(floor.id, []).append(obj)

                elif unit.element_type == "wall":
                    floor = floors_by_id[unit.data["floor_id"]]
                    wall = next(w for w in floor.walls if w.id == unit.element_id)
                    obj = compile_wall(wall, floor)
                    floor_children.setdefault(floor.id, []).append(obj)

                elif unit.element_type == "opening":
                    floor = floors_by_id[unit.data["floor_id"]]
                    wall_data = unit.data["wall"]
                    wall = next(w for w in floor.walls if w.id == wall_data["id"])
                    opening = next(o for o in wall.openings if o.id == unit.element_id)
                    obj = compile_opening(opening, wall, floor)
                    floor_children.setdefault(floor.id, []).append(obj)

                else:
                    logger.warning("Unknown compile unit type: %s", unit.element_type)

            except Exception as e:
                logger.error("Failed to compile unit %s: %s", unit.element_id, e)
                return {"validation_errors": [f"Compilation failed for {unit.element_id}: {e}"]}

        objects: list[SceneObject] = []
        for floor in state.project.building.floors:
            group = SceneObject(
                id=f"floor-group-{floor.id}",
                source_id=floor.id,
                type=SceneObjectType.group,
                children=floor_children.get(floor.id, []),
            )
            objects.append(group)

        scene = SceneJSON(
            metadata={
                "source_project_id": state.project.id,
                "compiled_at": datetime.utcnow().isoformat(),
            },
            scene=SceneData(objects=objects),
        )

        logger.info("Compiled %d floor groups with %d total objects",
                     len(objects), sum(len(c) for c in floor_children.values()))
        return {"scene": scene}

    async def agent_refine(state: GeometryCompilationState) -> dict[str, Any]:
        """Agent-assisted refinement for complex geometry.

        MVP: passthrough. This node is the extension point where a coding agent
        can generate custom geometry for non-rectilinear shapes.

        TODO: When activated, the agent would be invoked like:
            result = await agent.invoke(
                system_prompt="You are a geometry expert. Generate Three.js-compatible "
                              "vertices and indices for the following shape...",
                user_request=f"Generate geometry for: {complex_element}",
                context={"element": element_data, "surrounding": neighbor_data},
            )
        Then parse result.json_output as custom vertices/indices and inject
        into the scene as SceneObjects with GeometryPrimitive.custom.
        """
        return {}

    async def assemble(state: GeometryCompilationState) -> dict[str, Any]:
        """Final assembly — add lights, camera, finalize scene."""
        if state.scene is None:
            return {"validation_errors": ["No scene produced by compile step."]}

        camera = _compute_camera(state)

        scene = state.scene.model_copy(deep=True)
        scene.scene.lights = [
            Light(type=LightType.ambient, intensity=0.4),
            Light(type=LightType.directional, intensity=0.8, position=(10, 20, 10)),
        ]
        scene.scene.camera = camera

        return {"scene": scene}

    async def validate_scene(state: GeometryCompilationState) -> dict[str, Any]:
        """Validate the final scene output."""
        if state.scene is None:
            return {"validation_errors": ["No scene to validate."]}

        errors = scene_validator.validate(state.scene)
        if errors:
            logger.warning("Scene validation errors: %s", errors)
        return {"validation_errors": errors}

    return {
        "decompose": decompose,
        "compile": compile_geometry,
        "agent_refine": agent_refine,
        "assemble": assemble,
        "validate_scene": validate_scene,
    }


def _compute_camera(state: GeometryCompilationState) -> Camera:
    """Place camera to frame the building based on its bounding box."""
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


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_geometry_compilation_graph(
    agent: CodingAgentProvider,
    scene_validator: SceneValidator,
) -> Any:
    """Build and compile the geometry compilation LangGraph.

    Dependencies are injected so the graph is testable and vendor-agnostic.
    """
    nodes = make_nodes(agent, scene_validator)

    graph = StateGraph(GeometryCompilationState)

    graph.add_node("decompose", nodes["decompose"])
    graph.add_node("compile", nodes["compile"])
    graph.add_node("agent_refine", nodes["agent_refine"])
    graph.add_node("assemble", nodes["assemble"])
    graph.add_node("validate_scene", nodes["validate_scene"])

    graph.set_entry_point("decompose")
    graph.add_edge("decompose", "compile")
    graph.add_edge("compile", "agent_refine")
    graph.add_edge("agent_refine", "assemble")
    graph.add_edge("assemble", "validate_scene")
    graph.add_edge("validate_scene", END)

    return graph.compile()
