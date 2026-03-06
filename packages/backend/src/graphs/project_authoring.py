"""LangGraph workflow: Project Authoring.

Responsible for interpreting user intent and creating/updating ProjectJSON.

Graph structure:
  START → parse_request → agent_worker → validate → persist
            │                              │ (fail)
            │ (clarify)                    └→ agent_worker (retry, up to MAX_RETRIES)
            └→ respond ←───── persist ◄────┘
                  │
                 END
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langgraph.graph import END, StateGraph

from ..models.project import ProjectJSON
from ..models.state import AuthorPlan, ProjectAuthoringState
from ..services.agent_provider import CodingAgentProvider
from ..storage.project_store import ProjectStore
from ..validators.project_validator import ProjectValidator

logger = logging.getLogger(__name__)

MAX_RETRIES = 2

# ---------------------------------------------------------------------------
# System prompt template for the project authoring agent
# ---------------------------------------------------------------------------

PROJECT_AUTHOR_SYSTEM_PROMPT = """\
You are a building design assistant. Your job is to generate or update a \
ProjectJSON document based on the user's natural-language description.

RULES:
- Output ONLY valid JSON matching the ProjectJSON schema.
- Wrap your JSON output in ```json ... ``` fences.
- All dimensions are in meters.
- Floor IDs must be unique strings (e.g. "floor-1", "floor-2").
- Wall IDs must be unique within a floor.
- Opening positions are normalized [0, 1] along the wall.
- Preserve existing elements the user did not ask to change.
- If the user's request is unclear, explain what you need in plain text \
  (no JSON) and the system will treat it as a clarification.

SCHEMA SUMMARY:
{schema_summary}

CURRENT PROJECT:
{current_project}
"""

SCHEMA_SUMMARY = """\
ProjectJSON:
  version: str, id: str, metadata: {name, description, created_at, updated_at}
  site: {dimensions: {x, y}, elevation}
  building: {floors: Floor[], roof_type: "flat"|"gable"|"hip"}

Floor:
  id, label?, elevation (meters), height (floor-to-floor meters)
  outline: {points: [{x, y}, ...]}  (min 3 points)
  walls: Wall[], rooms: Room[]

Wall:
  id, start: {x, y}, end: {x, y}, thickness (default 0.2)
  openings: Opening[]

Opening:
  id, type: "door"|"window", position: 0..1, width, height, sill_height

Room:
  id, label, outline: {points: [...]}, function?
"""


# ---------------------------------------------------------------------------
# Graph node factory — closures over injected dependencies
# ---------------------------------------------------------------------------

def make_nodes(
    agent: CodingAgentProvider,
    validator: ProjectValidator,
    store: ProjectStore,
) -> dict[str, Any]:
    """Create node functions with injected dependencies.

    This avoids global state and makes the graph testable.
    """

    async def parse_request(state: ProjectAuthoringState) -> dict[str, Any]:
        """Analyze user prompt and decide: create / edit / clarify."""
        prompt = state.user_prompt.strip().lower()

        if state.project is None:
            plan = AuthorPlan.create
        elif any(
            word in prompt
            for word in ["what", "how", "explain", "why", "?", "help"]
        ):
            # Simple heuristic for clarification intent.
            # TODO: Replace with an LLM classifier call via the agent provider
            # for more accurate intent detection. E.g.:
            #   result = await agent.invoke(
            #       system_prompt="Classify intent as create/edit/clarify",
            #       user_request=state.user_prompt,
            #   )
            plan = AuthorPlan.clarify
        else:
            plan = AuthorPlan.edit

        logger.info("parse_request: plan=%s for prompt=%r", plan.value, state.user_prompt[:80])
        return {"plan": plan}

    async def agent_worker(state: ProjectAuthoringState) -> dict[str, Any]:
        """Invoke the coding-agent provider to generate/update ProjectJSON.

        The agent receives:
        - System prompt with schema and current project
        - The user's request
        - Structured context with the current project dict

        It returns an AgentResult with explanation + JSON output.
        """
        current_project_str = (
            state.project.model_dump_json(indent=2) if state.project else "null (no project yet)"
        )

        # Include validation errors from previous retry, if any
        user_request = state.user_prompt
        if state.validation_errors:
            error_feedback = "\n".join(f"- {e}" for e in state.validation_errors)
            user_request = (
                f"{state.user_prompt}\n\n"
                f"[SYSTEM] Your previous output had validation errors. Fix them:\n"
                f"{error_feedback}"
            )

        system_prompt = PROJECT_AUTHOR_SYSTEM_PROMPT.format(
            schema_summary=SCHEMA_SUMMARY,
            current_project=current_project_str,
        )

        context = {
            "project": state.project.model_dump() if state.project else None,
            "plan": state.plan.value if state.plan else "create",
        }

        # TODO: When a real CodingAgentProvider (e.g. AnthropicAgentProvider) is
        # connected, this call will send the prompt to an LLM which will:
        # 1. Read the current project JSON
        # 2. Understand the user's spatial/architectural intent
        # 3. Generate a complete updated ProjectJSON
        # The mock provider passes the project through unchanged.
        result = await agent.invoke(
            system_prompt=system_prompt,
            user_request=user_request,
            context=context,
        )

        # Try to parse the agent's JSON output into a ProjectJSON
        updated_project = state.project
        if result.json_output is not None:
            try:
                updated_project = ProjectJSON.model_validate(result.json_output)
            except Exception as e:
                logger.warning("Agent JSON output failed Pydantic validation: %s", e)
                return {
                    "validation_errors": [f"Agent output is not valid ProjectJSON: {e}"],
                    "retry_count": state.retry_count + 1,
                    "response_text": result.raw_text,
                }

        return {
            "updated_project": updated_project,
            "validation_errors": [],
            "response_text": result.raw_text,
        }

    async def validate(state: ProjectAuthoringState) -> dict[str, Any]:
        """Deterministic validation of the updated project JSON."""
        project = state.updated_project
        if project is None:
            return {"validation_errors": ["No project was produced by the agent."]}

        errors = validator.validate(project)
        if errors:
            logger.warning("Validation errors: %s", errors)
            return {
                "validation_errors": errors,
                "retry_count": state.retry_count + 1,
            }

        return {"validation_errors": []}

    async def persist(state: ProjectAuthoringState) -> dict[str, Any]:
        """Save the validated project to the store."""
        if state.updated_project is not None:
            await store.save_project_schema(state.updated_project)
            logger.info("Persisted project %s", state.updated_project.id)
        return {}

    async def respond(state: ProjectAuthoringState) -> dict[str, Any]:
        """Format the final response text."""
        if state.plan == AuthorPlan.clarify:
            return {
                "response_text": (
                    "I'd be happy to help! Could you tell me more specifically "
                    "what you'd like to change about the building? For example: "
                    "add floors, change dimensions, add doors/windows, etc."
                ),
            }

        if state.validation_errors:
            return {
                "response_text": (
                    f"I tried to update the project but encountered validation errors "
                    f"after {MAX_RETRIES} retries:\n"
                    + "\n".join(f"- {e}" for e in state.validation_errors)
                    + "\nPlease rephrase your request."
                ),
            }

        return {"response_text": state.response_text or "Project updated."}

    return {
        "parse_request": parse_request,
        "agent_worker": agent_worker,
        "validate": validate,
        "persist": persist,
        "respond": respond,
    }


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def should_call_agent(state: ProjectAuthoringState) -> str:
    """After parsing, skip agent if intent is 'clarify'."""
    if state.plan == AuthorPlan.clarify:
        return "respond"
    return "agent_worker"


def after_validation(state: ProjectAuthoringState) -> str:
    """After validation, retry agent or proceed to persist."""
    if state.validation_errors and state.retry_count < MAX_RETRIES:
        return "agent_worker"
    if state.validation_errors:
        # Exceeded retries — go straight to respond with errors
        return "respond"
    return "persist"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_project_authoring_graph(
    agent: CodingAgentProvider,
    validator: ProjectValidator,
    store: ProjectStore,
) -> Any:
    """Build and compile the project authoring LangGraph.

    Dependencies are injected so the graph is testable and vendor-agnostic.
    """
    nodes = make_nodes(agent, validator, store)

    graph = StateGraph(ProjectAuthoringState)

    graph.add_node("parse_request", nodes["parse_request"])
    graph.add_node("agent_worker", nodes["agent_worker"])
    graph.add_node("validate", nodes["validate"])
    graph.add_node("persist", nodes["persist"])
    graph.add_node("respond", nodes["respond"])

    graph.set_entry_point("parse_request")

    graph.add_conditional_edges("parse_request", should_call_agent, {
        "agent_worker": "agent_worker",
        "respond": "respond",
    })
    graph.add_edge("agent_worker", "validate")
    graph.add_conditional_edges("validate", after_validation, {
        "agent_worker": "agent_worker",
        "persist": "persist",
        "respond": "respond",
    })
    graph.add_edge("persist", "respond")
    graph.add_edge("respond", END)

    return graph.compile()
