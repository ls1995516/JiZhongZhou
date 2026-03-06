"""CodingAgentProvider — abstract interface for coding-agent-style LLM workers.

This is the swap point. Providers:
- MockAgentProvider: pipeline testing without any LLM
- OpenAIAgentProvider: default for local dev (uses OpenAI Responses API)
- AnthropicAgentProvider: stub for future Anthropic integration
"""

from __future__ import annotations

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Structured result from a coding-agent worker invocation."""

    raw_text: str  # the agent's natural-language explanation
    json_output: dict[str, Any] | None = None  # parsed structured output, if any


class CodingAgentProvider(ABC):
    """Interface for a coding-agent worker that can read/write structured data.

    The provider receives:
    - A system prompt describing its role
    - The user's request (plain text)
    - Optional structured context (current project JSON, schema, etc.)

    It returns an AgentResult with explanatory text and optional JSON output.
    """

    @abstractmethod
    async def invoke(
        self,
        system_prompt: str,
        user_request: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Run the agent and return its result."""
        ...


# ---------------------------------------------------------------------------
# Mock provider (no LLM, pipeline testing)
# ---------------------------------------------------------------------------

class MockAgentProvider(CodingAgentProvider):
    """MVP mock that echoes context back unchanged.

    Used for testing the pipeline end-to-end without an LLM.
    """

    async def invoke(
        self,
        system_prompt: str,
        user_request: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        logger.info("MockAgentProvider invoked: %s", user_request[:100])

        project_json = context.get("project") if context else None

        return AgentResult(
            raw_text=(
                f"[Mock Agent] Received your request: \"{user_request}\". "
                "In production, an LLM would analyze the current project "
                "and generate an updated ProjectJSON. For now, the project is unchanged."
            ),
            json_output=project_json,
        )


# ---------------------------------------------------------------------------
# OpenAI provider (default for local dev)
# ---------------------------------------------------------------------------

def _extract_json_from_text(text: str) -> dict[str, Any] | None:
    """Extract JSON from a response that may contain markdown fences or prose."""
    # Try ```json ... ``` fenced blocks first
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try the entire text as JSON
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to find the outermost { ... } block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None


class OpenAIAgentProvider(CodingAgentProvider):
    """Provider using the OpenAI Responses API.

    Reads OPENAI_API_KEY from environment. Uses the Responses API
    (client.responses.create) which is the current recommended API shape.
    """

    def __init__(self, model: str | None = None) -> None:
        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4.1")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required for OpenAIAgentProvider. "
                "Set it in your .env file or shell environment."
            )

        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=api_key)

    async def invoke(
        self,
        system_prompt: str,
        user_request: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        logger.info("OpenAIAgentProvider invoking %s: %s", self._model, user_request[:100])

        input_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_request},
        ]

        response = await self._client.responses.create(
            model=self._model,
            input=input_messages,
        )

        # Extract the text from the response
        raw_text = response.output_text or ""

        logger.debug("OpenAI response (%d chars): %s...", len(raw_text), raw_text[:200])

        # Try to extract structured JSON from the response
        json_output = _extract_json_from_text(raw_text)

        if json_output is None:
            logger.warning("Could not extract JSON from OpenAI response. Returning text only.")

        return AgentResult(raw_text=raw_text, json_output=json_output)


# ---------------------------------------------------------------------------
# Anthropic provider (stub for future use)
# ---------------------------------------------------------------------------

class AnthropicAgentProvider(CodingAgentProvider):
    """Anthropic Claude provider — stub for future implementation.

    TODO: Implement using the Anthropic SDK:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic()
        response = await client.messages.create(...)
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514") -> None:
        self._model_name = model

    async def invoke(
        self,
        system_prompt: str,
        user_request: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        logger.warning(
            "AnthropicAgentProvider.invoke() called but not yet implemented. "
            "Falling back to passthrough."
        )
        project_json = context.get("project") if context else None
        return AgentResult(
            raw_text=(
                f"[Anthropic Stub] I understood your request: \"{user_request}\". "
                "Anthropic integration is pending — project returned unchanged."
            ),
            json_output=project_json,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_agent_provider() -> CodingAgentProvider:
    """Create the appropriate agent provider based on environment configuration.

    Reads AI_PROVIDER env var:
    - "openai" (default): uses OpenAI Responses API, requires OPENAI_API_KEY
    - "anthropic": uses Anthropic (stub)
    - "mock": uses MockAgentProvider (no LLM)

    Falls back to MockAgentProvider if the configured provider can't be initialized.
    """
    provider_name = os.getenv("AI_PROVIDER", "openai").lower()

    if provider_name == "mock":
        logger.info("Using MockAgentProvider (no LLM)")
        return MockAgentProvider()

    if provider_name == "anthropic":
        logger.info("Using AnthropicAgentProvider (stub)")
        return AnthropicAgentProvider(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        )

    # Default: openai
    if provider_name != "openai":
        logger.warning("Unknown AI_PROVIDER=%r, defaulting to openai", provider_name)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning(
            "OPENAI_API_KEY not set. Falling back to MockAgentProvider. "
            "Set OPENAI_API_KEY in your environment or .env to enable AI."
        )
        return MockAgentProvider()

    model = os.getenv("OPENAI_MODEL", "gpt-4.1")
    logger.info("Using OpenAIAgentProvider (model=%s)", model)
    return OpenAIAgentProvider(model=model)
