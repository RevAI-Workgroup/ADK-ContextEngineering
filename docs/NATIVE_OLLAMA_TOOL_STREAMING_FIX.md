# Native Ollama Tool Streaming Fix

## Problem Statement

When using the application with **Token Streaming mode enabled**, LLMs failed to properly execute tools. Even when the agent's reasoning showed intent to use a tool (visible in the "Agent Reasoning" div), the actual tool call never happened. Instead, the model would hallucinate an answer.

### Example of the Bug
- User asks: "What time is it in Tokyo?"
- Agent reasoning shows: "I should use get_current_time tool..."
- **Expected**: Tool call UI appears, `get_current_time` executes, real time is returned
- **Actual**: No tool call, model makes up a time

## Root Cause

This is a **well-documented limitation of LiteLLM with Ollama** during streaming mode:
- GitHub Issue: https://github.com/BerriAI/litellm/issues/15399
- LiteLLM encounters parsing failures during streaming chunks from Ollama
- Errors like `MidStreamFallbackError` and `ServiceUnavailableError` occur
- Tool calls are not properly extracted during streaming mode

## Solution

Replaced the LiteLLM streaming implementation with **Ollama's native Python SDK** for token streaming mode.

### Key Changes

1. **New Native Ollama Streaming Method** (`process_message_stream_native_ollama`)
   - Uses `ollama.AsyncClient` directly
   - Implements an agentic loop pattern:
     ```
     1. Make non-streaming call with tools
     2. Check if model wants to use tools
     3. If yes: execute tool, add result to messages, goto 1
     4. If no: stream final response to user
     ```
   - Supports multi-step tool execution (up to 10 iterations)

2. **Tool Execution System**
   - `_build_ollama_tools()`: Converts Python functions to Ollama tool format
   - `_execute_tool()`: Executes tools by name with arguments
   - Full support for: `calculate`, `get_current_time`, `analyze_text`, `count_words`, `search_knowledge_base`

3. **WebSocket Handler Updated**
   - When `enableTokenStreaming = true`, uses native Ollama method
   - When `enableTokenStreaming = false`, uses ADK's run_async (unchanged)

### Architecture

```
User Query → WebSocket → endpoints.py
                           ↓
              (Token Streaming ON?)
                 /              \
               Yes              No
                ↓                ↓
    process_message_         process_message_
    stream_native_ollama     stream (ADK)
                ↓
    Ollama Native SDK
    (AsyncClient.chat)
                ↓
    Agentic Loop:
    - Detect tool calls
    - Execute tools
    - Continue conversation
                ↓
    Stream events to frontend:
    - reasoning_token
    - tool_call
    - tool_result
    - token
    - complete
```

## Files Modified

1. **`src/api/adk_wrapper.py`**
   - Added `import ollama`
   - Added `_build_ollama_tools()` method
   - Added `_execute_tool()` method
   - Added `process_message_stream_native_ollama()` method

2. **`src/api/endpoints.py`**
   - Updated WebSocket handler to use native Ollama method

## Testing

After the fix, with Token Streaming enabled:

1. **Tool calls work properly**
   - User asks "What time is it in Tokyo?"
   - Tool call div appears showing `get_current_time` invocation
   - Tool result shows actual time
   - Agent responds with the real time

2. **Reasoning still streams**
   - Agent Reasoning div expands
   - Reasoning tokens appear as they're generated

3. **Multi-step tools work**
   - Complex queries requiring multiple tool calls are handled
   - Each tool call is shown in the UI

## Consideration: CopilotKit AG-UI

AG-UI (Agent-User Interaction Protocol) was considered but **not implemented** because:

1. **Not necessary for this fix** - The issue was LiteLLM-specific, not architecture-related
2. **Current WebSocket events are sufficient** - Already support all needed event types
3. **Would add complexity** - AG-UI is better suited for multi-agent scenarios

**When to consider AG-UI:**
- Orchestrating multiple AI agents
- Integrating with AG-UI ecosystem
- Standardizing for third-party integrations
- Building a more general-purpose agent platform

## Dependencies

The fix uses the existing `ollama` package already in `requirements.txt`:
```
ollama>=0.5.0
```

## Related Documentation

- [Ollama Python SDK](https://github.com/ollama/ollama-python)
- [LiteLLM Issue #15399](https://github.com/BerriAI/litellm/issues/15399)
- [AG-UI Protocol](https://docs.ag-ui.com/introduction)

