# Testing Guide: Token Streaming & Reasoning Extraction Fix

## Quick Test Instructions

### Prerequisites

1. Ensure Ollama is running with `qwen3:4b` model:
   ```bash
   ollama serve
   ollama pull qwen3:4b
   ```

2. Backend is running:
   ```bash
   cd /Users/nektar/Project/ADK-ContextEngineering
   python -m src.api.main
   ```

3. Frontend is running:
   ```bash
   cd frontend
   npm run dev
   ```

---

## Test 1: True Token Streaming

### Objective
Verify that tokens stream immediately without delay

### Steps

1. Open frontend at `http://localhost:5173/chat`
2. Enable "Token Streaming" toggle (lightning bolt icon)
3. Send a query: **"What is 15 multiplied by 23? Explain your reasoning."**
4. Observe the response

### Expected Behavior

✅ **CORRECT:**
- Tokens appear immediately (within 1-2 seconds)
- Smooth, natural streaming effect
- Tokens appear one chunk at a time, continuously

❌ **INCORRECT (Old Behavior):**
- Long delay (3-5+ seconds) before ANY tokens appear
- Sudden "burst" of many words at once
- Artificial word-by-word typing with noticeable delays

### Backend Logs to Check

```
[Token Streaming] Received chunk: ... (length: X)
[Token Streaming] Streaming segment type=reasoning, length=Y
[Token Streaming] Streaming segment type=response, length=Z
```

---

## Test 2: Reasoning Extraction

### Objective
Verify that reasoning is properly extracted and displayed

### Steps

1. In the frontend chat, send: **"Calculate the area of a circle with radius 7"**
2. Wait for the response
3. Check the message display

### Expected Behavior

✅ **CORRECT:**
- You see TWO distinct sections:
  - **"Reasoning"** section with thinking process (collapsed or expanded)
  - **"Response"** section with the final answer
- The reasoning section is NOT empty
- Example reasoning content:
  ```
  The user wants the area of a circle with radius 7.
  I should use the calculate tool with the formula π * r²
  ```

❌ **INCORRECT (Old Behavior):**
- Only one section (response)
- No reasoning section OR reasoning section is empty
- All text appears in the response section

### Backend Logs to Check

```
[Token Streaming] Streaming segment type=reasoning, length=X
[Token Streaming] Streaming segment type=response, length=Y
```

---

## Test 3: Combined Test (Streaming + Reasoning)

### Objective
Verify both features work together seamlessly

### Steps

1. Enable "Token Streaming" toggle
2. Send: **"What is the current time in Tokyo? Walk me through your reasoning."**
3. Watch the response stream in real-time

### Expected Behavior

✅ **CORRECT:**
- Reasoning tokens stream first (appear in "Reasoning" section)
- Response tokens stream after (appear in "Response" section)
- No long initial delay
- Smooth streaming throughout

### Example Flow

```
[0.5s]  <thinking appears>
[1.0s]  "The user wants..."
[1.5s]  "I should use get_current_time..."
[2.0s]  "Let me calculate..."
[2.5s]  </thinking> <response starts>
[3.0s]  "The current time in Tokyo is..."
```

---

## Test 4: Different Models

### Objective
Verify fixes work with different Ollama models

### Steps

1. In frontend, click "Select Model" dropdown
2. Choose a different model (e.g., `llama2:7b`)
3. Send: **"Explain quantum computing in simple terms"**

### Expected Behavior

- ✅ Reasoning extraction works for all models
- ✅ Streaming is smooth regardless of model
- ✅ No errors in backend logs

---

## Test 5: RAG with Reasoning

### Objective
Verify reasoning works when RAG is enabled

### Steps

1. Open "Configuration" panel (left sidebar)
2. Enable "RAG as Tool"
3. Send: **"What do you know about Riri, Fifi, and Loulou?"**

### Expected Behavior

✅ **CORRECT:**
- Reasoning shows: "I should use search_knowledge_base tool..."
- Tool call appears in the response
- Final answer references the knowledge base results
- Reasoning is properly separated from response

---

## Debugging Tips

### Issue: No streaming at all

**Check:**
1. Backend logs for errors
2. WebSocket connection in browser DevTools (Network tab)
3. Ollama is running: `curl http://localhost:11434/api/version`

### Issue: Reasoning section is empty

**Check:**
1. Backend logs show `segment_type=reasoning`
2. Model is actually outputting `<think>` tags (check raw backend logs)
3. `_is_reasoning_model` returns `True` (add debug log)

### Issue: Streaming is still slow

**Check:**
1. Ollama model is fully loaded (first request is slower)
2. Network latency (WebSocket tab in DevTools)
3. Backend CPU usage (model inference speed)

---

## Performance Benchmarks

### Expected Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| Time to First Token | < 1s | Should be immediate |
| Token Rate | 20-50 tokens/s | Depends on model size |
| Reasoning Extraction | 100% | All `<think>` blocks captured |
| Backend CPU | < 50% | During streaming |

### How to Measure

1. **Time to First Token:** Stopwatch from send to first character
2. **Token Rate:** Count tokens, divide by total streaming time
3. **Reasoning Extraction:** Check frontend Reasoning section
4. **CPU:** `top` or Activity Monitor during streaming

---

## Rollback Plan

If critical issues arise:

```bash
# View recent commits
git log --oneline -5

# Revert specific commit
git revert <commit-hash>

# Or restore from backup
git checkout HEAD~1 -- context_engineering_agent/agent.py
git checkout HEAD~1 -- src/api/adk_wrapper.py
```

---

## Success Criteria

All tests pass when:

- ✅ Tokens appear within 1-2 seconds
- ✅ Streaming is smooth and continuous
- ✅ Reasoning section is populated
- ✅ No artificial delays or bursts
- ✅ Works with all models (qwen, llama, etc.)
- ✅ No errors in backend logs
- ✅ Frontend displays both reasoning and response correctly

---

## Contact

Report issues or questions:
- Create GitHub issue
- Check backend logs: `tail -f backend.log`
- Check frontend console: Browser DevTools → Console

---

**Last Updated:** 2025-11-24  
**Status:** Ready for Testing ✅

