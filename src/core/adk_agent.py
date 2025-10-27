"""
ADK Agent implementation for Context Engineering project.

This module provides the main agent class that integrates Google ADK with Ollama
for local LLM inference. The agent supports tool calling and can be configured
via YAML configuration files.

Based on the proven implementation pattern from:
https://github.com/jageenshukla/adk-ollama-tool
"""

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.genai import types
from typing import List, Callable, Dict, Any
import logging
from pathlib import Path
import uuid

from .tools import calculate, analyze_text, count_words, get_current_time
from .config import get_config

# Set up logging
logger = logging.getLogger(__name__)


class ContextEngineeringAgent:
    """
    Wrapper for ADK agent with Ollama backend via LiteLLM.

    This class provides a high-level interface to the Google ADK agent framework,
    configured to work with local Ollama models. It manages tool registration,
    model configuration, and provides a simple query interface.

    Attributes:
        model: LiteLLM model instance
        agent: ADK Agent instance
        runner: InMemoryRunner for executing agent queries
        tools: List of registered tool functions
        model_name: Name of the Ollama model being used
    """

    def __init__(self, model_name: str = None, tools: List[Callable] = None):
        """
        Initialize the ADK agent with Ollama backend.

        Args:
            model_name: Ollama model to use (default from config: qwen3:4b)
            tools: List of tool functions (default: all available tools)

        Raises:
            ValueError: If model configuration is invalid
            RuntimeError: If agent initialization fails
        """
        config = get_config()

        # Get model name from config or use parameter
        if model_name is None:
            model_name = config.get("models.ollama.primary_model.name", "qwen3:4b")

        # Get model parameters from config
        temperature = config.get("models.ollama.primary_model.temperature", 0.7)
        max_tokens = config.get("models.ollama.primary_model.max_tokens", 4096)

        self.model_name = model_name
        logger.info(f"Initializing ADK agent with model: ollama_chat/{model_name}")

        try:
            # Initialize LiteLLM model with Ollama backend
            # Format: "ollama_chat/{model_name}" for direct Ollama integration
            self.model = LiteLlm(
                model=f"ollama_chat/{model_name}",
                temperature=temperature,
                max_tokens=max_tokens
            )
            logger.debug(f"LiteLLM model initialized (temp={temperature}, max_tokens={max_tokens})")

        except Exception as e:
            logger.error(f"Failed to initialize LiteLLM model: {e}")
            raise RuntimeError(f"Model initialization failed: {e}") from e

        # Set up tools
        if tools is None:
            # Use all available tools by default
            self.tools = [
                calculate,
                analyze_text,
                count_words,
                get_current_time
            ]
        else:
            self.tools = tools

        logger.info(f"Registered {len(self.tools)} tools: {[t.__name__ for t in self.tools]}")

        # Build agent instruction
        instruction = self._build_instruction()

        try:
            # Create ADK agent
            # Following the proven pattern from jageenshukla/adk-ollama-tool
            self.agent = Agent(
                name="context_engineering_agent",
                model=self.model,
                description=(
                    "An intelligent AI agent for answering questions and performing tasks "
                    "using available tools. Capable of mathematical calculations, text analysis, "
                    "and time zone queries."
                ),
                instruction=instruction,
                tools=self.tools
            )
            logger.info("ADK agent initialized successfully")

            # Create InMemoryRunner for executing queries
            self.runner = InMemoryRunner(agent=self.agent)
            logger.debug("InMemoryRunner initialized")

        except Exception as e:
            logger.error(f"Failed to create ADK agent: {e}")
            raise RuntimeError(f"Agent creation failed: {e}") from e

    def _build_instruction(self) -> str:
        """
        Build the system instruction for the agent.

        Returns:
            str: Formatted instruction text
        """
        tool_names = [tool.__name__ for tool in self.tools]

        instruction = (
            "You are a helpful AI assistant with access to specialized tools.\n\n"
            "Your capabilities:\n"
            "- Answer questions accurately and concisely\n"
            "- Use tools when they help provide better answers\n"
            "- Explain your reasoning and which tools you used\n"
            "- Admit when you don't know something\n\n"
            f"Available tools: {', '.join(tool_names)}\n\n"
            "Guidelines:\n"
            "1. Use tools whenever they can improve your response\n"
            "2. For calculations, always use the 'calculate' tool\n"
            "3. For text analysis, use 'analyze_text' or 'count_words'\n"
            "4. For time queries, use 'get_current_time' with proper timezone format\n"
            "5. Provide clear, helpful responses based on tool results"
        )

        return instruction

    def query(self, user_query: str, user_id: str = "user", session_id: str = None) -> str:
        """
        Query the agent with a question or request.

        This is a synchronous blocking call that processes the query and returns
        the agent's response. Tool calls are handled automatically by ADK.

        Args:
            user_query: User's question or request
            user_id: User identifier for the session (default: "user")
            session_id: Session identifier for conversation continuity (default: generates new UUID)

        Returns:
            str: Agent's response

        Raises:
            RuntimeError: If query processing fails

        Examples:
            >>> agent = ContextEngineeringAgent()
            >>> response = agent.query("What is 15 multiplied by 7?")
            >>> print(response)
            "The result of 15 multiplied by 7 is 105."
        """
        if not user_query or not user_query.strip():
            raise ValueError("Query cannot be empty")

        # Generate a new session ID for each query if not provided
        # This ensures we start fresh each time
        if session_id is None:
            session_id = str(uuid.uuid4())

        logger.info(f"Processing query: {user_query[:100]}...")
        logger.debug(f"Session ID: {session_id}")

        try:
            # Create Content object for the user message
            content = types.Content(
                role='user',
                parts=[types.Part.from_text(text=user_query)]
            )

            # Run the agent using InMemoryRunner
            # The runner handles tool calling automatically
            response_parts = []
            for event in self.runner.run(
                user_id=user_id,
                session_id=session_id,
                new_message=content
            ):
                # Collect response text from events
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            response_parts.append(part.text)

            # Combine all response parts
            response = ' '.join(response_parts).strip()

            logger.info(f"Query completed successfully")
            logger.debug(f"Response: {response[:200]}...")

            return response

        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to process query: {e}") from e

    def get_tool_info(self) -> List[Dict[str, str]]:
        """
        Get information about available tools.

        Returns:
            List[Dict]: List of tool information dictionaries with 'name' and 'description'

        Examples:
            >>> agent = ContextEngineeringAgent()
            >>> tools = agent.get_tool_info()
            >>> for tool in tools:
            ...     print(f"{tool['name']}: {tool['description']}")
        """
        tool_info = []

        for tool in self.tools:
            # Extract first line of docstring as description
            description = "No description available"
            if tool.__doc__:
                doc_lines = tool.__doc__.strip().split('\n')
                first_line = doc_lines[0].strip()
                if first_line:
                    description = first_line

            tool_info.append({
                "name": tool.__name__,
                "description": description
            })

        return tool_info

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model configuration.

        Returns:
            Dict: Model configuration information
        """
        return {
            "model_name": self.model_name,
            "full_model_id": f"ollama_chat/{self.model_name}",
            "backend": "ollama",
            "framework": "google-adk",
            "num_tools": len(self.tools)
        }

    def __repr__(self) -> str:
        """String representation of the agent."""
        return (
            f"ContextEngineeringAgent("
            f"model={self.model_name}, "
            f"tools={len(self.tools)})"
        )
