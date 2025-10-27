# Phase 1 - Real Working Example Analysis

## Source
**Repository**: https://github.com/jageenshukla/adk-ollama-tool
**Medium Article**: How to Build Ollama-Powered AI Agents with ADK, Tool Calling, and MCP Integration
**Clone Location**: `/tmp/adk-ollama-tool`

---

## Key Insights from Working Example

### 1. **Simplicity is Key** ✨

The working example is **remarkably simple**:
- Only **40 lines of code** for a complete working agent with tool calling
- Minimal dependencies: just `google-adk` and `litellm`
- No complex configuration files
- No session management needed for basic usage
- Direct tool registration as Python functions

### 2. **Actual Implementation Pattern**

#### Time Agent (Function Tool Example)

```python
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents import Agent
import datetime
from zoneinfo import ZoneInfo

# Define a tool as a simple Python function with docstring
def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city.

    Args:
        city (str): The name of the city for which to retrieve the current time.

    Returns:
        dict: status and result or error msg.
    """
    try:
        tz_identifier = ZoneInfo(city)
        now = datetime.datetime.now(tz_identifier)
        report = f'The current time in {city} is {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}'
        return {"status": "success", "report": report}
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to retrieve timezone information for {city}. Error: {str(e)}"
        }

# Create agent - that's it!
root_agent = Agent(
    name="time_agent",
    model=LiteLlm(model="ollama_chat/qwen3:14b"),
    description="Agent to answer questions about the current time in a city.",
    instruction="You are a helpful agent who can answer user questions about the current time in a city.",
    tools=[get_current_time]  # Just pass the function directly!
)
```

#### Math Agent (MCP Tool Example)

```python
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseServerParams
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

root_agent = Agent(
    name="math_agent",
    model=LiteLlm(model="ollama_chat/qwen3:14b"),
    description="Agent to answer questions about mathematical queries using MCP tools.",
    instruction="You are a helpful agent who can answer user questions about mathematical queries using MCP tools.",
    tools=[
        MCPToolset(
            connection_params=SseServerParams(url="http://localhost:4000/sse")
        )
    ]
)
```

### 3. **Critical Differences from Our Initial Plan**

| Aspect | Initial Plan | Real Example |
|--------|-------------|--------------|
| **Model Format** | `openai/qwen2.5:latest` (OpenAI-compatible) | `ollama_chat/qwen3:14b` (Direct Ollama) |
| **Environment Setup** | Required OPENAI_BASE_URL, OPENAI_API_KEY | None required! |
| **Tool Definition** | Complex registration system | Just pass function to tools=[] |
| **Configuration** | YAML files, complex config manager | None - all inline |
| **Running** | FastAPI, custom endpoints | `adk web` command (built-in UI) |
| **Session Management** | Implement from scratch | Not needed for basic usage |

### 4. **Model Choice: qwen3:14b**

The example uses **`ollama_chat/qwen3:14b`** specifically because:
- Has tool calling support
- Good reasoning capabilities for error correction (e.g., "tokyo" → "Asia/Tokyo")
- 14B parameter model - larger than typical 7B models
- Balance between performance and resource usage

### 5. **How to Run**

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install google-adk litellm

# Pull the model
ollama pull qwen3:14b

# Run the agent
adk web
```

That's it! The `adk web` command provides:
- Interactive web interface
- Automatic session management
- Built-in testing UI
- No FastAPI needed for development

---

## Implications for Our Phase 1 Implementation

### ✅ What We Should Do (Aligned with Real Example)

1. **Use Direct Ollama Integration**: `ollama_chat/model_name`
   - No OpenAI-compatible wrapper needed
   - Simpler and more direct

2. **Simple Tool Definition Pattern**:
   ```python
   def tool_name(param: type) -> return_type:
       """Docstring is critical - ADK uses it for tool description."""
       # Implementation
       return result

   # Register directly
   tools=[tool_name]
   ```

3. **Model Selection**: Use `qwen3:14b` or similar with confirmed tool support
   - Not qwen2.5:latest (might not have tool calling)
   - Check Ollama model page for "tools" capability

4. **Agent Structure**:
   ```python
   agent = Agent(
       name="descriptive_name",
       model=LiteLlm(model="ollama_chat/qwen3:14b"),
       description="What the agent does",
       instruction="System prompt / behavior instructions",
       tools=[list_of_tool_functions]
   )
   ```

5. **Use `adk web` for Development Testing**:
   - Built-in UI for quick testing
   - FastAPI is optional (we can add it for Phase 1 API requirements)

### ⚠️ What We Should Adjust

1. **Drop OpenAI-Compatible API Approach**:
   - The example proves direct Ollama works
   - No environment variables needed
   - Simpler configuration

2. **Simplify Tool Registration**:
   - No complex tool registry needed
   - Just create functions and pass them in a list

3. **Model Configuration**:
   - Update `configs/models.yaml` to specify `qwen3:14b`
   - Or make it easily switchable

4. **Skip Session Management for Phase 1**:
   - ADK handles it automatically with `adk web`
   - Can add custom session logic in later phases if needed

### ✅ What We Should Keep

1. **Evaluation Framework**: Still critical for measuring improvements
2. **FastAPI Endpoints**: Add on top of basic agent for programmatic access
3. **Configuration System**: Useful for flexibility, just simpler than planned
4. **Multiple Tools**: Implement 3-5 tools as planned
5. **Testing Strategy**: Unit and integration tests still important

---

## Revised Phase 1 Architecture

### Core Components

```
src/
├── core/
│   ├── agent.py           # ADK agent initialization (simplified)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── calculator.py  # Math operations
│   │   ├── text_tools.py  # Text analysis
│   │   └── time_tools.py  # Time/date (like example)
│   └── config.py          # Keep existing config system
├── api/
│   ├── main.py            # FastAPI wrapper around agent
│   └── models.py          # Pydantic schemas
└── evaluation/
    └── (keep existing)
```

### Implementation Priority

1. **Core Agent** (1 hour)
   - Create simple agent.py following example pattern
   - Use `ollama_chat/qwen3:14b`
   - Initialize with minimal config

2. **Basic Tools** (1 hour)
   - Implement 3-5 simple tools as functions
   - Follow docstring pattern from example
   - Test with `adk web`

3. **FastAPI Wrapper** (2 hours)
   - Create API layer around the agent
   - Expose POST /chat endpoint
   - Add GET /tools, /health

4. **Evaluation Integration** (1 hour)
   - Update evaluation script to use agent
   - Run benchmark comparison

---

## Updated Tool Implementation Pattern

### Simple Calculator Tool

```python
def calculate(expression: str) -> dict:
    """
    Perform basic arithmetic calculations.

    Args:
        expression (str): Mathematical expression (e.g., "2 + 2", "10 * 5")

    Returns:
        dict: Result with status and value or error message
    """
    try:
        # Safe eval with restricted namespace
        allowed_names = {"__builtins__": {}}
        result = eval(expression, allowed_names, {})
        return {"status": "success", "result": str(result)}
    except Exception as e:
        return {"status": "error", "error_message": f"Calculation failed: {str(e)}"}
```

### Text Analysis Tool

```python
def analyze_text(text: str) -> dict:
    """
    Analyze text and return basic statistics.

    Args:
        text (str): Text to analyze

    Returns:
        dict: Statistics including word count, character count, etc.
    """
    try:
        words = text.split()
        return {
            "status": "success",
            "word_count": len(words),
            "character_count": len(text),
            "sentence_count": text.count('.') + text.count('!') + text.count('?'),
            "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Analysis failed: {str(e)}"}
```

### Time Tool (From Example)

```python
from datetime import datetime
from zoneinfo import ZoneInfo

def get_current_time(city: str) -> dict:
    """
    Get current time in a specified city.

    Args:
        city (str): City name (e.g., "Tokyo", "America/New_York")

    Returns:
        dict: Current time with status
    """
    try:
        tz = ZoneInfo(city)
        now = datetime.now(tz)
        return {
            "status": "success",
            "time": now.strftime("%Y-%m-%d %H:%M:%S %Z%z"),
            "city": city
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Could not get time for {city}: {str(e)}"
        }
```

---

## Agent Initialization Code

### src/core/agent.py

```python
"""
ADK Agent implementation for Context Engineering project.
"""

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from typing import List, Callable
import logging

from .tools.calculator import calculate
from .tools.text_tools import analyze_text
from .tools.time_tools import get_current_time
from .config import get_config

logger = logging.getLogger(__name__)


class ContextEngineeringAgent:
    """Wrapper for ADK agent with Ollama backend."""

    def __init__(self, model_name: str = None):
        """
        Initialize the agent.

        Args:
            model_name: Ollama model to use (default from config)
        """
        config = get_config()

        # Get model name from config or use parameter
        if model_name is None:
            model_name = config.get("models.ollama.primary_model.name", "qwen3:14b")

        # Get model parameters
        temperature = config.get("models.ollama.primary_model.temperature", 0.7)
        max_tokens = config.get("models.ollama.primary_model.max_tokens", 4096)

        logger.info(f"Initializing agent with model: {model_name}")

        # Initialize LiteLLM model
        self.model = LiteLlm(
            model=f"ollama_chat/{model_name}",
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Define tools
        self.tools = [
            calculate,
            analyze_text,
            get_current_time
        ]

        # Create ADK agent
        self.agent = Agent(
            name="context_engineering_agent",
            model=self.model,
            description="An intelligent agent for answering questions and performing tasks using available tools.",
            instruction=(
                "You are a helpful AI assistant. Use the available tools when needed to answer questions accurately. "
                "Always explain your reasoning and which tools you used."
            ),
            tools=self.tools
        )

        logger.info(f"Agent initialized with {len(self.tools)} tools")

    def query(self, user_query: str) -> str:
        """
        Query the agent.

        Args:
            user_query: User's question or request

        Returns:
            Agent's response as string
        """
        logger.info(f"Processing query: {user_query[:100]}...")

        try:
            # Simple synchronous query
            response = self.agent.run(user_query)
            return response
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise

    def get_tool_info(self) -> List[dict]:
        """Get information about available tools."""
        return [
            {
                "name": tool.__name__,
                "description": tool.__doc__.split('\n')[0] if tool.__doc__ else "No description"
            }
            for tool in self.tools
        ]
```

---

## Configuration Update

### configs/models.yaml (Updated)

```yaml
ollama:
  base_url: "http://localhost:11434"
  timeout: 120

  primary_model:
    name: "qwen3:14b"  # Changed from qwen2.5:latest
    temperature: 0.7
    max_tokens: 4096
    top_p: 0.9
    top_k: 40

  # Alternative models (all with tool support)
  alternative_models:
    - name: "qwen3:14b"
      description: "Qwen 3 14B - Good tool calling and reasoning"
    - name: "mistral-small3.1"
      description: "Mistral Small - Fast with tool support"
    - name: "llama3.2"
      description: "Llama 3.2 - Meta's latest with tools"
```

---

## Running & Testing

### Development Testing

```bash
# Pull the model
ollama pull qwen3:14b

# Method 1: Use ADK's built-in UI
adk web

# Method 2: Use our FastAPI endpoint
uvicorn src.api.main:app --reload

# Method 3: Run evaluation
python scripts/run_phase1_evaluation.py
```

### Quick Manual Test

```python
# test_agent_manual.py
from src.core.agent import ContextEngineeringAgent

agent = ContextEngineeringAgent()

# Test calculator tool
print(agent.query("What is 15 multiplied by 7?"))

# Test time tool
print(agent.query("What's the current time in Tokyo?"))

# Test text analysis
print(agent.query("Analyze this text: The quick brown fox jumps over the lazy dog"))
```

---

## Key Takeaways

### ✅ What Works (Proven by Example)

1. **Direct Ollama Integration**: `ollama_chat/model_name` works perfectly
2. **Simple Tool Registration**: Just pass functions to tools=[]
3. **Docstrings are Critical**: ADK reads docstrings for tool descriptions
4. **Return Dictionaries**: Tools should return dict with status/result pattern
5. **Built-in UI**: `adk web` provides instant testing interface
6. **Model Choice Matters**: Use models with confirmed tool support (qwen3:14b works)

### 🎯 Our Advantage

We're building on top of this simple pattern with:
- **Evaluation Framework**: Measure improvements scientifically
- **Configuration System**: Easy model/parameter switching
- **API Layer**: Programmatic access beyond web UI
- **Multiple Tools**: Diverse capabilities
- **Testing**: Comprehensive unit and integration tests

### 🚀 Phase 1 Success Criteria (Updated)

1. Agent initialized with Ollama backend via LiteLLM ✓
2. 3-5 working tools with proper docstrings ✓
3. Tools callable by agent in response to queries ✓
4. FastAPI endpoints for programmatic access ✓
5. Evaluation shows improvement over Phase 0 ✓
6. Documentation and tests complete ✓

---

## Next Steps

1. **Implement Core Agent** (following example pattern)
2. **Create 3-5 Tools** (calculator, text, time, + 2 more)
3. **Add FastAPI Wrapper** (for our API requirements)
4. **Run Evaluation** (compare with Phase 0 baseline)
5. **Document Results** (Phase 1 summary)

**Estimated Time**: 4-6 hours (simplified from 7-12)

---

*Analysis Date: 2025-10-27*
*Based on: https://github.com/jageenshukla/adk-ollama-tool*
*Status: Ready to Implement*
