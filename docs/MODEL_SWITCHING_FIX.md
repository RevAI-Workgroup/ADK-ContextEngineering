# Model Switching Fix - Implementation Summary

## Issue
When switching between locally available Ollama LLMs via the dropdown list in the Chat page, the application continued using the previously selected model instead of switching to the newly selected one.

## Root Cause
The model selection was properly captured in the frontend, but the backend was not using the `model` parameter passed in the chat request. The `ADKAgentWrapper` was using a single agent instance created at startup with a fixed model.

## Solution Implemented

### Backend Changes

#### 1. Dynamic Agent Creation (`src/api/adk_wrapper.py`)
- Added agent caching mechanism to support multiple models
- Implemented `_get_or_create_runner()` method that creates and caches agents per model
- Updated `process_message()` to accept a `model` parameter
- Updated `process_message_stream()` to accept a `model` parameter
- Modified `_run_agent_async()` to use a specific runner instance

**Key Features:**
- Lazy agent creation: Agents are only created when first requested
- Caching: Once an agent is created for a model, it's cached for reuse
- Backward compatibility: If no model is specified, uses the default agent

#### 2. Endpoint Updates (`src/api/endpoints.py`)
- Updated the `/api/chat` endpoint to pass the `model` parameter to `process_message()`
- Added `model` field to `ChatResponse` model to include which model was used
- Updated the response to include the model information

### Frontend Changes

#### 1. Type Updates
- Updated `AgentResponse` interface to include optional `model` field (`frontend/src/types/agent.types.ts`)
- Updated `Message` interface to include optional `model` field (`frontend/src/types/message.types.ts`)

#### 2. ChatInterface Component (`frontend/src/components/chat/ChatInterface.tsx`)
- Updated to pass the `model` from response to the assistant message

#### 3. ChatMessage Component (`frontend/src/components/chat/ChatMessage.tsx`)
- Added visual indicator showing which model was used for assistant messages
- Displays model name in a badge next to the timestamp
- Only shown for assistant messages (not user messages)

#### 4. ModelSelector Component (`frontend/src/components/chat/ModelSelector.tsx`)
- Added automatic chat clearing when switching models
- Prevents confusion from mixing responses from different models
- Only clears when actually switching (not on initial selection)

## Technical Details

### Agent Caching Strategy
```python
# Cache structure in ADKAgentWrapper
self._agent_cache: Dict[str, Agent] = {
    "default": root_agent
}
self._runner_cache: Dict[str, Runner] = {
    "default": self.runner
}
```

When a new model is requested:
1. Check if a runner exists in cache for that model
2. If yes, return cached runner
3. If no, create new agent with specified model
4. Cache both agent and runner for future use
5. Use the runner for the current request

### Model Parameter Flow
```
Frontend (ModelSelector) 
  → selectedModel state (ChatContext)
  → ChatInterface sends request with model
  → Backend endpoint receives model in ChatMessage
  → ADKAgentWrapper.process_message(model=...)
  → _get_or_create_runner(model)
  → Run agent with model-specific runner
  → Response includes model used
  → Frontend displays model badge
```

## Benefits

1. **Seamless Model Switching**: Users can now switch between models without any manual intervention
2. **Automatic Chat Clearing**: Chat history is automatically cleared when switching models to avoid confusion
3. **Visual Feedback**: Users can see which model generated each response
4. **Performance Optimization**: Agents are cached, so switching back to a previously used model is instant
5. **Backward Compatible**: Existing code that doesn't specify a model continues to work with the default

## Testing Recommendations

### Prerequisites
- Ensure Ollama is running on `localhost:11434`
- Have at least 2 different models installed (e.g., `qwen3:4b`, `llama2:7b`, `mistral:7b`)

### Test Cases

#### Test 1: Basic Model Switching
1. Start the frontend and backend
2. Open the Chat page
3. Select model A from the dropdown
4. Send a message (e.g., "What is 2+2?")
5. Verify the response shows a badge with model A's name
6. Switch to model B
7. Verify chat is automatically cleared
8. Send the same message
9. Verify the response shows a badge with model B's name
10. Confirm responses match each model's style/behavior

#### Test 2: Model Caching
1. Switch to model A, send a message
2. Switch to model B, send a message
3. Switch back to model A, send another message
4. Check backend logs - should see "Using cached runner for model: ..."
5. Verify response time for cached model is faster

#### Test 3: Multiple Conversations
1. Select model A
2. Have a multi-turn conversation (3-4 messages)
3. Switch to model B
4. Verify all previous messages are cleared
5. Start new conversation with model B
6. Verify responses are from model B

#### Test 4: Default Model Behavior
1. Clear browser cache/storage
2. Refresh page
3. Verify first model in list is auto-selected
4. Send message without manually selecting
5. Verify response shows model badge

#### Test 5: Error Handling
1. Stop Ollama service
2. Try to load model list - should show error
3. Start Ollama
4. Refresh - models should load
5. Select a model that doesn't exist in backend
6. Send message - verify appropriate error handling

## Files Modified

### Backend
- `src/api/adk_wrapper.py` - Added dynamic agent creation and caching
- `src/api/endpoints.py` - Added model parameter support

### Frontend
- `frontend/src/types/agent.types.ts` - Added model field
- `frontend/src/types/message.types.ts` - Added model field
- `frontend/src/components/chat/ChatInterface.tsx` - Pass model from response
- `frontend/src/components/chat/ChatMessage.tsx` - Display model badge
- `frontend/src/components/chat/ModelSelector.tsx` - Auto-clear on model switch

## Configuration

No configuration changes required. The system uses existing model configuration from `configs/models.yaml` for default temperature and max_tokens settings, which are applied to all dynamically created agents.

## Future Enhancements

1. **Model-specific configurations**: Allow different temperature/max_tokens per model
2. **Model comparison**: Side-by-side comparison of responses from different models
3. **Model metadata**: Show model size, parameters, capabilities in the selector
4. **Session preservation**: Option to maintain separate conversations per model
5. **Performance metrics**: Track and display latency/token usage per model

## Notes

- The session service is shared across all agents, allowing conversation history to be maintained
- Model switching clears the UI but doesn't affect backend session storage
- The first time a model is used, there may be a slight delay while the agent is created
- Subsequent uses of the same model will be instant due to caching

