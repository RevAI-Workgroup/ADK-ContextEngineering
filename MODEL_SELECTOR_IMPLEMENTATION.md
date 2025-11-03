# Model Selector Implementation

## Overview
Added a dropdown selector to the chat page that allows users to choose from locally installed Ollama models.

## Changes Made

### Backend (Python/FastAPI)

#### 1. **API Endpoints** (`src/api/endpoints.py`)
- Added `models_router` to handle model-related endpoints
- Created `/api/models` GET endpoint that fetches locally installed Ollama models
- Added `httpx` import for making HTTP requests to Ollama API
- Updated `ChatMessage` model to include optional `model` field

**Key Features:**
- Connects to Ollama API at `http://localhost:11434/api/tags`
- Returns formatted model information (name, size, modified date, digest)
- Handles connection errors with appropriate HTTP status codes
- Provides user-friendly error messages when Ollama is not running

#### 2. **API Router Registration** (`src/api/main.py`)
- Registered `models_router` with prefix `/api` and tag `models`

#### 3. **Dependencies** (`requirements.txt`)
- Added `httpx>=0.27.0` for HTTP client functionality

### Frontend (React/TypeScript)

#### 1. **UI Component** (`frontend/src/components/ui/select.tsx`)
- Installed shadcn/ui select component using `npx shadcn@latest add select`

#### 2. **Model Service** (`frontend/src/services/modelsService.ts`)
- Created new service to fetch Ollama models from backend API
- Defined `OllamaModel` interface matching backend schema
- Implements `getModels()` method

#### 3. **Model Selector Component** (`frontend/src/components/chat/ModelSelector.tsx`)
- New component for displaying model dropdown
- Features:
  - Fetches available models on mount
  - Auto-selects first model if none selected
  - Shows loading state while fetching
  - Displays error messages if Ollama is not running
  - Updates selected model in ChatContext

#### 4. **Chat Context** (`frontend/src/contexts/ChatContext.tsx`)
- Added `selectedModel` state (string | null)
- Added `setSelectedModel` state setter
- Exposed through ChatContext provider

#### 5. **Agent Service** (`frontend/src/services/agentService.ts`)
- Updated `sendMessage()` to accept optional `model` parameter
- Passes model to backend API when making chat requests

#### 6. **Agent Hook** (`frontend/src/hooks/useAgent.ts`)
- Updated `sendMessage()` to accept and forward `model` parameter

#### 7. **Chat Interface** (`frontend/src/components/chat/ChatInterface.tsx`)
- Retrieves `selectedModel` from ChatContext
- Passes selected model to `sendHttpMessage()` when sending messages

#### 8. **Chat Page** (`frontend/src/pages/Chat.tsx`)
- Added `ModelSelector` component to page header
- Positioned between page title and "Clear Chat" button
- Responsive layout with proper spacing

## Usage

### User Flow:
1. Navigate to the Chat page
2. Model dropdown appears in the header with robot icon
3. Dropdown shows all locally installed Ollama models
4. User selects desired model from dropdown
5. All subsequent chat messages use the selected model
6. Model selection persists during the session

### Error Handling:
- If Ollama is not running: Shows "Failed to load models. Is Ollama running?"
- If no models installed: Shows "No models available"
- Backend returns 503 error if cannot connect to Ollama
- Backend returns 504 error on timeout

## Testing

### Backend Test:
```bash
# Test models endpoint
curl http://localhost:8000/api/models

# Expected response:
[
  {
    "name": "qwen3:8b",
    "modified_at": "2025-11-02T20:22:50.91563348+01:00",
    "size": 5225388164,
    "digest": "500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41"
  }
]
```

### Frontend Test:
1. Start backend: `uvicorn src.api.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Open browser to `http://localhost:5173`
4. Navigate to Chat page
5. Verify model dropdown appears and shows available models
6. Select a model and send a message
7. Verify message is sent with selected model

## Technical Details

### Model Selection Flow:
```
User selects model in UI
    ↓
ModelSelector updates ChatContext.selectedModel
    ↓
ChatInterface reads selectedModel from context
    ↓
Passes model to useAgent.sendMessage()
    ↓
agentService.sendMessage() includes model in request body
    ↓
Backend receives model parameter in ChatMessage
    ↓
Model used for processing the chat message
```

### API Contract:

**Request:**
```typescript
POST /api/chat
{
  "message": "Hello",
  "session_id": "optional-session-id",
  "include_thinking": true,
  "model": "qwen3:8b"  // Optional - uses default if not provided
}
```

**Models Endpoint:**
```typescript
GET /api/models
Response: OllamaModel[]

interface OllamaModel {
  name: string
  modified_at: string
  size: number
  digest?: string
}
```

## Future Enhancements

Possible improvements:
1. Save selected model to localStorage for persistence across sessions
2. Show model details (size, parameters) in dropdown
3. Add model search/filter for users with many models
4. Display currently active model in chat messages
5. Allow per-message model override
6. Show model-specific capabilities or limitations
7. Add model performance metrics (speed, quality)
8. Support for model configuration options (temperature, etc.)

## Files Modified

**Backend:**
- `src/api/endpoints.py`
- `src/api/main.py`
- `requirements.txt`

**Frontend:**
- `frontend/src/components/chat/ModelSelector.tsx` (new)
- `frontend/src/components/ui/select.tsx` (new)
- `frontend/src/services/modelsService.ts` (new)
- `frontend/src/contexts/ChatContext.tsx`
- `frontend/src/services/agentService.ts`
- `frontend/src/hooks/useAgent.ts`
- `frontend/src/components/chat/ChatInterface.tsx`
- `frontend/src/pages/Chat.tsx`

