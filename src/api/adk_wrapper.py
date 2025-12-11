"""
ADK Agent Wrapper for FastAPI integration.

This module wraps the ADK agent to provide both synchronous and
streaming interfaces for the FastAPI endpoints.

IMPORTANT: Token streaming with tool calling uses Ollama's native Python SDK
directly instead of LiteLLM, as LiteLLM has known limitations with tool calling
during streaming mode with Ollama. See: https://github.com/BerriAI/litellm/issues/15399
"""

import asyncio
import json
import logging
import re
import time
import uuid
from contextlib import nullcontext
from typing import Dict, Any, List, AsyncGenerator, Optional, Tuple, Callable
from datetime import datetime

from context_engineering_agent.agent import root_agent, TOOLS, INSTRUCTION
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from src.core.config import get_config
# Direct LiteLLM import for accessing reasoning_content that ADK doesn't expose
import litellm
# Native Ollama client for proper tool calling support during streaming
import ollama
from src.core.tracing import trace_span, record_metric, get_tracer
from src.core.context_config import ContextEngineeringConfig
from src.core.modular_pipeline import ContextPipeline
from src.core.tools import search_knowledge_base, calculate, analyze_text, count_words, get_current_time
import hashlib
import sys

logger = logging.getLogger(__name__)


def _flush_logs():
    """Force flush all log handlers to ensure real-time output."""
    for handler in logger.handlers:
        handler.flush()
    for handler in logging.root.handlers:
        handler.flush()
    # Also flush stdout/stderr directly
    sys.stdout.flush()
    sys.stderr.flush()


class _NullSpan:
    """Mock span object that does nothing when tracing is unavailable."""

    def set_attribute(self, key: str, value: Any) -> None:
        """No-op method for compatibility when tracing is disabled."""
        pass


def _get_trace_context(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Get trace context, falling back to nullcontext if tracing isn't initialized.

    Args:
        name: Span name
        attributes: Optional span attributes

    Returns:
        Context manager that yields a span (real or mock)
    """
    try:
        return trace_span(name, attributes)
    except RuntimeError:
        # Tracing not initialized, use nullcontext with mock span
        logger.debug(f"Tracing not initialized, using nullcontext for span: {name}")
        return nullcontext(_NullSpan())


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
            agent=root_agent, app_name="agents", session_service=self.session_service
        )

        # Agent cache for different models
        self._agent_cache: Dict[str, Agent] = {"default": root_agent}
        self._runner_cache: Dict[str, Runner] = {"default": self.runner}

        self.sessions: Dict[str, Dict[str, Any]] = {}

        # Load config for model settings
        try:
            self.config = get_config()
        except Exception as e:
            logger.warning(f"Could not load config: {e}")
            self.config = None

        logger.info("ADK Agent Wrapper initialized with dynamic model support")

    def _get_config_hash(self, config: Optional[ContextEngineeringConfig]) -> str:
        """
        Generate a hash of the config to use as part of cache key.

        Args:
            config: Context engineering configuration

        Returns:
            Hash string representing the config state
        """
        if not config:
            logger.debug("Config is None, using 'no_config' hash")
            return "no_config"

        # Create a simple hash based on enabled techniques
        techniques = sorted(config.get_enabled_techniques())
        config_str = ",".join(techniques)
        hash_value = hashlib.md5(config_str.encode()).hexdigest()[:8]
        logger.debug(
            f"Config hash generated: {hash_value} from techniques: {techniques}"
        )
        return hash_value

    def _build_tools_list(self, config: Optional[ContextEngineeringConfig]) -> List:
        """
        Build list of tools based on configuration.

        Args:
            config: Context engineering configuration

        Returns:
            List of tool functions to provide to the agent
        """
        # Start with base tools
        tools = list(TOOLS)
        logger.debug(
            f"Base tools count: {len(tools)}, names: {[t.__name__ for t in tools]}"
        )

        # Add RAG-as-tool if enabled
        if config:
            logger.debug(
                f"Config provided, checking rag_tool_enabled: {config.rag_tool_enabled}"
            )
            if config.rag_tool_enabled:
                logger.info(
                    "✓ RAG-as-tool is ENABLED - Adding search_knowledge_base tool to agent"
                )
                tools.append(search_knowledge_base)
            else:
                logger.info(
                    "✗ RAG-as-tool is DISABLED - NOT adding search_knowledge_base tool"
                )
        else:
            logger.debug("No config provided, using base tools only")

        logger.info(
            f"Final tools list: {len(tools)} tools - {[t.__name__ for t in tools]}"
        )
        return tools

    def _is_reasoning_model(self, model: Optional[str]) -> bool:
        """
        Determine whether the supplied model is expected to emit explicit reasoning traces.

        Args:
            model: Model identifier provided by caller.

        Returns:
            True if the model is known to stream reasoning content, otherwise False.
        """
        # Enable reasoning extraction for all models by default
        # This ensures that if the model outputs <think> tags (which we now force via INSTRUCTION),
        # they will be properly parsed and displayed in the frontend
        if not model:
            return True  # Default models use reasoning format

        model_lower = model.lower()
        reasoning_keywords = [
            "deepseek-r1",
            "deepseek_r1",
            "deepseek-reasoner",
            "deepseek reasoner",
            "o1",
            "gpt-o1",
            "reasoning",
            "think",
            "qwen",   # Added: qwen models are instructed to use <think> tags
            "llama",  # Added: llama models are instructed to use <think> tags
            "mistral",
            "phi",
            "gemma",
        ]
        return any(keyword in model_lower for keyword in reasoning_keywords)

    def _segment_stream_text(
        self, text: str, in_reasoning_phase: bool, is_reasoning_model: bool, in_explicit_think_tag: bool = False
    ) -> Tuple[List[Tuple[str, str]], bool, bool]:
        """
        Split streamed text into reasoning and response segments.

        This method detects and separates reasoning content (inside <think> tags or similar markers)
        from final response content. It handles both explicit XML-style tags and natural language
        markers like "Answer:" or "Final Response:".

        Args:
            text: The raw text emitted by the model for this event.
            in_reasoning_phase: Whether the previous segment indicated we are inside a reasoning block.
            is_reasoning_model: Whether the current model is expected to emit reasoning traces.
            in_explicit_think_tag: Whether we're inside an explicit <think> tag (vs implicit reasoning).

        Returns:
            A tuple containing:
                - Ordered list of (segment_type, segment_text) tuples where segment_type is
                  either "reasoning" or "response".
                - Updated in_reasoning_phase flag reflecting the end state after processing ``text``.
                - Updated in_explicit_think_tag flag.
        """
        if not text:
            return [], in_reasoning_phase, in_explicit_think_tag

        # If the model is not reasoning-capable and we're not already in a reasoning block,
        # treat the entire segment as part of the final response.
        if not is_reasoning_model and not in_reasoning_phase:
            logger.debug(f"[Segment] Non-reasoning model, treating as response: {text[:50]}...")
            return [("response", text)], in_reasoning_phase, in_explicit_think_tag

        remaining = text
        segments: List[Tuple[str, str]] = []

        # Patterns for detecting reasoning blocks
        # Supports: <think>, <thinking>, <analysis>, <reasoning>, <thought>
        open_pattern = re.compile(
            r"<\s*(think|thinking|analysis|reasoning|thought)\s*>", re.IGNORECASE
        )
        close_pattern = re.compile(
            r"<\s*/\s*(think|thinking|analysis|reasoning|thought)\s*>", re.IGNORECASE
        )
        # Pattern to detect the start of a final answer
        answer_pattern = re.compile(
            r"(?:^|\n+)\s*(final answer|answer|final response|response|solution|conclusion)\s*:?",
            re.IGNORECASE,
        )
        # Pattern for explicit reasoning labels at the start
        reasoning_label_pattern = re.compile(
            r"^\s*(analysis|reasoning|thought|thinking|chain of thought|deliberation|let me think|i need to)\s*:?",
            re.IGNORECASE,
        )

        logger.debug(f"[Segment] Processing text (len={len(text)}, in_reasoning={in_reasoning_phase}, explicit_tag={in_explicit_think_tag}): {text[:100]}...")

        iteration_count = 0
        max_iterations = 100  # Safety guard

        while remaining and iteration_count < max_iterations:
            iteration_count += 1

            if in_reasoning_phase:
                # We're inside a reasoning block, look for the closing tag
                close_match = close_pattern.search(remaining)
                if close_match:
                    segment_text = remaining[: close_match.start()]
                    if segment_text:
                        logger.debug(f"[Segment] Found reasoning content before close tag: {len(segment_text)} chars")
                        segments.append(("reasoning", segment_text))
                    remaining = remaining[close_match.end() :]
                    in_reasoning_phase = False
                    in_explicit_think_tag = False  # Exited explicit tag
                    logger.debug(f"[Segment] Closed reasoning block, remaining: {len(remaining)} chars")
                    continue

                # ONLY check for answer markers if we're NOT inside explicit <think> tags
                # This prevents truncation when model writes "Answer:" inside its thinking
                if not in_explicit_think_tag:
                    answer_match = answer_pattern.search(remaining)
                    if answer_match:
                        if answer_match.start() > 0:
                            reasoning_part = remaining[: answer_match.start()]
                            if reasoning_part.strip():
                                logger.debug(f"[Segment] Reasoning before answer marker: {len(reasoning_part)} chars")
                                segments.append(("reasoning", reasoning_part))
                        remaining = remaining[answer_match.start() :]
                        in_reasoning_phase = False
                        logger.debug(f"[Segment] Found answer marker, exiting implicit reasoning phase")
                        continue
                
                # No close tag found (or answer marker when in explicit tag), all remaining text is reasoning
                if remaining:
                    logger.debug(f"[Segment] All remaining is reasoning: {len(remaining)} chars")
                    segments.append(("reasoning", remaining))
                remaining = ""
                break
            else:
                # We're not in a reasoning block

                # Check for explicit opening reasoning tag
                open_match = open_pattern.search(remaining)
                
                # Check for reasoning label at the start (e.g., "Reasoning:", "Let me think")
                reasoning_label_match = reasoning_label_pattern.match(remaining)
                
                if reasoning_label_match:
                    # Handle explicit reasoning labels
                    answer_match = answer_pattern.search(
                        remaining, reasoning_label_match.end()
                    )
                    if (
                        answer_match
                        and answer_match.start() > reasoning_label_match.end()
                    ):
                        split_index = answer_match.start()
                        reasoning_part = remaining[:split_index]
                        response_part = remaining[split_index:]

                        if reasoning_part.strip():
                            logger.debug(f"[Segment] Reasoning label block: {len(reasoning_part)} chars")
                            segments.append(("reasoning", reasoning_part))

                        if response_part:
                            logger.debug(f"[Segment] Response after label block: {len(response_part)} chars")
                            segments.append(("response", response_part))

                        remaining = ""
                        break

                    # No answer yet; treat the remainder as reasoning and keep phase active
                    # This is IMPLICIT reasoning (via label), not explicit <think> tag
                    logger.debug(f"[Segment] Reasoning label with no answer marker, continuing as implicit reasoning")
                    segments.append(("reasoning", remaining))
                    remaining = ""
                    in_reasoning_phase = True
                    in_explicit_think_tag = False  # Implicit reasoning
                    break

                if open_match:
                    # Found an opening reasoning tag
                    before_text = remaining[: open_match.start()]
                    if before_text:
                        logger.debug(f"[Segment] Response before think tag: {len(before_text)} chars")
                        segments.append(("response", before_text))
                    remaining = remaining[open_match.end() :]
                    in_reasoning_phase = True
                    in_explicit_think_tag = True  # EXPLICIT <think> tag
                    logger.debug(f"[Segment] Entered reasoning phase via <think> tag (explicit)")
                    continue

                # Fallback heuristics: many reasoning models emit "Answer:" style separators
                answer_match = answer_pattern.search(remaining)
                if answer_match and answer_match.start() > 0:
                    # Text before "Answer:" might be implicit reasoning
                    reasoning_part = remaining[: answer_match.start()]
                    response_part = remaining[answer_match.start() :]

                    if reasoning_part.strip():
                        logger.debug(f"[Segment] Implicit reasoning before answer: {len(reasoning_part)} chars")
                        segments.append(("reasoning", reasoning_part))

                    if response_part:
                        logger.debug(f"[Segment] Response after answer marker: {len(response_part)} chars")
                        segments.append(("response", response_part))

                    remaining = ""
                    break

                # No reasoning markers detected — treat the remainder as response text
                if remaining:
                    logger.debug(f"[Segment] No markers, treating as response: {len(remaining)} chars")
                    segments.append(("response", remaining))
                remaining = ""
                break

        if iteration_count >= max_iterations:
            logger.warning(f"[Segment] Max iterations reached, possible infinite loop. Remaining: {remaining[:100]}")

        logger.debug(f"[Segment] Result: {len(segments)} segments, still_in_reasoning={in_reasoning_phase}, explicit_tag={in_explicit_think_tag}")
        return segments, in_reasoning_phase, in_explicit_think_tag

    def _get_or_create_runner(
        self,
        model: Optional[str] = None,
        config: Optional[ContextEngineeringConfig] = None,
    ) -> Runner:
        """
        Get or create a runner for the specified model and configuration.

        Args:
            model: Model name (e.g., "qwen3:4b", "llama2:7b").
                   If None, uses default model.
            config: Optional configuration that affects tool availability

        Returns:
            Runner instance configured for the specified model and config
        """
        # Build cache key including config
        config_hash = self._get_config_hash(config)
        cache_key = f"{model or 'default'}_{config_hash}"

        # Check cache
        if cache_key in self._runner_cache:
            logger.info(f"Using cached runner for: {cache_key}")
            return self._runner_cache[cache_key]

        # Create new agent with specified model and config
        logger.info(
            f"Creating new agent for model: {model}, config_hash: {config_hash}"
        )

        # Get model config from config file or use defaults
        temperature = 0.7
        max_tokens = 4096

        if self.config:
            temperature = self.config.get(
                "models.ollama.primary_model.temperature", 0.7
            )
            max_tokens = self.config.get("models.ollama.primary_model.max_tokens", 4096)

        # Build tools list based on configuration
        tools = self._build_tools_list(config)
        logger.info(
            f"Agent will have {len(tools)} tools: {[t.__name__ for t in tools]}"
        )

        # Create new agent with the specified model
        # Sanitize model name for agent name (only alphanumeric and underscores)
        safe_model_name = re.sub(r"[^A-Za-z0-9_]", "_", model or "default")
        safe_model_name = re.sub(r"_+", "_", safe_model_name)
        safe_model_name = safe_model_name.strip("_")

        agent_description = (
            "An intelligent AI agent for answering questions and performing tasks "
            "using available tools. Capable of mathematical calculations, text analysis, "
            "time zone queries"
        )

        # Build custom instruction based on configuration
        # INSTRUCTION already includes the <think> tag requirement
        custom_instruction = INSTRUCTION

        # Add RAG capability to description and enhanced instructions if enabled
        if config and config.rag_tool_enabled:
            agent_description += ", and searching the knowledge base for information"

            # Enhance instructions with RAG-specific guidance
            # Note: INSTRUCTION already contains the critical <think> tag formatting requirement
            custom_instruction = (
                f"{INSTRUCTION}\n\n"
                "⚠️ IMPORTANT - Knowledge Base Search:\n"
                "You have access to a 'search_knowledge_base' tool.\n"
                "- Use it PROACTIVELY for ANY question that could benefit from documentation or data\n"
                "- Use it BEFORE saying you don't have information\n"
                "- Use it when users ask 'what', 'how', 'why', 'explain', or 'tell me about' anything\n"
                "- Even for seemingly simple questions, the knowledge base might have relevant details\n"
                "- If search returns no results, then you can say you don't have information\n\n"
                "Strategy: When in doubt, search the knowledge base first!\n\n"
                "REMINDER: Always start your response with <think>reasoning</think> tags!"
            )

        agent_description += "."

        new_agent = Agent(
            name=f"context_engineering_agent_{safe_model_name}_{config_hash}",
            model=LiteLlm(
                model=f"ollama_chat/{model}" if model else "ollama_chat/qwen3:4b",
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            ),
            description=agent_description,
            instruction=custom_instruction,
            tools=tools,
        )

        # Create runner for the new agent
        new_runner = Runner(
            agent=new_agent, app_name="agents", session_service=self.session_service
        )

        # Cache the agent and runner
        self._agent_cache[cache_key] = new_agent
        self._runner_cache[cache_key] = new_runner

        logger.info(f"Successfully created and cached agent: {cache_key}")
        return new_runner

    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        include_thinking: bool = True,
        model: Optional[str] = None,
        config: Optional[ContextEngineeringConfig] = None,
    ) -> Dict[str, Any]:
        """
        Process a message through the ADK agent (synchronous).

        Args:
            message: User's message
            session_id: Optional session ID for conversation tracking
            include_thinking: Whether to include thinking steps
            model: Optional model name to use (e.g., "qwen3:4b", "llama2:7b")
            config: Optional context engineering configuration

        Returns:
            Dictionary containing response, thinking steps, tool calls, and metrics
        """
        logger.info(
            f"Processing message with model '{model or 'default'}': {message[:50]}..."
        )
        start_time = time.time()
        resolved_model = model if model else "default"

        with _get_trace_context(
            "adk_wrapper.process_message",
            attributes={
                "model": resolved_model,
                "session_id": session_id or "none",
                "message_length": len(message),
                "include_thinking": include_thinking,
            },
        ) as span:
            try:
                # Initialize context engineering pipeline if config provided
                pipeline = None
                pipeline_context = None
                pipeline_metrics = {}

                if config:
                    logger.info(
                        f"Initializing context engineering pipeline with config: {config.get_enabled_techniques()}"
                    )
                    pipeline = ContextPipeline(config)

                    # Process message through pipeline before sending to agent
                    pipeline_context = pipeline.process(
                        query=message,
                        conversation_history=[],  # TODO: Get from session in future
                    )

                    # Get pipeline metrics
                    pipeline_metrics = pipeline.get_aggregated_metrics()
                    logger.info(
                        f"Pipeline processed in {pipeline_metrics.get('total_execution_time_ms', 0):.2f}ms"
                    )

                    # If pipeline modified the context, use the enriched version
                    if pipeline_context.context:
                        # Prepend pipeline context to the message
                        enriched_message = (
                            f"{pipeline_context.context}\n\nUser Query: {message}"
                        )
                        logger.info(
                            f"Enriched message with pipeline context ({len(pipeline_context.context)} chars)"
                        )
                    else:
                        enriched_message = message
                else:
                    enriched_message = message

                # Get the appropriate runner for the specified model
                runner = self._get_or_create_runner(model, config)

                # Generate unique IDs if needed
                if not session_id:
                    session_id = f"session-{uuid.uuid4().hex[:8]}"
                user_id = "api-user"

                # Create message content (use enriched message if pipeline was used)
                content = types.Content(
                    role="user", parts=[types.Part(text=enriched_message)]
                )

                # Run agent and collect events
                logger.info(f"Invoking agent via Runner for session {session_id}")

                # Use run_async since we're already in an async context
                # This avoids thread-safety issues with InMemorySessionService
                events_list = await self._run_agent_async(
                    user_id, session_id, content, runner
                )

                logger.info(f"Received {len(events_list)} events from agent")
                span.set_attribute("event_count", len(events_list))

                # Process events to extract response
                response_text = ""
                reasoning_text = ""  # For ADK 'thought' attribute
                tool_calls = []
                thinking_steps = []

                for idx, event in enumerate(events_list):
                    event_type = type(event).__name__
                    logger.debug(f"Processing event {idx}: {event_type}")

                    # Extract content from event
                    if hasattr(event, "content") and event.content:
                        if hasattr(event.content, "parts"):
                            for part in event.content.parts:
                                # CRITICAL: Check for 'thought' attribute first
                                # ADK/Gemini models store reasoning in part.thought, separate from part.text
                                if hasattr(part, "thought") and part.thought:
                                    thought_text = part.thought
                                    logger.info(f"[Sync] Thought/reasoning detected ({len(thought_text)} chars): {thought_text[:100]}...")
                                    reasoning_text += thought_text
                                
                                # Check for function call (tool usage)
                                if hasattr(part, "function_call") and part.function_call:
                                    func_call = part.function_call
                                    tool_name = getattr(func_call, 'name', 'unknown_tool')
                                    
                                    # Extract function arguments if available
                                    tool_args = {}
                                    if hasattr(func_call, "args"):
                                        try:
                                            if isinstance(func_call.args, dict):
                                                tool_args = func_call.args
                                            elif isinstance(func_call.args, str):
                                                import json
                                                tool_args = json.loads(func_call.args)
                                        except Exception as e:
                                            logger.warning(f"Could not parse tool args: {e}")
                                    
                                    tool_call_data = {
                                        "name": tool_name,
                                        "description": f"Tool invocation: {tool_name}",
                                        "parameters": tool_args if tool_args else None,
                                        "timestamp": datetime.utcnow().isoformat(),
                                    }
                                    tool_calls.append(tool_call_data)
                                    logger.info(f"[Sync] Tool call detected: {tool_name} with args: {tool_args}")
                                
                                # Check for function response (tool result)
                                if hasattr(part, "function_response") and part.function_response:
                                    func_response = part.function_response
                                    response_name = getattr(func_response, 'name', 'unknown')
                                    response_result = getattr(func_response, 'response', None)
                                    if response_result is None:
                                        response_result = getattr(func_response, 'result', str(func_response))
                                    
                                    # Update the corresponding tool call with the result
                                    for tc in tool_calls:
                                        if tc['name'] == response_name and tc.get('result') is None:
                                            tc['result'] = response_result
                                            logger.info(f"[Sync] Tool result added for: {response_name}")
                                            break
                                
                                # Extract text content (accumulate rather than overwrite)
                                if hasattr(part, "text") and part.text:
                                    text = part.text
                                    logger.info(
                                        f"Extracted text from event {idx}: {text[:100]}"
                                    )
                                    # Check for embedded <think> tags in text
                                    if "<think>" in text.lower() or "</think>" in text.lower():
                                        # Extract reasoning from <think> tags
                                        think_pattern = re.compile(r'<think>(.*?)</think>', re.DOTALL | re.IGNORECASE)
                                        matches = think_pattern.findall(text)
                                        for match in matches:
                                            if match.strip():
                                                reasoning_text += match.strip() + "\n"
                                                logger.info(f"[Sync] Extracted embedded reasoning ({len(match)} chars)")
                                        # Remove think tags from response text
                                        clean_text = think_pattern.sub('', text).strip()
                                        if clean_text:
                                            response_text = clean_text
                                    else:
                                        response_text = text

                    # Legacy fallback: Look for tool call in event type name
                    if "tool" in event_type.lower() and not any(tc for tc in tool_calls if tc.get('name') != event_type):
                        tool_calls.append(
                            {
                                "name": event_type,
                                "description": f"Tool invocation: {event_type}",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                
                # Convert reasoning to thinking_steps if we captured any
                if reasoning_text.strip():
                    thinking_steps = [reasoning_text.strip()]
                    logger.info(f"[Sync] Total reasoning captured: {len(reasoning_text)} chars")

                if response_text:
                    logger.info(f"Agent response received: {response_text[:200]}...")
                else:
                    logger.warning(
                        f"No response text extracted from {len(events_list)} events"
                    )

                # Build response data
                response_data = {
                    "response": response_text,
                    "thinking_steps": thinking_steps if include_thinking else None,
                    "tool_calls": tool_calls if tool_calls else None,
                    "model": resolved_model,
                }

                # Calculate metrics
                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000

                response_data["metrics"] = {
                    "latency_ms": latency_ms,
                    "timestamp": datetime.utcnow().isoformat(),
                    "session_id": session_id,
                }

                # Store in session if session_id provided
                if session_id:
                    if session_id not in self.sessions:
                        self.sessions[session_id] = {"messages": []}
                    self.sessions[session_id]["messages"].append(
                        {
                            "message": message,
                            "response": response_data,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

                logger.info(f"Message processed in {latency_ms:.2f}ms")
                return response_data

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                raise

    async def _run_agent_async(
        self, user_id: str, session_id: str, content, runner: Runner
    ):
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
        with _get_trace_context(
            "adk_wrapper._run_agent_async",
            attributes={"user_id": user_id, "session_id": session_id},
        ) as span:
            try:
                # Create or get session
                session_created = False
                try:
                    logger.info(f"Attempting to get existing session: {session_id}")
                    existing_session = await self.session_service.get_session(
                        app_name="agents", user_id=user_id, session_id=session_id
                    )
                    logger.info(f"Found existing session: {existing_session.id}")
                except Exception as e:
                    # Session doesn't exist, create it
                    logger.info(
                        f"Session not found ({type(e).__name__}), creating new session: {session_id}"
                    )
                    try:
                        new_session = await self.session_service.create_session(
                            app_name="agents", user_id=user_id, session_id=session_id
                        )
                        session_created = True
                        logger.info(f"Successfully created session: {new_session.id}")

                        # Verify we can retrieve it
                        verify_session = await self.session_service.get_session(
                            app_name="agents", user_id=user_id, session_id=session_id
                        )
                        logger.info(f"Verified session retrieval: {verify_session.id}")
                    except Exception as create_error:
                        logger.error(
                            f"Failed to create session: {create_error}", exc_info=True
                        )
                        raise

                span.set_attribute("session_created", session_created)

                # Run the agent asynchronously using the provided runner
                logger.info(
                    f"Starting async agent run for session {session_id} (created={session_created})"
                )
                async for event in runner.run_async(
                    user_id=user_id, session_id=session_id, new_message=content
                ):
                    events_list.append(event)
                    event_type = type(event).__name__
                    logger.debug(f"Event received: {event_type}")

                logger.info(f"Agent run complete, collected {len(events_list)} events")
                span.set_attribute("event_count", len(events_list))
            except Exception as e:
                span.set_attribute("error", str(e))
                logger.error(f"Error in _run_agent_async: {e}", exc_info=True)
                raise

            return events_list

    async def process_message_stream_tokens(
        self,
        message: str,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[ContextEngineeringConfig] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a message through the ADK agent with token-level streaming.

        Yields individual tokens as they're generated for a more responsive UX.
        This is different from process_message_stream which sends complete text chunks.

        Args:
            message: User's message
            session_id: Optional session ID
            model: Optional model name to use
            config: Optional context engineering configuration

        Yields:
            Event dictionaries with token-level updates
        """
        logger.info(
            f"Processing message with token streaming (model: '{model or 'default'}'): {message[:50]}..."
        )
        _flush_logs()

        try:
            # Get the appropriate runner for the specified model
            runner = self._get_or_create_runner(model, config)

            # Track the resolved model
            resolved_model = model if model else "default"

            # Detect if this is a reasoning-capable model (used for heuristics only)
            is_reasoning_model = self._is_reasoning_model(model)

            # Generate unique IDs if needed
            if not session_id:
                session_id = f"session-{uuid.uuid4().hex[:8]}"
            user_id = "api-user"

            # Send initial thinking event
            yield {
                "type": "thinking",
                "data": {"message": "Processing your request..."},
            }

            # Initialize context engineering pipeline if config provided
            pipeline = None
            pipeline_context = None
            enriched_message = message
            # Cache pipeline metrics and metadata for propagation to client
            pipeline_metrics = None
            pipeline_metadata = None
            enabled_techniques = None

            if config:
                logger.info(
                    f"Initializing context engineering pipeline with config: {config.get_enabled_techniques()}"
                )
                _flush_logs()
                pipeline = ContextPipeline(config)
                enabled_techniques = config.get_enabled_techniques()

                yield {
                    "type": "thinking",
                    "data": {
                        "message": f"Running context engineering: {', '.join(enabled_techniques)}"
                    },
                }

                # Process message through pipeline
                pipeline_context = pipeline.process(
                    query=message, conversation_history=[]
                )

                # Get aggregated metrics after processing
                pipeline_metrics = pipeline.get_aggregated_metrics()
                pipeline_metadata = pipeline_context.metadata

                logger.info(
                    f"Pipeline processed in {pipeline_metrics.get('total_execution_time_ms', 0):.2f}ms "
                    f"with {len(pipeline_metrics.get('enabled_modules', []))} enabled modules"
                )

                # Send early metadata event with pipeline information
                yield {
                    "type": "thinking",
                    "data": {
                        "message": f"Pipeline execution complete. Enabled modules: {', '.join(pipeline_metrics.get('enabled_modules', []))}"
                    },
                }

                # If pipeline modified the context, use the enriched version
                if pipeline_context.context:
                    enriched_message = (
                        f"{pipeline_context.context}\n\nUser Query: {message}"
                    )
                    logger.info(
                        f"Enriched message with pipeline context ({len(pipeline_context.context)} chars)"
                    )

            # Create message content
            content = types.Content(
                role="user", parts=[types.Part(text=enriched_message)]
            )

            # Run agent and stream tokens as they arrive
            logger.info(f"Invoking agent with token streaming for session {session_id}")
            _flush_logs()

            current_reasoning = ""
            current_response = ""
            tool_calls = []  # Track tool calls during streaming
            in_reasoning_phase = False
            in_explicit_think_tag = False  # Track if we're inside explicit <think> tags
            # With stream=True in LiteLLM, we get real token-level streaming from Ollama
            # No need for artificial delays

            # Ensure session exists before running agent
            # Use the same session creation logic as _run_agent_async
            try:
                # Try to get existing session
                logger.info(f"Attempting to get existing session: {session_id}")
                try:
                    _existing_session = await self.session_service.get_session(
                        app_name="agents", user_id=user_id, session_id=session_id
                    )
                    logger.info(f"Found existing session: {_existing_session.id}")
                except Exception as get_error:
                    # Session doesn't exist, create it
                    logger.info(
                        f"Session not found ({type(get_error).__name__}), creating new session: {session_id}"
                    )
                    try:
                        new_session = await self.session_service.create_session(
                            app_name="agents", user_id=user_id, session_id=session_id
                        )
                        logger.info(f"Successfully created session: {new_session.id}")

                        # Verify we can retrieve it
                        verify_session = await self.session_service.get_session(
                            app_name="agents", user_id=user_id, session_id=session_id
                        )
                        logger.info(f"Verified session retrieval: {verify_session.id}")
                    except Exception as create_error:
                        logger.error(
                            f"Failed to create session: {create_error}", exc_info=True
                        )
                        yield {
                            "type": "error",
                            "data": {
                                "error": f"Failed to create session: {str(create_error)}"
                            },
                        }
                        return
            except Exception as session_error:
                logger.error(
                    f"Unexpected session error: {session_error}", exc_info=True
                )
                yield {
                    "type": "error",
                    "data": {"error": f"Session error: {str(session_error)}"},
                }
                return

            # Stream events directly from the agent as they arrive
            # This prevents the WebSocket from timing out while waiting for all events
            logger.info(f"Starting async agent stream for session {session_id}")

            event_count = 0
            last_event_time = asyncio.get_event_loop().time()
            EVENT_TIMEOUT = 120.0  # 120 seconds max between events

            # Initialize Smart Buffer for tag fragmentation prevention
            stream_buffer = ""

            try:
                agent_stream = runner.run_async(
                    user_id=user_id, session_id=session_id, new_message=content
                )

                async for event in agent_stream:
                    # Update last event time
                    last_event_time = asyncio.get_event_loop().time()

                    event_count += 1
                    event_type = type(event).__name__
                    logger.info(f"[Token Streaming] Event {event_count}: {event_type}")

                    # Extract text from content
                    if hasattr(event, "content") and event.content:
                        if hasattr(event.content, "parts"):
                            for part_idx, part in enumerate(event.content.parts):
                                part_type = type(part).__name__
                                
                                # Log all relevant Part attributes for debugging
                                part_text = getattr(part, 'text', None)
                                part_thought = getattr(part, 'thought', None)
                                part_func_call = getattr(part, 'function_call', None)
                                part_func_response = getattr(part, 'function_response', None)
                                
                                logger.info(
                                    f"[Token Streaming] Event {event_count}, Part {part_idx}: "
                                    f"text={repr(part_text[:50] if part_text else None)}, "
                                    f"thought={repr(part_thought[:50] if part_thought else None) if part_thought else None}, "
                                    f"func_call={bool(part_func_call)}, func_response={bool(part_func_response)}"
                                )

                                # CRITICAL: Check for 'thought' attribute first
                                # ADK/Gemini models store reasoning in part.thought, separate from part.text
                                # This is how models like Qwen3 expose their internal thinking process
                                if hasattr(part, "thought") and part.thought:
                                    try:
                                        thought_text = part.thought
                                        logger.info(
                                            f"[Token Streaming] 🧠 THOUGHT detected (length={len(thought_text)}): "
                                            f"{repr(thought_text[:100])}{'...' if len(thought_text) > 100 else ''}"
                                        )
                                        
                                        # Stream thought content directly as reasoning
                                        current_reasoning += thought_text
                                        yield {
                                            "type": "reasoning_token",
                                            "data": {
                                                "token": thought_text,
                                                "cumulative_reasoning": current_reasoning,
                                            },
                                        }
                                        logger.info(
                                            f"[Token Streaming] Cumulative reasoning (from thought) now {len(current_reasoning)} chars"
                                        )
                                        await asyncio.sleep(0)
                                    except Exception as thought_error:
                                        logger.error(
                                            f"Error processing thought part: {thought_error}",
                                            exc_info=True,
                                        )

                                # Extract text and stream chunks as they arrive
                                # With stream=True, LiteLLM emits text in real-time chunks from Ollama
                                if hasattr(part, "text") and part.text:
                                    try:
                                        text = part.text
                                        logger.info(
                                            f"[Token Streaming] Received chunk (length={len(text)}): "
                                            f"{repr(text[:100])}{'...' if len(text) > 100 else ''}"
                                        )

                                        # Append to stream buffer
                                        stream_buffer += text

                                        # Check if buffer ends with a partial tag
                                        # Patterns to detect incomplete tags:
                                        # - '<' at end (start of any tag)
                                        # - '</' at end (start of closing tag)
                                        # - '<think' or '</think' without '>' (incomplete tag)
                                        # - Any '<' followed by characters but no '>' at the end
                                        partial_tag_patterns = [
                                            r'<\s*$',  # Just '<' or '< ' at end
                                            r'<\s*/\s*$',  # Just '</' at end
                                            r'<\s*[a-zA-Z][^>]{0,30}$',  # Opening tag started but not closed
                                            r'<\s*/\s*[a-zA-Z][^>]{0,30}$',  # Closing tag started but not closed
                                        ]
                                        
                                        partial_tag_match = None
                                        for pattern in partial_tag_patterns:
                                            match = re.search(pattern, stream_buffer)
                                            if match:
                                                partial_tag_match = match
                                                break
                                        
                                        text_to_process = ""
                                        if partial_tag_match:
                                            # Split: safe part before the partial tag, and the partial tag itself
                                            partial_start = partial_tag_match.start()
                                            safe_to_process = stream_buffer[:partial_start]
                                            partial_tag = stream_buffer[partial_start:]
                                            
                                            logger.info(
                                                f"[Token Streaming] Partial tag detected: {repr(partial_tag)} "
                                                f"(holding back {len(partial_tag)} chars, safe={len(safe_to_process)} chars)"
                                            )
                                            
                                            text_to_process = safe_to_process
                                            stream_buffer = partial_tag  # Keep partial tag for next iteration
                                        else:
                                            # No partial tag - process everything
                                            text_to_process = stream_buffer
                                            stream_buffer = ""  # Clear buffer
                                            logger.debug(f"[Token Streaming] No partial tag, processing all {len(text_to_process)} chars")
                                        
                                        # Only process if we have text
                                        if text_to_process:
                                            # Segment the text into reasoning and response parts
                                            segments, in_reasoning_phase, in_explicit_think_tag = (
                                                self._segment_stream_text(
                                                    text=text_to_process,
                                                    in_reasoning_phase=in_reasoning_phase,
                                                    is_reasoning_model=is_reasoning_model,
                                                    in_explicit_think_tag=in_explicit_think_tag,
                                                )
                                            )

                                            if not segments:
                                                logger.debug(
                                                    "[Token Streaming] No segments detected, skipping"
                                                )
                                                continue

                                            # Stream each segment immediately without artificial delays
                                            for segment_type, segment_text in segments:
                                                if not segment_text:
                                                    continue

                                                logger.info(
                                                    f"[Token Streaming] YIELDING {segment_type.upper()} segment "
                                                    f"(len={len(segment_text)}): {repr(segment_text[:80])}{'...' if len(segment_text) > 80 else ''}"
                                                )

                                                # Stream the chunk as-is (no artificial tokenization)
                                                if segment_type == "reasoning":
                                                    current_reasoning += segment_text
                                                    yield {
                                                        "type": "reasoning_token",
                                                        "data": {
                                                            "token": segment_text,
                                                            "cumulative_reasoning": current_reasoning,
                                                        },
                                                    }
                                                    logger.debug(
                                                        f"[Token Streaming] Cumulative reasoning now {len(current_reasoning)} chars"
                                                    )
                                                else:
                                                    current_response += segment_text
                                                    yield {
                                                        "type": "token",
                                                        "data": {
                                                            "token": segment_text,
                                                            "cumulative_response": current_response,
                                                        },
                                                    }
                                                    logger.debug(
                                                        f"[Token Streaming] Cumulative response now {len(current_response)} chars"
                                                    )
                                                
                                                # No artificial delays - stream naturally as chunks arrive
                                                # Allow other async tasks to run with minimal yield
                                                await asyncio.sleep(0)

                                            logger.debug(
                                                f"[Token Streaming] Segment complete "
                                                f"(reasoning_chars={len(current_reasoning)}, response_chars={len(current_response)})"
                                            )
                                    except Exception as text_processing_error:
                                        logger.error(
                                            f"Error processing text part: {text_processing_error}",
                                            exc_info=True,
                                        )
                                        yield {
                                            "type": "error",
                                            "data": {
                                                "error": f"Error processing response text: {str(text_processing_error)}",
                                                "partial_response": current_response,
                                            },
                                        }
                                        # Continue to next part
                                        continue

                                # Check for function call (tool usage)
                                if hasattr(part, "function_call"):
                                    func_call = part.function_call
                                    if func_call:
                                        tool_name = (
                                            func_call.name
                                            if hasattr(func_call, "name")
                                            else "unknown_tool"
                                        )
                                        
                                        # Extract function arguments if available
                                        tool_args = {}
                                        if hasattr(func_call, "args"):
                                            try:
                                                if isinstance(func_call.args, dict):
                                                    tool_args = func_call.args
                                                elif isinstance(func_call.args, str):
                                                    import json
                                                    tool_args = json.loads(func_call.args)
                                            except Exception as e:
                                                logger.warning(f"Could not parse tool args: {e}")
                                        
                                        tool_call_data = {
                                            "name": tool_name,
                                            "description": f"Tool invocation: {tool_name}",
                                            "parameters": tool_args if tool_args else None,
                                            "timestamp": datetime.utcnow().isoformat(),
                                        }
                                        tool_calls.append(tool_call_data)
                                        
                                        logger.info(
                                            f"[Token Streaming] Tool call detected: {tool_name} with args: {tool_args}"
                                        )
                                        # Emit full tool call data (not just message) for frontend display
                                        yield {
                                            "type": "tool_call",
                                            "data": {
                                                "name": tool_name,
                                                "description": f"Calling tool: {tool_name}",
                                                "parameters": tool_args if tool_args else None,
                                                "timestamp": datetime.utcnow().isoformat(),
                                            },
                                        }
                                
                                # Check for function response (tool result)
                                if hasattr(part, "function_response"):
                                    func_response = part.function_response
                                    if func_response:
                                        response_name = getattr(func_response, 'name', 'unknown')
                                        response_result = getattr(func_response, 'response', None)
                                        
                                        # Try to extract result from response
                                        if response_result is None:
                                            # Try alternative attribute names
                                            response_result = getattr(func_response, 'result', None)
                                            if response_result is None:
                                                response_result = str(func_response)
                                        
                                        logger.info(
                                            f"[Token Streaming] Tool result received: {response_name} = {str(response_result)[:100]}..."
                                        )
                                        
                                        # Emit tool result event for frontend to update tool call
                                        yield {
                                            "type": "tool_result",
                                            "data": {
                                                "name": response_name,
                                                "result": response_result,
                                                "timestamp": datetime.utcnow().isoformat(),
                                            },
                                        }

                # After loop: Process any remaining buffer content
                if stream_buffer.strip():
                    logger.info(
                        f"[Token Streaming] Processing leftover buffer content ({len(stream_buffer)} chars): '{stream_buffer[:50]}...'"
                    )
                    segments, in_reasoning_phase, in_explicit_think_tag = (
                        self._segment_stream_text(
                            text=stream_buffer,
                            in_reasoning_phase=in_reasoning_phase,
                            is_reasoning_model=is_reasoning_model,
                            in_explicit_think_tag=in_explicit_think_tag,
                        )
                    )
                    
                    for segment_type, segment_text in segments:
                        if not segment_text:
                            continue
                        
                        if segment_type == "reasoning":
                            current_reasoning += segment_text
                            yield {
                                "type": "reasoning_token",
                                "data": {
                                    "token": segment_text,
                                    "cumulative_reasoning": current_reasoning,
                                },
                            }
                        else:
                            current_response += segment_text
                            yield {
                                "type": "token",
                                "data": {
                                    "token": segment_text,
                                    "cumulative_response": current_response,
                                },
                            }
                        
                        await asyncio.sleep(0)

                logger.info(
                    f"[Token Streaming] Completed streaming {event_count} events"
                )

            except asyncio.CancelledError:
                logger.warning("[Token Streaming] Stream cancelled by client")
                yield {"type": "error", "data": {"error": "Stream cancelled by client"}}
                return
            except asyncio.TimeoutError:
                logger.error(
                    f"[Token Streaming] Timeout after {EVENT_TIMEOUT}s waiting for model response"
                )
                yield {
                    "type": "error",
                    "data": {
                        "error": f"Model response timeout after {EVENT_TIMEOUT}s. The model may be too large or busy.",
                        "suggestion": "Try a smaller model or wait and retry",
                    },
                }
                return
            except ConnectionError as conn_error:
                logger.error(
                    f"[Token Streaming] Connection error: {conn_error}", exc_info=True
                )
                yield {
                    "type": "error",
                    "data": {
                        "error": f"Connection error: {str(conn_error)}",
                        "suggestion": "Check if Ollama is running and accessible",
                    },
                }
                return
            except Exception as stream_error:
                error_type = type(stream_error).__name__
                error_msg = str(stream_error)
                logger.error(
                    f"[Token Streaming] {error_type} during agent stream: {error_msg}",
                    exc_info=True,
                )

                # Provide more helpful error messages based on error type
                if "model" in error_msg.lower() and "not found" in error_msg.lower():
                    yield {
                        "type": "error",
                        "data": {
                            "error": f"Model not found: {model}",
                            "suggestion": "Check if the model is installed in Ollama. Run: ollama pull "
                            + (model or "qwen3:4b"),
                        },
                    }
                elif (
                    "connection" in error_msg.lower() or "connect" in error_msg.lower()
                ):
                    yield {
                        "type": "error",
                        "data": {
                            "error": "Cannot connect to Ollama",
                            "suggestion": "Ensure Ollama is running: ollama serve",
                        },
                    }
                elif "memory" in error_msg.lower() or "oom" in error_msg.lower():
                    yield {
                        "type": "error",
                        "data": {
                            "error": "Out of memory",
                            "suggestion": "Try a smaller model or free up system resources",
                        },
                    }
                else:
                    yield {
                        "type": "error",
                        "data": {
                            "error": f"{error_type}: {error_msg}",
                            "suggestion": "Check the backend logs for more details",
                        },
                    }
                return

            # Send completion signal with model info and pipeline metrics/metadata
            reasoning_length = (
                len(current_reasoning.strip()) if current_reasoning.strip() else 0
            )
            response_length = len(current_response.strip())
            
            logger.info(
                f"[Token Streaming] COMPLETE - Model: {resolved_model}, "
                f"Reasoning: {reasoning_length} chars, Response: {response_length} chars, "
                f"Events processed: {event_count}"
            )
            
            # Log summary of what was extracted
            if reasoning_length > 0:
                logger.info(f"[Token Streaming] Reasoning preview: {current_reasoning[:200]}...")
            else:
                logger.warning("[Token Streaming] No reasoning content was extracted from the model response")

            complete_data = {
                "model": resolved_model,
                "reasoning_length": reasoning_length if is_reasoning_model else 0,
                "response_length": response_length,
            }

            # Include pipeline metrics, metadata, and enabled techniques if available
            if pipeline_metrics is not None:
                complete_data["pipeline_metrics"] = pipeline_metrics
                logger.debug(f"Including pipeline metrics: {pipeline_metrics}")

            if pipeline_metadata is not None:
                complete_data["pipeline_metadata"] = pipeline_metadata
                logger.debug(
                    f"Including pipeline metadata: {list(pipeline_metadata.keys())}"
                )

            if enabled_techniques is not None:
                complete_data["enabled_techniques"] = enabled_techniques
                logger.debug(f"Including enabled techniques: {enabled_techniques}")

            # Include tool calls if any were detected
            if tool_calls:
                complete_data["tool_calls"] = tool_calls
                logger.info(f"[Token Streaming] Including {len(tool_calls)} tool call(s) in complete event")

            yield {"type": "complete", "data": complete_data}

        except Exception as e:
            logger.error(f"Error in token streaming: {e}", exc_info=True)
            yield {"type": "error", "data": {"error": str(e)}}

    async def process_message_stream_litellm(
        self,
        message: str,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[ContextEngineeringConfig] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream tokens using LiteLLM directly to access reasoning_content.
        
        This method bypasses ADK's abstraction to get access to LiteLLM's
        reasoning_content field which contains the model's thinking process
        from Qwen and other thinking-capable models.
        
        Args:
            message: User's message
            session_id: Optional session ID
            model: Optional model name (e.g., "qwen3:8b")
            config: Optional context engineering configuration
            
        Yields:
            Dictionary events for reasoning_token, token, tool_call, complete, error
        """
        resolved_model = model if model else "qwen3:4b"
        logger.info(
            f"[LiteLLM Streaming] Processing with model '{resolved_model}': {message[:50]}..."
        )
        
        current_reasoning = ""
        current_response = ""
        tool_calls = []  # Track tool calls during streaming
        
        try:
            # Build the full model name for LiteLLM
            litellm_model = f"ollama_chat/{resolved_model}"
            
            # Build system message with our instruction
            system_message = {"role": "system", "content": INSTRUCTION}
            
            # Process pipeline context if config provided
            enriched_message = message
            pipeline_metrics = {}
            if config:
                pipeline = ContextPipeline(config)
                pipeline_context = pipeline.process(
                    query=message,
                    conversation_history=[],
                )
                pipeline_metrics = pipeline.get_aggregated_metrics()
                
                if pipeline_context.context:
                    enriched_message = f"{pipeline_context.context}\n\nUser Query: {message}"
                    logger.info(
                        f"[LiteLLM Streaming] Enriched message with pipeline context ({len(pipeline_context.context)} chars)"
                    )
            
            # Build messages
            messages = [
                system_message,
                {"role": "user", "content": enriched_message}
            ]
            
            # IMPORTANT: Do NOT pass tools to LiteLLM for streaming mode
            # Ollama's reasoning_content (thinking) feature is DISABLED when tools are provided
            # The model will answer directly and show its thinking process
            # For tool functionality, use the ADK streaming method instead
            logger.info(f"[LiteLLM Streaming] Starting stream WITHOUT tools (enables reasoning_content)")
            
            # Call LiteLLM directly with streaming - NO TOOLS to enable reasoning
            response = litellm.completion(
                model=litellm_model,
                messages=messages,
                api_base="http://localhost:11434",
                stream=True,
                # tools=None intentionally - passing tools disables Ollama's reasoning mode
            )
            
            chunk_count = 0
            
            for chunk in response:
                chunk_count += 1
                
                if not chunk.choices:
                    continue
                    
                delta = chunk.choices[0].delta
                
                # Check for reasoning_content (LiteLLM extracts <think> tags here)
                # This is the model's thinking/deliberation process
                reasoning = getattr(delta, 'reasoning_content', None)
                if reasoning:
                    current_reasoning += reasoning
                    logger.debug(f"[LiteLLM Streaming] Chunk {chunk_count}: reasoning ({len(reasoning)} chars)")
                    yield {
                        "type": "reasoning_token",
                        "data": {
                            "token": reasoning,
                            "cumulative_reasoning": current_reasoning,
                        },
                    }
                    await asyncio.sleep(0)
                
                # Check for content (the actual response)
                content = getattr(delta, 'content', None)
                if content:
                    current_response += content
                    logger.debug(f"[LiteLLM Streaming] Chunk {chunk_count}: content ({len(content)} chars)")
                    yield {
                        "type": "token",
                        "data": {
                            "token": content,
                            "cumulative_response": current_response,
                        },
                    }
                    await asyncio.sleep(0)
            
            # Log completion
            reasoning_length = len(current_reasoning.strip())
            response_length = len(current_response.strip())
            
            logger.info(
                f"[LiteLLM Streaming] COMPLETE - Model: {resolved_model}, "
                f"Reasoning: {reasoning_length} chars, Response: {response_length} chars, "
                f"Chunks: {chunk_count}"
            )
            
            if reasoning_length > 0:
                logger.info(f"[LiteLLM Streaming] Reasoning preview: {current_reasoning[:200]}...")
            else:
                logger.warning("[LiteLLM Streaming] No reasoning_content was received from LiteLLM")
            
            # Send completion
            # Note: This streaming mode prioritizes showing reasoning over tool execution
            # For tool functionality, use Token Streaming = OFF which uses ADK's run_async
            complete_data = {
                "model": resolved_model,
                "reasoning_length": reasoning_length,
                "response_length": response_length,
                "pipeline_metrics": pipeline_metrics,
            }
            
            # Include tool calls if any were detected
            if tool_calls:
                complete_data["tool_calls"] = tool_calls
                logger.info(f"[Token Streaming] Including {len(tool_calls)} tool call(s) in complete event")
            
            yield {
                "type": "complete",
                "data": complete_data,
            }
            
        except Exception as e:
            logger.error(f"[LiteLLM Streaming] Error: {e}", exc_info=True)
            yield {
                "type": "error",
                "data": {
                    "error": str(e),
                    "suggestion": "Check if Ollama is running and the model is available",
                },
            }

    def _build_ollama_tools(self, config: Optional[ContextEngineeringConfig] = None) -> List[Dict[str, Any]]:
        """
        Build tool definitions in Ollama's expected format.
        
        Args:
            config: Optional configuration to include RAG tool
            
        Returns:
            List of tool definitions for Ollama API
        """
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "Evaluate a mathematical expression safely. Supports +, -, *, /, //, %, and ** operators.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "Mathematical expression to evaluate, e.g. '2 + 2' or '3**4'"
                            }
                        },
                        "required": ["expression"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "Get the current time in a specific city or timezone. Use timezone identifiers like 'America/New_York', 'Europe/London', 'Asia/Tokyo'.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "City name or timezone identifier (e.g., 'America/New_York', 'Europe/Paris', 'Asia/Tokyo')"
                            }
                        },
                        "required": ["city"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_text",
                    "description": "Analyze text and return comprehensive statistics including word count, character count, sentence count, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The text to analyze"
                            }
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "count_words",
                    "description": "Count the number of words in a text string.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The text to count words in"
                            }
                        },
                        "required": ["text"]
                    }
                }
            }
        ]
        
        # Add RAG tool if enabled
        if config and config.rag_tool_enabled:
            tools.append({
                "type": "function",
                "function": {
                    "name": "search_knowledge_base",
                    "description": "Search the knowledge base for relevant documents and information. Use this PROACTIVELY for any question that could benefit from documentation or external data.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query describing what information you need"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of documents to retrieve (default: 5)"
                            }
                        },
                        "required": ["query"]
                    }
                }
            })
            
        return tools
    
    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """
        Execute a tool by name with the given arguments.
        
        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments to pass to the tool
            
        Returns:
            Tool execution result
        """
        # Map tool names to actual functions
        tool_map: Dict[str, Callable] = {
            "calculate": calculate,
            "get_current_time": get_current_time,
            "analyze_text": analyze_text,
            "count_words": count_words,
            "search_knowledge_base": search_knowledge_base,
        }
        
        if tool_name not in tool_map:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            tool_func = tool_map[tool_name]
            result = tool_func(**tool_args)
            logger.info(f"[Tool Execution] {tool_name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"[Tool Execution] Error executing {tool_name}: {e}", exc_info=True)
            return {"error": f"Tool execution failed: {str(e)}"}

    async def process_message_stream_native_ollama(
        self,
        message: str,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[ContextEngineeringConfig] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream tokens using Ollama's native Python SDK with PROPER tool calling support.
        
        UPDATED: Uses stream=True for ALL calls, allowing real-time streaming of 
        reasoning/content BEFORE tool execution. This solves the "frozen UI" issue
        where reasoning appeared in bulk only after the model finished thinking.
        
        The approach:
        1. Use stream=True to get real-time token streaming
        2. Stream reasoning/content tokens as they arrive (user sees thinking immediately)
        3. Accumulate tool calls from the stream
        4. After stream completes, execute accumulated tools and continue the loop
        
        Args:
            message: User's message
            session_id: Optional session ID
            model: Optional model name (e.g., "qwen3:8b")
            config: Optional context engineering configuration
            
        Yields:
            Dictionary events for reasoning_token, token, tool_call, tool_result, complete, error
        """
        resolved_model = model if model else "qwen3:4b"
        logger.info(
            f"[Native Ollama] Processing with model '{resolved_model}': {message[:50]}..."
        )
        _flush_logs()
        
        start_time = time.time()
        
        # State tracking for the entire conversation
        all_tool_calls = []
        
        try:
            client = ollama.AsyncClient()
            system_message = {"role": "system", "content": INSTRUCTION}
            
            # 1. Pipeline & Context Setup
            enriched_message = message
            pipeline_metrics = {}
            enabled_techniques = []
            
            if config:
                enabled_techniques = config.get_enabled_techniques()
                yield {
                    "type": "thinking",
                    "data": {"message": f"Running context engineering: {', '.join(enabled_techniques)}"},
                }
                
                pipeline = ContextPipeline(config)
                pipeline_context = pipeline.process(query=message, conversation_history=[])
                pipeline_metrics = pipeline.get_aggregated_metrics()
                
                if pipeline_context.context:
                    enriched_message = f"{pipeline_context.context}\n\nUser Query: {message}"
                    logger.info(
                        f"[Native Ollama] Enriched message with pipeline context ({len(pipeline_context.context)} chars)"
                    )
            
            # 2. Build Tools & Initial Messages
            tools = self._build_ollama_tools(config)
            logger.info(f"[Native Ollama] Using {len(tools)} tools: {[t['function']['name'] for t in tools]}")
            
            messages = [
                system_message,
                {"role": "user", "content": enriched_message}
            ]
            
            # 3. Agentic Loop
            max_iterations = 10
            iteration = 0
            
            # Track final response stats
            final_reasoning_len = 0
            final_response_len = 0

            while iteration < max_iterations:
                iteration += 1
                logger.info(f"[Native Ollama] Iteration {iteration}: Streaming response with tools...")
                _flush_logs()
                
                if iteration == 1:
                    yield {
                        "type": "thinking",
                        "data": {"message": "Processing your request..."},
                    }

                # STATE FOR THIS TURN
                current_turn_content = ""
                current_turn_reasoning = ""
                current_turn_tool_calls = []
                
                # Helper state for segmentation
                in_reasoning_phase = False
                in_explicit_think_tag = False
                is_reasoning_model = self._is_reasoning_model(resolved_model)

                # STREAMING CALL WITH TOOLS (Now enabled!)
                # Newer Ollama versions support streaming + tool calls together
                stream = await client.chat(
                    model=resolved_model,
                    messages=messages,
                    tools=tools,
                    stream=True,  # ✅ ENABLED: Allows reasoning to stream BEFORE tools execute
                )

                async for chunk in stream:
                    # Parse the chunk
                    # Ollama SDK objects: chunk.message.content, chunk.message.tool_calls, chunk.message.thinking
                    
                    # A. Handle Explicit "Thinking" field (DeepSeek/Newer Models)
                    chunk_thinking = getattr(chunk.message, 'thinking', None)
                    if chunk_thinking:
                        current_turn_reasoning += chunk_thinking
                        final_reasoning_len += len(chunk_thinking)
                        yield {
                            "type": "reasoning_token",
                            "data": {
                                "token": chunk_thinking,
                                "cumulative_reasoning": current_turn_reasoning,
                            },
                        }
                        await asyncio.sleep(0)

                    # B. Handle Content (Reasoning OR Final Answer)
                    chunk_content = chunk.message.content or ""
                    if chunk_content:
                        # Use existing segmentation logic to distinguish <think> vs response
                        segments, in_reasoning_phase, in_explicit_think_tag = self._segment_stream_text(
                            chunk_content, in_reasoning_phase, is_reasoning_model, in_explicit_think_tag
                        )
                        
                        for seg_type, seg_text in segments:
                            if not seg_text:
                                continue
                            if seg_type == "reasoning":
                                current_turn_reasoning += seg_text
                                final_reasoning_len += len(seg_text)
                                yield {
                                    "type": "reasoning_token",
                                    "data": {"token": seg_text, "cumulative_reasoning": current_turn_reasoning}
                                }
                                await asyncio.sleep(0)
                            else:
                                current_turn_content += seg_text
                                final_response_len += len(seg_text)
                                yield {
                                    "type": "token",
                                    "data": {"token": seg_text, "cumulative_response": current_turn_content}
                                }
                                await asyncio.sleep(0)

                    # C. Handle Tool Calls (Accumulate them from stream)
                    if chunk.message.tool_calls:
                        for tc in chunk.message.tool_calls:
                            # Avoid duplicates - check if this tool call is already accumulated
                            if tc not in current_turn_tool_calls:
                                current_turn_tool_calls.append(tc)

                # END OF STREAM FOR THIS TURN
                logger.info(
                    f"[Native Ollama] Stream complete for iteration {iteration}: "
                    f"reasoning={len(current_turn_reasoning)} chars, "
                    f"content={len(current_turn_content)} chars, "
                    f"tool_calls={len(current_turn_tool_calls)}"
                )
                _flush_logs()
                
                # 4. Decide: Execute Tools OR Finish
                if current_turn_tool_calls:
                    logger.info(f"[Native Ollama] Processing {len(current_turn_tool_calls)} tool call(s)")
                    _flush_logs()
                    
                    # Build the assistant message to add to history
                    # We need to reconstruct it since we streamed
                    assistant_msg = {
                        "role": "assistant",
                        "content": current_turn_content if current_turn_content else None,
                        "tool_calls": current_turn_tool_calls
                    }
                    messages.append(assistant_msg)

                    # Execute each tool
                    for tool_call in current_turn_tool_calls:
                        # Normalize tool call data - handle both object attributes and dict access
                        if hasattr(tool_call, 'function'):
                            func = tool_call.function
                            tool_name = getattr(func, 'name', 'unknown') if hasattr(func, 'name') else func.get("name", "unknown")
                            tool_args = getattr(func, 'arguments', {}) if hasattr(func, 'arguments') else func.get("arguments", {})
                        else:
                            func = tool_call.get("function", {})
                            tool_name = func.get("name", "unknown")
                            tool_args = func.get("arguments", {})
                        
                        # Handle arguments - might be string or dict
                        if isinstance(tool_args, str):
                            try:
                                tool_args = json.loads(tool_args)
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse tool arguments for {tool_name}: {e}")
                                tool_args = {}

                        logger.info(f"[Native Ollama] Executing tool: {tool_name} with args: {tool_args}")
                        _flush_logs()

                        # Notify Frontend of tool call
                        tool_call_data = {
                            "name": tool_name,
                            "description": f"Calling tool: {tool_name}",
                            "parameters": tool_args,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                        yield {
                            "type": "tool_call",
                            "data": tool_call_data,
                        }
                        await asyncio.sleep(0)

                        # Execute the tool
                        tool_result = self._execute_tool(tool_name, tool_args)
                        
                        # Track for final completion event
                        all_tool_calls.append({"name": tool_name, "parameters": tool_args, "result": tool_result})

                        # Notify Frontend of result
                        yield {
                            "type": "tool_result",
                            "data": {
                                "name": tool_name,
                                "result": tool_result,
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        }
                        await asyncio.sleep(0)
                        
                        # Add tool result to message history
                        tool_result_str = json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result)
                        messages.append({
                            "role": "tool",
                            "content": tool_result_str,
                        })
                    
                    # Continue loop to let model process tool results...
                    continue
                else:
                    # No tools called -> This was the final answer.
                    logger.info("[Native Ollama] No tool calls, conversation complete.")
                    break

            # Handle max iterations
            if iteration >= max_iterations:
                logger.warning(f"[Native Ollama] Max iterations ({max_iterations}) reached")
                yield {
                    "type": "error",
                    "data": {
                        "error": "Maximum tool call iterations reached",
                        "suggestion": "The model may be stuck in a tool-calling loop",
                    },
                }
                return

            # 5. Final Completion Event
            execution_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                f"[Native Ollama] COMPLETE - Model: {resolved_model}, "
                f"Reasoning: {final_reasoning_len} chars, Response: {final_response_len} chars, "
                f"Tool calls: {len(all_tool_calls)}, Iterations: {iteration}, "
                f"Execution time: {execution_time_ms:.0f}ms"
            )
            
            yield {
                "type": "complete",
                "data": {
                    "model": resolved_model,
                    "reasoning_length": final_reasoning_len,
                    "response_length": final_response_len,
                    "execution_time_ms": round(execution_time_ms),
                    "pipeline_metrics": pipeline_metrics,
                    "enabled_techniques": enabled_techniques,
                    "tool_calls": all_tool_calls if all_tool_calls else None
                }
            }

        except ollama.ResponseError as e:
            logger.error(f"[Native Ollama] Ollama ResponseError: {e}", exc_info=True)
            yield {
                "type": "error",
                "data": {
                    "error": f"Ollama error: {str(e)}",
                    "suggestion": "Check if the model is installed. Run: ollama pull " + resolved_model,
                },
            }
        except Exception as e:
            logger.error(f"[Native Ollama] Error: {e}", exc_info=True)
            
            error_msg = str(e)
            suggestion = "Check the backend logs for more details"
            
            if "connection" in error_msg.lower() or "connect" in error_msg.lower():
                suggestion = "Ensure Ollama is running: ollama serve"
            elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                suggestion = f"Check if the model is installed. Run: ollama pull {resolved_model}"
            
            yield {
                "type": "error",
                "data": {
                    "error": error_msg,
                    "suggestion": suggestion,
                },
            }

    async def process_message_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[ContextEngineeringConfig] = None,
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
            config: Optional context engineering configuration

        Yields:
            Event dictionaries with type and data
        """
        logger.info(
            f"Processing message with streaming (model: '{model or 'default'}'): {message[:50]}..."
        )

        try:
            # Get the appropriate runner for the specified model and config
            runner = self._get_or_create_runner(model, config)

            # Track the resolved model (use "default" if model is None)
            resolved_model = model if model else "default"

            # Generate unique IDs if needed
            if not session_id:
                session_id = f"session-{uuid.uuid4().hex[:8]}"
            user_id = "api-user"

            # Send initial thinking event
            yield {
                "type": "thinking",
                "data": {"message": "Processing your request..."},
            }

            # Initialize context engineering pipeline if config provided
            pipeline = None
            pipeline_context = None
            pipeline_metrics = {}

            if config:
                logger.info(
                    f"Initializing context engineering pipeline with config: {config.get_enabled_techniques()}"
                )
                pipeline = ContextPipeline(config)

                yield {
                    "type": "thinking",
                    "data": {
                        "message": f"Running context engineering modules: {', '.join(config.get_enabled_techniques())}"
                    },
                }

                # Process message through pipeline before sending to agent
                pipeline_context = pipeline.process(
                    query=message,
                    conversation_history=[],  # TODO: Get from session in future
                )

                # Get pipeline metrics
                pipeline_metrics = pipeline.get_aggregated_metrics()
                logger.info(
                    f"Pipeline processed in {pipeline_metrics.get('total_execution_time_ms', 0):.2f}ms"
                )

                # If pipeline modified the context, use the enriched version
                if pipeline_context.context:
                    enriched_message = (
                        f"{pipeline_context.context}\n\nUser Query: {message}"
                    )
                    logger.info(
                        f"Enriched message with pipeline context ({len(pipeline_context.context)} chars)"
                    )
                else:
                    enriched_message = message
            else:
                enriched_message = message

            # Ensure session exists before running agent
            try:
                # Try to get existing session
                _existing_session = await asyncio.to_thread(
                    self.session_service.get_session_sync,
                    app_name="agents",
                    user_id=user_id,
                    session_id=session_id,
                )
                logger.info(f"Using existing session: {session_id}")
            except Exception as _get_error:
                # Session doesn't exist, create it
                logger.info(f"Session not found, creating new session: {session_id}")
                new_session = await asyncio.to_thread(
                    self.session_service.create_session_sync,
                    app_name="agents",
                    user_id=user_id,
                    session_id=session_id,
                )
                logger.info(f"Created new session: {new_session.id}")

            # Create message content (use enriched message if pipeline was used)
            content = types.Content(
                role="user", parts=[types.Part(text=enriched_message)]
            )

            # Run agent and stream events using the model-specific runner
            events = await asyncio.to_thread(
                runner.run, user_id=user_id, session_id=session_id, new_message=content
            )

            # Stream events to client
            response_text = ""
            tool_calls = []
            thinking_steps = []

            for event in events:
                # Yield event info
                event_type = type(event).__name__

                # Extract content from event
                if hasattr(event, "content") and event.content:
                    if hasattr(event.content, "parts"):
                        for part in event.content.parts:
                            # Check for function call (tool usage)
                            if hasattr(part, "function_call") and part.function_call:
                                func_call = part.function_call
                                tool_name = getattr(func_call, 'name', 'unknown_tool')
                                
                                # Extract function arguments if available
                                tool_args = {}
                                if hasattr(func_call, "args"):
                                    try:
                                        if isinstance(func_call.args, dict):
                                            tool_args = func_call.args
                                        elif isinstance(func_call.args, str):
                                            import json
                                            tool_args = json.loads(func_call.args)
                                    except Exception as e:
                                        logger.warning(f"Could not parse tool args: {e}")
                                
                                tool_call_data = {
                                    "name": tool_name,
                                    "description": f"Calling tool: {tool_name}",
                                    "parameters": tool_args if tool_args else None,
                                    "timestamp": datetime.utcnow().isoformat(),
                                }
                                tool_calls.append(tool_call_data)
                                
                                logger.info(f"[Standard Streaming] Tool call: {tool_name} with args: {tool_args}")
                                yield {
                                    "type": "tool_call",
                                    "data": tool_call_data,
                                }
                            
                            # Check for function response (tool result)
                            if hasattr(part, "function_response") and part.function_response:
                                func_response = part.function_response
                                response_name = getattr(func_response, 'name', 'unknown')
                                response_result = getattr(func_response, 'response', None)
                                if response_result is None:
                                    response_result = getattr(func_response, 'result', str(func_response))
                                
                                logger.info(f"[Standard Streaming] Tool result: {response_name} = {str(response_result)[:100]}...")
                                yield {
                                    "type": "tool_result",
                                    "data": {
                                        "name": response_name,
                                        "result": response_result,
                                        "timestamp": datetime.utcnow().isoformat(),
                                    },
                                }
                            
                            # Extract text content
                            if hasattr(part, "text") and part.text:
                                response_text = part.text

            # Send final response
            response_data = {
                "response": response_text,
                "thinking_steps": thinking_steps,
                "tool_calls": tool_calls,
                "model": resolved_model,
                "pipeline_metrics": pipeline_metrics if pipeline_metrics else None,
                "enabled_techniques": config.get_enabled_techniques() if config else [],
            }

            # Include pipeline metadata if available
            if pipeline_context:
                response_data["pipeline_metadata"] = pipeline_context.metadata

            yield {"type": "response", "data": response_data}

        except Exception as e:
            logger.error(f"Error in streaming: {e}", exc_info=True)
            yield {"type": "error", "data": {"error": str(e)}}

    def _parse_agent_output(
        self, output: str, include_thinking: bool
    ) -> Dict[str, Any]:
        """
        Parse ADK agent output to extract response, thinking, and tool calls.

        Args:
            output: Raw agent output
            include_thinking: Whether to include thinking steps

        Returns:
            Parsed response data
        """
        response_data = {"response": "", "thinking_steps": [], "tool_calls": []}

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

                response_data["tool_calls"].append(
                    {"name": tool_name, "description": line}
                )

        # Extract final response (usually the last substantial output)
        # Filter out empty lines and metadata
        response_lines = [
            line
            for line in lines
            if line.strip()
            and not line.startswith("INFO:")
            and not line.startswith("DEBUG:")
            and "<think>" not in line
            and "</think>" not in line
            and "tool_call:" not in line.lower()
        ]

        if response_lines:
            response_data["response"] = "\n".join(
                response_lines[-5:]
            )  # Last 5 lines as response

        if not include_thinking:
            response_data["thinking_steps"] = None

        return response_data

    def get_available_tools(
        self, config: Optional[ContextEngineeringConfig] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of available tools from the ADK agent.

        Args:
            config: Optional configuration to determine which tools are available

        Returns:
            List of tool information dictionaries
        """
        # Base tools that are always available
        tools = [
            {
                "name": "calculate",
                "description": "Perform mathematical calculations safely",
                "parameters": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate",
                    }
                },
            },
            {
                "name": "count_words",
                "description": "Count words in a text string",
                "parameters": {
                    "text": {"type": "string", "description": "Text to count words in"}
                },
            },
            {
                "name": "get_current_time",
                "description": "Get current time in a specific timezone",
                "parameters": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone name (e.g., 'America/New_York')",
                    }
                },
            },
            {
                "name": "analyze_text",
                "description": "Analyze text and provide statistics",
                "parameters": {
                    "text": {"type": "string", "description": "Text to analyze"}
                },
            },
        ]

        # Add RAG-as-tool if enabled in configuration
        if config and config.rag_tool_enabled:
            tools.append(
                {
                    "name": "search_knowledge_base",
                    "description": "Search the knowledge base for relevant documents. Use PROACTIVELY for any question that could benefit from documentation or external information. Always try this before saying you don't have information.",
                    "parameters": {
                        "query": {
                            "type": "string",
                            "description": "The search query describing what information you need",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of documents to retrieve (default: 5)",
                            "default": 5,
                        },
                    },
                }
            )

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
