"""
ADK Agent Wrapper for FastAPI integration.

This module wraps the ADK agent to provide both synchronous and
streaming interfaces for the FastAPI endpoints.
"""

import asyncio
import logging
import json
import time
import uuid
from typing import Dict, Any, List, AsyncGenerator, Optional
from datetime import datetime

from context_engineering_agent.agent import root_agent, TOOLS, INSTRUCTION
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from src.core.config import get_config

logger = logging.getLogger(__name__)


class ADKAgentWrapper:
    """
    Wrapper for the ADK agent to provide API-friendly interfaces.
    
    Provides both synchronous and streaming methods for agent interaction.
    Supports dynamic model switching with agent caching.
    """
    
    def __init__(self):
        """Initialize the ADK agent wrapper with model caching."""
        # Default agent and runner (for backward compatibility)
        self.agent = root_agent
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            agent=root_agent,
            app_name='agents',
            session_service=self.session_service
        )
        
        # Agent cache for different models
        self._agent_cache: Dict[str, Agent] = {
            "default": root_agent
        }
        self._runner_cache: Dict[str, Runner] = {
            "default": self.runner
        }
        
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # Load config for model settings
        try:
            self.config = get_config()
        except Exception as e:
            logger.warning(f"Could not load config: {e}")
            self.config = None
        
        logger.info("ADK Agent Wrapper initialized with dynamic model support")
    
    def _get_or_create_runner(self, model: Optional[str] = None) -> Runner:
        """
        Get or create a runner for the specified model.
        
        Args:
            model: Model name (e.g., "qwen3:4b", "llama2:7b"). 
                   If None, uses default model.
        
        Returns:
            Runner instance configured for the specified model
        """
        # Use default if no model specified
        if not model:
            return self._runner_cache["default"]
        
        # Check cache
        if model in self._runner_cache:
            logger.info(f"Using cached runner for model: {model}")
            return self._runner_cache[model]
        
        # Create new agent with specified model
        logger.info(f"Creating new agent for model: {model}")
        
        # Get model config from config file or use defaults
        temperature = 0.7
        max_tokens = 4096
        
        if self.config:
            temperature = self.config.get("models.ollama.primary_model.temperature", 0.7)
            max_tokens = self.config.get("models.ollama.primary_model.max_tokens", 4096)
        
        # Create new agent with the specified model
        new_agent = Agent(
            name=f"context_engineering_agent_{model.replace(':', '_')}",
            model=LiteLlm(
                model=f"ollama_chat/{model}",
                temperature=temperature,
                max_tokens=max_tokens
            ),
            description=(
                "An intelligent AI agent for answering questions and performing tasks "
                "using available tools. Capable of mathematical calculations, text analysis, "
                "and time zone queries."
            ),
            instruction=INSTRUCTION,
            tools=TOOLS
        )
        
        # Create runner for the new agent
        new_runner = Runner(
            agent=new_agent,
            app_name='agents',
            session_service=self.session_service
        )
        
        # Cache the agent and runner
        self._agent_cache[model] = new_agent
        self._runner_cache[model] = new_runner
        
        logger.info(f"Successfully created and cached agent for model: {model}")
        return new_runner
    
    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        include_thinking: bool = True,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a message through the ADK agent (synchronous).
        
        Args:
            message: User's message
            session_id: Optional session ID for conversation tracking
            include_thinking: Whether to include thinking steps
            model: Optional model name to use (e.g., "qwen3:4b", "llama2:7b")
            
        Returns:
            Dictionary containing response, thinking steps, tool calls, and metrics
        """
        logger.info(f"Processing message with model '{model or 'default'}': {message[:50]}...")
        start_time = time.time()
        
        try:
            # Get the appropriate runner for the specified model
            runner = self._get_or_create_runner(model)
            
            # Track the resolved model (use "default" if model is None)
            resolved_model = model if model else "default"
            
            # Generate unique IDs if needed
            if not session_id:
                session_id = f"session-{uuid.uuid4().hex[:8]}"
            user_id = "api-user"
            
            # Create message content
            content = types.Content(
                role='user',
                parts=[types.Part(text=message)]
            )
            
            # Run agent and collect events
            logger.info(f"Invoking agent via Runner for session {session_id}")
            
            # Use run_async since we're already in an async context
            # This avoids thread-safety issues with InMemorySessionService
            events_list = await self._run_agent_async(user_id, session_id, content, runner)
            
            logger.info(f"Received {len(events_list)} events from agent")
            
            # Process events to extract response
            response_text = ""
            tool_calls = []
            thinking_steps = []
            
            for idx, event in enumerate(events_list):
                event_type = type(event).__name__
                logger.debug(f"Processing event {idx}: {event_type}")
                
                # Extract text from content
                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text = part.text
                                logger.info(f"Extracted text from event {idx}: {text[:100]}")
                                response_text = text
                
                # Look for tool call information
                if 'tool' in event_type.lower():
                    tool_calls.append({
                        "name": event_type,
                        "description": f"Tool invocation: {event_type}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            if response_text:
                logger.info(f"Agent response received: {response_text[:200]}...")
            else:
                logger.warning(f"No response text extracted from {len(events_list)} events")
            
            # Build response data
            response_data = {
                "response": response_text,
                "thinking_steps": thinking_steps if include_thinking else None,
                "tool_calls": tool_calls if tool_calls else None,
                "model": resolved_model
            }
            
            # Calculate metrics
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            
            response_data["metrics"] = {
                "latency_ms": latency_ms,
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": session_id
            }
            
            # Store in session if session_id provided
            if session_id:
                if session_id not in self.sessions:
                    self.sessions[session_id] = {"messages": []}
                self.sessions[session_id]["messages"].append({
                    "message": message,
                    "response": response_data,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            logger.info(f"Message processed in {latency_ms:.2f}ms")
            return response_data
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            raise
    
    async def _run_agent_async(self, user_id: str, session_id: str, content, runner: Runner):
        """
        Helper method to run agent asynchronously using run_async.
        This avoids thread-safety issues with InMemorySessionService.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            content: Message content
            runner: Runner instance to use for this request
        """
        events_list = []
        try:
            # Create or get session
            session_created = False
            try:
                logger.info(f"Attempting to get existing session: {session_id}")
                existing_session = await self.session_service.get_session(
                    app_name='agents',
                    user_id=user_id,
                    session_id=session_id
                )
                logger.info(f"Found existing session: {existing_session.id}")
            except Exception as e:
                # Session doesn't exist, create it
                logger.info(f"Session not found ({type(e).__name__}), creating new session: {session_id}")
                try:
                    new_session = await self.session_service.create_session(
                        app_name='agents',
                        user_id=user_id,
                        session_id=session_id
                    )
                    session_created = True
                    logger.info(f"Successfully created session: {new_session.id}")
                    
                    # Verify we can retrieve it
                    verify_session = await self.session_service.get_session(
                        app_name='agents',
                        user_id=user_id,
                        session_id=session_id
                    )
                    logger.info(f"Verified session retrieval: {verify_session.id}")
                except Exception as create_error:
                    logger.error(f"Failed to create session: {create_error}", exc_info=True)
                    raise
            
            # Run the agent asynchronously using the provided runner
            logger.info(f"Starting async agent run for session {session_id} (created={session_created})")
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content
            ):
                events_list.append(event)
                event_type = type(event).__name__
                logger.debug(f"Event received: {event_type}")
            
            logger.info(f"Agent run complete, collected {len(events_list)} events")
        except Exception as e:
            logger.error(f"Error in _run_agent_async: {e}", exc_info=True)
            raise
        
        return events_list
    
    async def process_message_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
        model: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a message through the ADK agent with streaming updates.
        
        Yields events as the agent processes the message:
        - thinking: Agent thinking steps
        - tool_call: Tool invocation
        - response: Final response
        
        Args:
            message: User's message
            session_id: Optional session ID
            model: Optional model name to use (e.g., "qwen3:4b", "llama2:7b")
            
        Yields:
            Event dictionaries with type and data
        """
        logger.info(f"Processing message with streaming (model: '{model or 'default'}'): {message[:50]}...")
        
        try:
            # Get the appropriate runner for the specified model
            runner = self._get_or_create_runner(model)
            
            # Track the resolved model (use "default" if model is None)
            resolved_model = model if model else "default"
            
            # Generate unique IDs if needed
            if not session_id:
                session_id = f"session-{uuid.uuid4().hex[:8]}"
            user_id = "api-user"
            
            # Send initial thinking event
            yield {
                "type": "thinking",
                "data": {"message": "Processing your request..."}
            }
            
            # Ensure session exists before running agent
            try:
                # Try to get existing session
                existing_session = await asyncio.to_thread(
                    self.session_service.get_session_sync,
                    app_name='agents',
                    user_id=user_id,
                    session_id=session_id
                )
                logger.info(f"Using existing session: {session_id}")
            except Exception as e:
                # Session doesn't exist, create it
                logger.info(f"Session not found, creating new session: {session_id}")
                new_session = await asyncio.to_thread(
                    self.session_service.create_session_sync,
                    app_name='agents',
                    user_id=user_id,
                    session_id=session_id
                )
                logger.info(f"Created new session: {new_session.id}")
            
            # Create message content
            content = types.Content(
                role='user',
                parts=[types.Part(text=message)]
            )
            
            # Run agent and stream events using the model-specific runner
            events = await asyncio.to_thread(
                runner.run,
                user_id=user_id,
                session_id=session_id,
                new_message=content
            )
            
            # Stream events to client
            response_text = ""
            tool_calls = []
            thinking_steps = []
            
            for event in events:
                # Yield event info
                event_type = type(event).__name__
                
                if 'tool' in event_type.lower():
                    tool_call_data = {
                        "name": event_type,
                        "description": f"Tool invocation: {event_type}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    tool_calls.append(tool_call_data)
                    yield {
                        "type": "tool_call",
                        "data": {"message": f"{event_type}: Tool invocation: {event_type}"}
                    }
                
                # Extract text from content
                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                response_text = part.text
            
            # Send final response
            yield {
                "type": "response",
                "data": {
                    "response": response_text,
                    "thinking_steps": thinking_steps,
                    "tool_calls": tool_calls,
                    "model": resolved_model
                }
            }
            
        except Exception as e:
            logger.error(f"Error in streaming: {e}", exc_info=True)
            yield {
                "type": "error",
                "data": {"error": str(e)}
            }
    
    def _parse_agent_output(self, output: str, include_thinking: bool) -> Dict[str, Any]:
        """
        Parse ADK agent output to extract response, thinking, and tool calls.
        
        Args:
            output: Raw agent output
            include_thinking: Whether to include thinking steps
            
        Returns:
            Parsed response data
        """
        response_data = {
            "response": "",
            "thinking_steps": [],
            "tool_calls": []
        }
        
        lines = output.split("\n")
        
        # Extract thinking steps
        in_thinking = False
        thinking_buffer = []
        
        for line in lines:
            line = line.strip()
            
            # Detect thinking blocks
            if "<think>" in line:
                in_thinking = True
                continue
            if "</think>" in line:
                in_thinking = False
                if thinking_buffer:
                    response_data["thinking_steps"].append(" ".join(thinking_buffer))
                    thinking_buffer = []
                continue
            
            if in_thinking:
                thinking_buffer.append(line)
            
            # Detect tool calls
            if "tool_call:" in line.lower() or "calling tool:" in line.lower():
                # Extract tool name from line if possible
                tool_name = "unknown"
                if ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        tool_name = parts[0].strip().replace("tool_call", "").strip()
                
                response_data["tool_calls"].append({
                    "name": tool_name,
                    "description": line
                })
        
        # Extract final response (usually the last substantial output)
        # Filter out empty lines and metadata
        response_lines = [
            line for line in lines
            if line.strip()
            and not line.startswith("INFO:")
            and not line.startswith("DEBUG:")
            and "<think>" not in line
            and "</think>" not in line
            and "tool_call:" not in line.lower()
        ]
        
        if response_lines:
            response_data["response"] = "\n".join(response_lines[-5:])  # Last 5 lines as response
        
        if not include_thinking:
            response_data["thinking_steps"] = None
        
        return response_data
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available tools from the ADK agent.
        
        Returns:
            List of tool information dictionaries
        """
        # These are the tools from Phase 1
        tools = [
            {
                "name": "calculate",
                "description": "Perform mathematical calculations safely",
                "parameters": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate"
                    }
                }
            },
            {
                "name": "count_words",
                "description": "Count words in a text string",
                "parameters": {
                    "text": {
                        "type": "string",
                        "description": "Text to count words in"
                    }
                }
            },
            {
                "name": "get_current_time",
                "description": "Get current time in a specific timezone",
                "parameters": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone name (e.g., 'America/New_York')"
                    }
                }
            },
            {
                "name": "analyze_text",
                "description": "Analyze text and provide statistics",
                "parameters": {
                    "text": {
                        "type": "string",
                        "description": "Text to analyze"
                    }
                }
            }
        ]
        
        return tools
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool information dictionary or None if not found
        """
        tools = self.get_available_tools()
        for tool in tools:
            if tool["name"] == tool_name:
                return tool
        return None

