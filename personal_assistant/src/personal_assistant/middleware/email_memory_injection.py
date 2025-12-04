"""Middleware for injecting memory into system prompts."""

from typing import Callable

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langgraph.store.base import BaseStore

from ..prompts import (
    agent_system_prompt_hitl_memory,
    default_background,
    default_cal_preferences,
    default_response_preferences,
    default_triage_instructions,
)
from ..tools.default.prompt_templates import HITL_MEMORY_TOOLS_PROMPT
from ..utils import aget_memory, get_memory


class MemoryInjectionMiddleware(AgentMiddleware):
    """Middleware for injecting memory preferences into system prompts.

    This middleware fetches memory from three namespaces (triage_preferences,
    response_preferences, cal_preferences) and injects them into the system prompt
    before each LLM call.

    Args:
        store: LangGraph store for persistent memory
    """

    def __init__(self, store: BaseStore):
        self.store = store

    def _get_store(self, runtime=None) -> BaseStore:
        """Get store from runtime if available, otherwise use instance store.

        In deployment, LangGraph platform provides store via runtime.
        In local testing, we use the store passed during initialization.

        Args:
            runtime: Optional runtime object with store attribute

        Returns:
            BaseStore instance
        """
        if runtime and hasattr(runtime, "store"):
            return runtime.store
        return self.store

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Inject memory into system prompt before LLM call.

        Fetches memory from the three namespaces (triage_preferences, response_preferences,
        cal_preferences) and injects them into the system prompt.
        """
        # Get store (from runtime in deployment, or from self in local testing)
        store = self._get_store(request.runtime if hasattr(request, "runtime") else None)

        # Fetch memory from store
        triage_prefs = get_memory(
            store,
            ("email_assistant", "triage_preferences"),
            default_triage_instructions,
        )
        response_prefs = get_memory(
            store,
            ("email_assistant", "response_preferences"),
            default_response_preferences,
        )
        cal_prefs = get_memory(
            store,
            ("email_assistant", "cal_preferences"),
            default_cal_preferences,
        )

        # Format system prompt with memory
        memory_prompt = agent_system_prompt_hitl_memory.format(
            tools_prompt=HITL_MEMORY_TOOLS_PROMPT,
            background=default_background,
            triage_instructions=triage_prefs,
            response_preferences=response_prefs,
            cal_preferences=cal_prefs,
        )

        # Append memory prompt to existing system prompt
        new_system_prompt = (
            request.system_prompt + "\n\n" + memory_prompt
            if request.system_prompt
            else memory_prompt
        )

        # Update request with new system prompt
        updated_request = request.override(system_prompt=new_system_prompt)

        return handler(updated_request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Async version of wrap_model_call for async agent invocation.

        Identical logic to wrap_model_call but supports async context.
        """
        # Get store (from runtime in deployment, or from self in local testing)
        store = self._get_store(request.runtime if hasattr(request, "runtime") else None)

        # Fetch memory from store (using async methods)
        triage_prefs = await aget_memory(
            store,
            ("email_assistant", "triage_preferences"),
            default_triage_instructions,
        )
        response_prefs = await aget_memory(
            store,
            ("email_assistant", "response_preferences"),
            default_response_preferences,
        )
        cal_prefs = await aget_memory(
            store,
            ("email_assistant", "cal_preferences"),
            default_cal_preferences,
        )

        # Format system prompt with memory
        memory_prompt = agent_system_prompt_hitl_memory.format(
            tools_prompt=HITL_MEMORY_TOOLS_PROMPT,
            background=default_background,
            triage_instructions=triage_prefs,
            response_preferences=response_prefs,
            cal_preferences=cal_prefs,
        )

        # Append memory prompt to existing system prompt
        new_system_prompt = (
            request.system_prompt + "\n\n" + memory_prompt
            if request.system_prompt
            else memory_prompt
        )

        # Update request with new system prompt
        updated_request = request.override(system_prompt=new_system_prompt)

        # Call handler (may or may not be async)
        return await handler(updated_request)
