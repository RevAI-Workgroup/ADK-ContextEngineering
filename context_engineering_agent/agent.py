"""
Phase 1 Context Engineering Agent - Google ADK with Ollama

This is the main agent file in ADK standard format.
Can be tested using: adk web
"""

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from src.core.tools import calculate, analyze_text, count_words, get_current_time

# Create the root agent using the proven pattern
root_agent = Agent(
    name="context_engineering_agent",
    model=LiteLlm(
        model="ollama_chat/qwen3:4b",
        temperature=0.7,
        max_tokens=4096
    ),
    description=(
        "An intelligent AI agent for answering questions and performing tasks "
        "using available tools. Capable of mathematical calculations, text analysis, "
        "and time zone queries."
    ),
    instruction=(
        "You are a helpful AI assistant with access to specialized tools.\n\n"
        "Your capabilities:\n"
        "- Answer questions accurately and concisely\n"
        "- Use tools when they help provide better answers\n"
        "- Explain your reasoning and which tools you used\n"
        "- Admit when you don't know something\n\n"
        "Available tools: calculate, analyze_text, count_words, get_current_time\n\n"
        "Guidelines:\n"
        "1. Use tools whenever they can improve your response\n"
        "2. For calculations, always use the 'calculate' tool\n"
        "3. For text analysis, use 'analyze_text' or 'count_words'\n"
        "4. For time queries, use 'get_current_time' with proper timezone format\n"
        "5. Provide clear, helpful responses based on tool results"
    ),
    tools=[calculate, analyze_text, count_words, get_current_time]
)
