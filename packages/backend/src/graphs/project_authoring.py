"""LangGraph workflow: Project Authoring.

Responsible for interpreting user intent and creating/updating ProjectJSON.

Graph structure:
  START → plan → agent_worker → validate → (pass→respond | fail→agent_worker retry) → END
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from ..models.state import AuthorPlan, ProjectAuthoringState

MAX_RETRIES = 2


# ---------------------------------------------------------------------------
# Node functions (stubs — implementation in next phase)
# ---------------------------------------------------------------------------

async def plan_node(state: ProjectAuthoringState) -> dict[str, Any]:
    """Analyze user message and decide: create / edit / clarify.

    TODO: Call LLM to classify intent. For now, default to 'edit' if project
    exists, 'create' if not.
    """
    if state.project is None:
        plan = AuthorPlan.create
    else:
        plan = AuthorPlan.edit

    return {"plan": plan}


async def agent_worker_node(state: ProjectAuthoringState) -> dict[str, Any]:
    """Coding-agent-style worker that generates or modifies ProjectJSON.

    This is where the CodingAgentProvider is invoked. The worker receives:
    - Current project JSON (if editing)
    - User messages / conversation history
    - The project JSON schema as context
    - The plan (create vs edit)

    It returns an updated ProjectJSON.

    TODO: Wire up CodingAgentProvider with proper prompt engineering.
    """
    # Stub: pass through existing project unchanged
    return {
        "validation_errors": [],
        "response_text": "[stub] Agent worker not yet implemented.",
    }


async def validate_node(state: ProjectAuthoringState) -> dict[str, Any]:
    """Deterministic validation of the project JSON.

    TODO: Invoke ProjectValidator. On failure, route back to agent_worker
    with error messages for self-correction.
    """
    # Stub: always passes
    return {"validation_errors": []}


async def respond_node(state: ProjectAuthoringState) -> dict[str, Any]:
    """Format the assistant's response message.

    TODO: Summarize what changed in the project.
    """
    text = state.response_text or "Project updated."
    return {"response_text": text}


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def should_retry(state: ProjectAuthoringState) -> str:
    """After validation, decide whether to retry or respond."""
    if state.validation_errors and state.retry_count < MAX_RETRIES:
        return "agent_worker"
    return "respond"


def should_skip_agent(state: ProjectAuthoringState) -> str:
    """After planning, skip agent if intent is 'clarify'."""
    if state.plan == AuthorPlan.clarify:
        return "respond"
    return "agent_worker"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_project_authoring_graph() -> StateGraph:
    """Build and return the compiled project authoring LangGraph."""

    graph = StateGraph(ProjectAuthoringState)

    graph.add_node("plan", plan_node)
    graph.add_node("agent_worker", agent_worker_node)
    graph.add_node("validate", validate_node)
    graph.add_node("respond", respond_node)

    graph.set_entry_point("plan")

    graph.add_conditional_edges("plan", should_skip_agent, {
        "agent_worker": "agent_worker",
        "respond": "respond",
    })
    graph.add_edge("agent_worker", "validate")
    graph.add_conditional_edges("validate", should_retry, {
        "agent_worker": "agent_worker",
        "respond": "respond",
    })
    graph.add_edge("respond", END)

    return graph.compile()
