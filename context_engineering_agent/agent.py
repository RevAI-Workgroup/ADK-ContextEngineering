"""
Context Engineering Agent - Single Source of Truth

This is the main agent definition for the Context Engineering project.
It integrates Google ADK with Ollama for local LLM inference with tool calling.

Usage:
    - ADK CLI: adk run context_engineering_agent
    - ADK Web UI: adk web context_engineering_agent
    - Programmatic: from context_engineering_agent import root_agent

Configuration is loaded from configs/models.yaml and can be overridden
via environment variables.
"""

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from src.core.tools import calculate, analyze_text, count_words, get_current_time
from src.core.config import get_config
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Load configuration
try:
    config = get_config()

    # Get model configuration
    model_name = config.get("models.ollama.primary_model.name", "qwen3:4b")
    temperature = config.get("models.ollama.primary_model.temperature", 0.7)
    max_tokens = config.get("models.ollama.primary_model.max_tokens", 4096)

    logger.info(f"Initializing agent with model: ollama_chat/{model_name}")
    logger.debug(f"Model config - temp={temperature}, max_tokens={max_tokens}")

except Exception as e:
    # Fallback to defaults if config loading fails
    logger.warning(f"Config loading failed, using defaults: {e}")
    model_name = "qwen3:4b"
    temperature = 0.7
    max_tokens = 4096

# Define available tools
TOOLS = [calculate, analyze_text, count_words, get_current_time]

# Build instruction text
tool_names = [tool.__name__ for tool in TOOLS]
INSTRUCTION = (
    "You are a helpful AI assistant with access to specialized tools.\n\n"
    "CRITICAL FORMATTING REQUIREMENT:\n"
    "You MUST structure your response in this exact format:\n"
    "1. Start with <think>your reasoning process here</think>\n"
    "2. Then provide your final answer\n\n"
    "Example:\n"
    "<think>\n"
    "The user is asking about X. I should use tool Y because Z.\n"
    "Let me break down the problem: ...\n"
    "</think>\n\n"
    "Here is my answer: ...\n\n"
    "Your capabilities:\n"
    "- Answer questions accurately and concisely\n"
    "- Use tools when they help provide better answers\n"
    "- Explain your reasoning inside <think> tags\n"
    "- Admit when you don't know something\n\n"
    f"Available tools: {', '.join(tool_names)}\n\n"
    "Guidelines:\n"
    "1. ALWAYS start your response with <think> tags containing your reasoning\n"
    "2. Use tools whenever they can improve your response\n"
    "3. For calculations, always use the 'calculate' tool\n"
    "4. For text analysis, use 'analyze_text' or 'count_words'\n"
    "5. For time queries, use 'get_current_time' with proper timezone format\n"
    "6. Provide clear, helpful responses based on tool results\n"
    "7. IMPORTANT: When using get_current_time, always use the 'time' field (human-readable format) "
    "in your response to the user. Never use the 'iso_format' field as it is not user-friendly."
)

# Create the root agent
# This is the single source of truth for the agent definition
root_agent = Agent(
    name="context_engineering_agent",
    model=LiteLlm(
        model=f"ollama_chat/{model_name}",
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True
    ),
    description=(
        "An intelligent AI agent for answering questions and performing tasks "
        "using available tools. Capable of mathematical calculations, text analysis, "
        "and time zone queries."
    ),
    instruction=INSTRUCTION,
    tools=TOOLS
)

logger.info(f"Agent initialized successfully with {len(TOOLS)} tools")
