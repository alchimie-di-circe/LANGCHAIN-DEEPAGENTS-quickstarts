# Personal Assistant

Email assistant using deepagents library with two-tiered architecture, human-in-the-loop (HITL) interrupts, and persistent memory system.

## Quickstart

### Python Version

* Ensure you're using Python 3.11 or later
* Required for optimal compatibility with LangGraph

```shell
python3 --version
```

### API Keys

* Sign up for Anthropic API key [here](https://console.anthropic.com/)
* Sign up for LangSmith [here](https://smith.langchain.com/)

### Set Environment Variables

Create a `.env` file in the root directory:

```shell
ANTHROPIC_API_KEY=your_anthropic_api_key
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=personal-assistant
```

Or set them in your terminal:

```shell
export ANTHROPIC_API_KEY=your_anthropic_api_key
export LANGSMITH_API_KEY=your_langsmith_api_key
export LANGSMITH_TRACING=true
```

### Package Installation

**Using uv (recommended):**

```shell
# Install uv if you haven't already
pip install uv

# Install the package
uv sync

# Activate the virtual environment
source .venv/bin/activate
```

### Local Deployment

Start LangGraph Studio for interactive testing:

```bash
langgraph dev
```

Then open [http://localhost:2024](http://localhost:2024) in your browser.

### Using Agent Inbox

[Agent Inbox](https://github.com/langchain-ai/agent-inbox) provides a user-friendly web interface for managing human-in-the-loop interactions. Instead of programmatically handling interrupts, you can use Agent Inbox's UI to review and respond to agent actions.

**Quick Setup:**

1. Start your local LangGraph deployment:
   ```bash
   langgraph dev
   ```

2. Open Agent Inbox in your browser:
   ```
   https://dev.agentinbox.ai/
   ```

3. Connect to your local graph:
   - Click "Settings" (gear icon) in Agent Inbox
   - Add your LangSmith API key
   - Create a new inbox connection:
     - **Graph ID**: `personal_assistant` (from `langgraph.json`)
     - **Deployment URL**: `http://localhost:2024` (your local dev server)

4. Process emails through the inbox:
   - Send an email input to your graph via LangGraph Studio or API
   - When the agent needs approval, the interrupt appears in Agent Inbox
   - Review the email context and proposed action
   - Choose your response:
     - **Accept** - Execute the action as-is
     - **Edit** - Modify the arguments and execute
     - **Ignore** - Skip the action and end workflow
     - **Response** - Provide feedback for the agent to incorporate

**What You'll See:**

When the email assistant interrupts (for `write_email`, `schedule_meeting`, or `Question`), Agent Inbox displays:
- Original email context (subject, sender, content)
- Proposed action (email draft or meeting invite)
- Action details (formatted for easy review)
- Available response options based on the tool

**Memory Learning:**

Agent Inbox responses automatically update the assistant's memory:
- **Edit responses** → Updates response/calendar preferences
- **Ignore responses** → Updates triage preferences
- **Feedback responses** → Incorporates into next action

This allows the assistant to learn your preferences over time and improve future suggestions.

## Architecture Overview

### Two-Tiered Design

The assistant uses a two-tiered architecture to efficiently handle emails:

```
Email Input → Triage Router → [Respond / Notify / Ignore]
                    ↓
            Response Agent (with HITL)
```

**Tier 1: Triage Router**
- **Purpose**: Classify emails to avoid wasting time on irrelevant messages
- **Classifications**:
  - `respond` - Email requires a response → Routes to Response Agent
  - `notify` - Important FYI email → Creates interrupt for user review
  - `ignore` - Spam, marketing, or irrelevant → Ends workflow
- **Memory**: Learns from user corrections via `triage_preferences` namespace
- **Location**: `src/personal_assistant/email_assistant_deepagents.py:29-156`

**Tier 2: Response Agent**
- **Purpose**: Generate email drafts and schedule meetings with HITL approval
- **Built with**: `create_deep_agent()` from deepagents library
- **Custom Middleware**: `EmailAssistantHITLMiddleware` for intelligent interrupts
- **Tools**: `write_email`, `schedule_meeting`, `check_calendar_availability`, `Question`, `Done`
- **Location**: `src/personal_assistant/email_assistant_deepagents.py:227-255`

### HITL Middleware System

Custom middleware that intercepts specific tool calls for human approval:

**Interrupt Filtering**:
- Only interrupts for: `write_email`, `schedule_meeting`, `Question`
- Other tools execute directly (e.g., `check_calendar_availability`)

**Four Response Types**:
1. **Accept** - Execute tool with original arguments
2. **Edit** - Execute with modified arguments, update AI message immutably
3. **Ignore** - Skip execution, end workflow, update triage memory
4. **Response** - Provide feedback, continue workflow with updated context

**Memory Integration**:
- Injects learned preferences into system prompt before each LLM call
- Updates memory after user edits or feedback
- Uses runtime store in deployment, local store in testing

**Location**: `src/personal_assistant/middleware/email_assistant_hitl.py`

### Memory System

Three persistent memory namespaces that learn from user behavior:

1. **`triage_preferences`** - Email classification rules
   - Updated when: User corrects triage decisions (respond vs. notify vs. ignore)
   - Example: "Emails from Alice about API docs should be responded to"

2. **`response_preferences`** - Email writing style
   - Updated when: User edits email drafts or provides feedback
   - Example: "Keep responses concise, avoid formalities"

3. **`cal_preferences`** - Meeting scheduling preferences
   - Updated when: User edits meeting invitations or provides feedback
   - Example: "Prefer 30-minute meetings, avoid Fridays"

**Storage**:
- Local testing: `InMemoryStore()` (ephemeral)
- Deployment: LangGraph platform store (persistent across sessions)
- Backend: `StoreBackend` for deepagents integration

### Deployment Modes

**Local Testing Mode** (`for_deployment=False`):
- Creates `InMemoryStore()` and `MemorySaver()`
- Passes store/checkpointer to both top-level workflow and response agent
- Use for: Notebook testing, standalone Python scripts

**Deployment Mode** (`for_deployment=True`):
- Does NOT pass store/checkpointer to graph compilation
- LangGraph platform provides persistence infrastructure
- Use for: `langgraph dev`, LangGraph Cloud, production deployments

## Code Structure

```
examples/personal_assistant/
├── agent.py                          # Deployment entry point (used by langgraph.json)
├── langgraph.json                    # LangGraph deployment config
├── pyproject.toml                    # Package dependencies and metadata
├── test.ipynb                        # Interactive testing notebook
├── README.md                         # This file
│
└── src/personal_assistant/
    ├── __init__.py                   # Package exports
    ├── email_assistant_deepagents.py # Main: Email assistant with triage tool
    ├── schemas.py                    # State schemas (EmailAssistantState, etc.)
    ├── prompts.py                    # System prompts and memory instructions
    ├── configuration.py              # Config loading (minimal)
    ├── utils.py                      # Utilities (memory, formatting, parsing)
    ├── ntbk_utils.py                 # Notebook utilities (rich formatting)
    │
    ├── middleware/
    │   ├── __init__.py
    │   └── email_assistant_hitl.py   # Custom HITL middleware with memory
    │
    └── tools/
        ├── __init__.py
        ├── base.py                   # Tool loading and registry
        │
        ├── default/                  # Default tools (no external APIs)
        │   ├── __init__.py
        │   ├── email_tools.py        # write_email, Question, Done
        │   ├── calendar_tools.py     # schedule_meeting, check_calendar_availability
        │   └── prompt_templates.py   # Tool prompt templates
        │
        └── gmail/                    # Gmail integration (optional)
            ├── __init__.py
            ├── gmail_tools.py        # Gmail API tools
            └── gmail_utils.py        # Gmail utilities
```

## Test Email Examples

### Example 1: Direct Question (Will be RESPONDED to)

This email will trigger the `respond` classification because it's addressed to Lance with a direct technical question:

```json
{
  "author": "Sarah Chen <sarah.chen@techcorp.com>",
  "to": "Lance Martin <lance@langchain.dev>",
  "subject": "Question about LangGraph deployment",
  "email_thread": "Hi Lance,\n\nI'm working on deploying a LangGraph agent to production and ran into an issue with the store configuration. When I try to use a custom store, I get an error about the platform providing its own persistence.\n\nCould you clarify when we should pass a store vs. letting the platform handle it?\n\nAlso, do you have any examples of deploying agents with custom HITL middleware?\n\nThanks!\nSarah"
}
```

**Why this will be responded to:**
- ✅ Addressed TO Lance (not CC'd)
- ✅ Contains direct questions requiring response
- ✅ Technical question about LangGraph (Lance's area)

### Example 2: Meeting Request (Will be RESPONDED to)

```json
{
  "author": "Alex Rodriguez <alex.rodriguez@company.com>",
  "to": "Lance Martin <lance@langchain.dev>",
  "subject": "Sync on agent architecture",
  "email_thread": "Hey Lance,\n\nCan we schedule 30 minutes next week to discuss the multi-agent architecture for our project? I have some questions about routing between agents and want to get your input.\n\nI'm free Tuesday afternoon or Thursday morning. Let me know what works!\n\nBest,\nAlex"
}
```

**Why this will be responded to:**
- ✅ Direct meeting request to Lance
- ✅ Requires scheduling action
- ✅ Will trigger `schedule_meeting` tool with HITL

### Example 3: FYI Email (Will be IGNORED)

```json
{
  "author": "Newsletter <newsletter@techblog.com>",
  "to": "Lance Martin <lance@langchain.dev>",
  "subject": "Weekly AI Newsletter - Top Articles",
  "email_thread": "This week's top articles:\n\n1. New advances in RAG systems\n2. Latest LLM benchmarks\n3. Multi-agent coordination patterns\n\n[Read more...]"
}
```

**Why this will be ignored:**
- ❌ Newsletter/marketing content
- ❌ No action required
- ❌ No direct questions

## Usage

### Python API

```python
from personal_assistant import create_email_assistant

# Create agent (local testing mode)
agent = create_email_assistant(for_deployment=False)

# Example email
email_input = {
    "author": "sarah.chen@techcorp.com",
    "to": "lance@langchain.dev",
    "subject": "Question about LangGraph deployment",
    "email_thread": "Hi Lance,\n\nI'm working on deploying a LangGraph agent..."
}

# Process email
config = {"configurable": {"thread_id": "thread-1"}}
result = agent.invoke({"email_input": email_input}, config=config)

# Check for interrupts
if "__interrupt__" in result:
    print("Agent is waiting for approval")
    # Resume with decision
    from langgraph.types import Command
    result = agent.invoke(
        Command(resume={"decisions": [{"type": "accept"}]}),
        config=config
    )
```

### Notebook Testing

See `test.ipynb` for interactive examples with rich formatting:
- Process emails step-by-step
- Visualize agent reasoning
- Test all HITL response types (accept, edit, ignore, response)
- View memory updates in real-time

### Deployment

The agent is configured for LangGraph deployment via `agent.py` and `langgraph.json`.

**Key difference**: In deployment mode, the agent doesn't create its own store/checkpointer:

```python
# agent.py uses deployment mode
graph = create_email_assistant(for_deployment=True)
```

This allows the LangGraph platform to provide persistent storage, checkpointing, and the LangGraph Studio UI.

## Features

- **Two-Tiered Architecture**: Triage router + response agent for efficient email handling
- **Custom HITL Middleware**: Sophisticated interrupt handling with tool filtering
- **Persistent Memory**: Learns from user feedback across 3 namespaces
- **Four Response Types**: Accept, edit, ignore, or provide feedback on agent actions
- **Async Support**: Works with both sync and async invocation (invoke/ainvoke, stream/astream)
- **Deployment Ready**: Optimized for LangGraph Cloud with platform-provided persistence

## Testing

Run the notebook for interactive testing:

```bash
jupyter notebook test.ipynb
```

Or run the standalone script:

```bash
python -m personal_assistant.email_assistant_deepagents
```
