"""CodingAgentProvider — abstract interface for coding-agent-style LLM workers.

This is the swap point. In MVP we call Anthropic Claude directly.
Later this can be replaced with Codex, Claude Code CLI, or any repo-aware agent.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from langchain_core.messages import BaseMessage


class CodingAgentProvider(ABC):
    """Interface for a coding-agent worker that can read/write structured data.

    The provider receives context (current JSON, schema, user intent) and
    returns an updated structured result plus optional explanatory text.
    """

    @abstractmethod
    async def invoke(
        self,
        messages: list[BaseMessage],
        system_prompt: str,
        context: dict[str, Any] | None = None,
    ) -> BaseMessage:
        """Run the agent and return its response message.

        Args:
            messages: Conversation history including the latest user request.
            system_prompt: Role/task instructions for this worker.
            context: Additional structured context (current project JSON, schema, etc.)

        Returns:
            The agent's response message.
        """
        ...


class AnthropicAgentProvider(CodingAgentProvider):
    """MVP implementation using langchain-anthropic ChatAnthropic.

    TODO: Wire up actual model call in implementation phase.
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514") -> None:
        self._model_name = model

    async def invoke(
        self,
        messages: list[BaseMessage],
        system_prompt: str,
        context: dict[str, Any] | None = None,
    ) -> BaseMessage:
        # Stub — will be implemented when we wire up the LangGraph nodes
        raise NotImplementedError(
            "AnthropicAgentProvider.invoke() is not yet implemented. "
            "This will be connected during LangGraph node implementation."
        )
