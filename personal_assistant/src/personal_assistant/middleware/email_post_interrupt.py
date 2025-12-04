"""Middleware for updating memory based on interrupt responses."""

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import AIMessage
from langgraph.store.base import BaseStore

from ..prompts import MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT
from ..utils import aupdate_memory, update_memory


class PostInterruptMemoryMiddleware(AgentMiddleware):
    """Middleware for updating memory when user rejects tool calls.

    This middleware detects when tool calls are rejected (never executed) and
    updates triage preferences to learn which emails should not trigger responses.

    Memory updates:
    - reject write_email: Updates triage_preferences
    - reject schedule_meeting: Updates triage_preferences
    - approve: No memory update

    Args:
        store: LangGraph store for persistent memory
    """

    # Import state schema at the top of the file
    from ..schemas import EmailAssistantState
    state_schema = EmailAssistantState

    def __init__(self, store: BaseStore):
        self.store = store
        # Track which tools should trigger memory updates on reject
        self.interrupt_tools = {"write_email", "schedule_meeting"}
        # Track which tool calls we've already processed (to avoid duplicates)
        self._processed_tool_calls = set()

    def before_model(self, state, runtime) -> dict | None:
        """Check for rejected tool calls before next model generation.

        After a rejection, the built-in HITL middleware adds a ToolMessage with
        status="error". We check for these BEFORE the next model call to update memory.
        """
        print("DEBUG before_model: Hook called")
        messages = state.get("messages", [])
        print(f"DEBUG before_model: Found {len(messages)} messages")

        # Debug: Print message types
        for idx, msg in enumerate(messages):
            msg_type = type(msg).__name__
            status = getattr(msg, "status", None)
            print(f"DEBUG before_model: Message {idx}: {msg_type}, status={status}")

        # Look for ToolMessages with status="error" (rejections)
        for message in reversed(messages):
            # Check if this is a ToolMessage with error status (indicates rejection)
            if (hasattr(message, "status") and
                message.status == "error" and
                hasattr(message, "tool_call_id")):

                tool_call_id = message.tool_call_id
                tool_name = message.name
                rejection_message = message.content
                print(f"DEBUG before_model: Found rejection - tool_name={tool_name}, tool_call_id={tool_call_id}")

                # Check if this is a tool we care about and haven't processed yet
                if tool_name in self.interrupt_tools and tool_call_id not in self._processed_tool_calls:
                    print(f"DEBUG before_model: Processing rejection for {tool_name}")
                    # Find the original tool call args from the AIMessage
                    original_args = {}
                    for msg in reversed(messages):
                        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
                            for tc in msg.tool_calls:
                                if tc.get("id") == tool_call_id:
                                    original_args = dict(tc.get("args", {}))
                                    break
                            if original_args:
                                break

                    # Update memory with rejection message
                    print(f"DEBUG before_model: Updating memory for rejection")
                    self._update_memory_for_reject(tool_name, original_args, rejection_message, state, runtime)
                    # Mark as processed
                    self._processed_tool_calls.add(tool_call_id)
                    print(f"DEBUG before_model: Memory update complete")

        return None

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

    def after_tool(self, state, runtime) -> dict | None:
        """Check for rejected tool calls.

        When a user rejects a tool call with built-in interrupt_on, a ToolMessage
        with status="error" is created containing the rejection reason.
        """
        print("DEBUG after_tool: Hook called")
        messages = state.get("messages", [])
        print(f"DEBUG after_tool: Found {len(messages)} messages")
        if not messages:
            return None

        # Debug: Print message types
        for idx, msg in enumerate(messages):
            msg_type = type(msg).__name__
            status = getattr(msg, "status", None)
            print(f"DEBUG after_tool: Message {idx}: {msg_type}, status={status}")

        # Look for ToolMessages with status="error" (rejections)
        for message in reversed(messages):
            # Check if this is a ToolMessage with error status (indicates rejection)
            if (hasattr(message, "status") and
                message.status == "error" and
                hasattr(message, "tool_call_id")):

                tool_call_id = message.tool_call_id
                tool_name = message.name
                rejection_message = message.content  # This contains the user's rejection reason
                print(f"DEBUG after_tool: Found rejection - tool_name={tool_name}, tool_call_id={tool_call_id}")

                # Check if this is a tool we care about and haven't processed yet
                if tool_name in self.interrupt_tools and tool_call_id not in self._processed_tool_calls:
                    print(f"DEBUG after_tool: Processing rejection for {tool_name}")
                    # Find the original tool call args from the AIMessage
                    original_args = {}
                    for msg in reversed(messages):
                        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
                            for tc in msg.tool_calls:
                                if tc.get("id") == tool_call_id:
                                    original_args = dict(tc.get("args", {}))
                                    break
                            if original_args:
                                break

                    # Update memory with rejection message
                    print(f"DEBUG after_tool: Updating memory for rejection")
                    self._update_memory_for_reject(tool_name, original_args, rejection_message, state, runtime)
                    # Mark as processed
                    self._processed_tool_calls.add(tool_call_id)
                    print(f"DEBUG after_tool: Memory update complete")
                else:
                    print(f"DEBUG after_tool: Skipping - tool_name in interrupt_tools: {tool_name in self.interrupt_tools}, already processed: {tool_call_id in self._processed_tool_calls}")

        return None

    def _update_memory_for_reject(
        self, tool_name: str, original_args: dict, rejection_message: str, state, runtime
    ):
        """Update triage preferences when user rejects a tool call.

        Args:
            tool_name: Name of the tool that was rejected
            original_args: Original tool arguments that were rejected
            rejection_message: User's optional feedback explaining why they rejected
            state: Agent state containing messages
            runtime: Runtime context
        """
        namespace = ("email_assistant", "triage_preferences")

        # Create feedback based on tool type
        if tool_name == "write_email":
            feedback = "The user rejected the email draft. That means they did not want to respond to the email. Update the triage preferences to ensure emails of this type are not classified as respond."
        elif tool_name == "schedule_meeting":
            feedback = "The user rejected the calendar meeting draft. That means they did not want to schedule a meeting for this email. Update the triage preferences to ensure emails of this type are not classified as respond."
        else:
            return  # No memory update for other tools

        # Get conversation context for memory update from state
        messages = state.get("messages", [])

        # Format args as JSON for context
        import json
        args_str = json.dumps(original_args, indent=2)

        # Include user's rejection message if provided
        rejection_context = f"\n\nUser's rejection reason: {rejection_message}" if rejection_message else ""

        messages_for_update = messages + [
            {
                "role": "user",
                "content": f"{feedback}\n\nRejected tool call: {tool_name}\nArguments: {args_str}{rejection_context}\n\nFollow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}",
            }
        ]

        store = self._get_store(runtime)
        update_memory(store, namespace, messages_for_update)

    # Async versions

    async def abefore_model(self, state, runtime) -> dict | None:
        """Async version - check for rejected tool calls before next model generation."""
        print("DEBUG abefore_model: Hook called")
        messages = state.get("messages", [])
        print(f"DEBUG abefore_model: Found {len(messages)} messages")

        # Debug: Print message types
        for idx, msg in enumerate(messages):
            msg_type = type(msg).__name__
            status = getattr(msg, "status", None)
            print(f"DEBUG abefore_model: Message {idx}: {msg_type}, status={status}")

        # Look for ToolMessages with status="error" (rejections)
        for message in reversed(messages):
            # Check if this is a ToolMessage with error status (indicates rejection)
            if (hasattr(message, "status") and
                message.status == "error" and
                hasattr(message, "tool_call_id")):

                tool_call_id = message.tool_call_id
                tool_name = message.name
                rejection_message = message.content
                print(f"DEBUG abefore_model: Found rejection - tool_name={tool_name}, tool_call_id={tool_call_id}")

                # Check if this is a tool we care about and haven't processed yet
                if tool_name in self.interrupt_tools and tool_call_id not in self._processed_tool_calls:
                    print(f"DEBUG abefore_model: Processing rejection for {tool_name}")
                    # Find the original tool call args from the AIMessage
                    original_args = {}
                    for msg in reversed(messages):
                        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
                            for tc in msg.tool_calls:
                                if tc.get("id") == tool_call_id:
                                    original_args = dict(tc.get("args", {}))
                                    break
                            if original_args:
                                break

                    # Update memory with rejection message
                    print(f"DEBUG abefore_model: Updating memory for rejection")
                    await self._aupdate_memory_for_reject(tool_name, original_args, rejection_message, state, runtime)
                    # Mark as processed
                    self._processed_tool_calls.add(tool_call_id)
                    print(f"DEBUG abefore_model: Memory update complete")

        return None

    async def _aupdate_memory_for_reject(
        self, tool_name: str, original_args: dict, rejection_message: str, state, runtime
    ):
        """Async version of _update_memory_for_reject.

        Args:
            tool_name: Name of the tool that was rejected
            original_args: Original tool arguments that were rejected
            rejection_message: User's optional feedback explaining why they rejected
            state: Agent state containing messages
            runtime: Runtime context
        """
        namespace = ("email_assistant", "triage_preferences")

        # Create feedback based on tool type
        if tool_name == "write_email":
            feedback = "The user rejected the email draft. That means they did not want to respond to the email. Update the triage preferences to ensure emails of this type are not classified as respond."
        elif tool_name == "schedule_meeting":
            feedback = "The user rejected the calendar meeting draft. That means they did not want to schedule a meeting for this email. Update the triage preferences to ensure emails of this type are not classified as respond."
        else:
            return  # No memory update for other tools

        # Get conversation context for memory update from state
        messages = state.get("messages", [])

        # Format args as JSON for context
        import json
        args_str = json.dumps(original_args, indent=2)

        # Include user's rejection message if provided
        rejection_context = f"\n\nUser's rejection reason: {rejection_message}" if rejection_message else ""

        messages_for_update = messages + [
            {
                "role": "user",
                "content": f"{feedback}\n\nRejected tool call: {tool_name}\nArguments: {args_str}{rejection_context}\n\nFollow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}",
            }
        ]

        store = self._get_store(runtime)
        await aupdate_memory(store, namespace, messages_for_update)
