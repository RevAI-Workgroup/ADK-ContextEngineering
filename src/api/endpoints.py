"""
API endpoint handlers for chat, metrics, and tools.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
import logging
from datetime import datetime, timezone
import httpx
import subprocess
import platform
import shutil
import asyncio

from src.api.adk_wrapper import ADKAgentWrapper
from src.evaluation.metrics import MetricsCollector
from src.core.tracing import trace_span, record_metric, record_throughput, update_memory_usage

logger = logging.getLogger(__name__)

# Initialize routers
chat_router = APIRouter()
metrics_router = APIRouter()
tools_router = APIRouter()
models_router = APIRouter()


# ============================================================================
# DEPENDENCY PROVIDERS
# ============================================================================

def get_adk_wrapper(request: Request) -> ADKAgentWrapper:
    """
    Dependency provider for ADK Agent Wrapper.
    
    Returns the singleton instance from app state.
    """
    return request.app.state.adk_wrapper


def get_metrics_collector(request: Request) -> MetricsCollector:
    """
    Dependency provider for Metrics Collector.
    
    Returns the singleton instance from app state.
    """
    return request.app.state.metrics_collector


# Pydantic models
class ChatMessage(BaseModel):
    """Chat message from user."""
    message: str = Field(..., description="User's message to the agent")
    session_id: Optional[str] = Field(None, description="Session ID for conversation tracking")
    include_thinking: bool = Field(True, description="Include agent thinking process in response")
    model: Optional[str] = Field(None, description="LLM model to use for this message")


class ChatResponse(BaseModel):
    """Response from agent."""
    response: str = Field(..., description="Agent's response")
    thinking_steps: Optional[List[str]] = Field(None, description="Agent's thinking process")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tools called by agent")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Response metrics")
    timestamp: str = Field(..., description="Response timestamp")
    model: Optional[str] = Field(None, description="Model used for this response")


class ToolInfo(BaseModel):
    """Information about a tool."""
    name: str
    description: str
    parameters: Dict[str, Any]


# ============================================================================
# CHAT ENDPOINTS
# ============================================================================

@chat_router.post("/chat", response_model=ChatResponse)
async def chat(
    message: ChatMessage,
    adk_wrapper: ADKAgentWrapper = Depends(get_adk_wrapper),
    metrics_collector: MetricsCollector = Depends(get_metrics_collector)
):
    """
    Send a message to the ADK agent and get a response.
    
    This endpoint provides synchronous chat interaction.
    For real-time streaming, use the WebSocket endpoint /api/chat/ws
    """
    import time
    start_time = time.time()
    
    # Record throughput
    record_throughput({"endpoint": "/api/chat"})
    
    with trace_span(
        "api.chat.post",
        attributes={
            "endpoint": "/api/chat",
            "model": message.model or "default",
            "session_id": message.session_id or "none",
            "message_length": len(message.message),
            "include_thinking": message.include_thinking
        }
    ) as span:
        logger.debug(
            "Received chat message for model %s", message.model or "default"
        )
        
        try:
            # Process message through ADK agent with specified model
            result = await adk_wrapper.process_message(
                message=message.message,
                session_id=message.session_id,
                include_thinking=message.include_thinking,
                model=message.model
            )
            
            # Collect metrics
            metrics = metrics_collector.collect_response_metrics(result)
            
            # Record latency
            latency_ms = (time.time() - start_time) * 1000
            record_metric("latency", latency_ms, {
                "endpoint": "/api/chat",
                "model": message.model or "default"
            })
            
            # Record tokens if available
            if "token_count" in metrics:
                record_metric("tokens_per_query", float(metrics["token_count"]), {
                    "endpoint": "/api/chat",
                    "model": message.model or "default"
                })
            
            span.set_attribute("response_length", len(result.get("response", "")))
            span.set_attribute("latency_ms", latency_ms)
            span.set_attribute("tool_calls_count", len(result.get("tool_calls", []) or []) or 0)
            
            return ChatResponse(
                response=result.get("response", ""),
                thinking_steps=result.get("thinking_steps"),
                tool_calls=result.get("tool_calls"),
                metrics=metrics,
                timestamp=datetime.now(timezone.utc).isoformat(),
                model=result.get("model", message.model),
            )
            
        except Exception as e:
            span.set_attribute("error", str(e))
            logger.error(f"Error processing chat message: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@chat_router.websocket("/chat/ws")
async def chat_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time agent interaction.
    
    Streams agent thinking, tool calls, and responses in real-time.
    
    Message format (client -> server):
    {
        "type": "message",
        "message": "user's message",
        "session_id": "optional-session-id"
    }
    
    Message format (server -> client):
    {
        "type": "thinking" | "tool_call" | "response" | "complete" | "error",
        "data": { ... },
        "timestamp": "ISO-8601 timestamp"
    }
    """
    import time
    
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    # Record throughput
    record_throughput({"endpoint": "/api/chat/ws"})
    
    # Get dependencies from app state
    adk_wrapper = websocket.app.state.adk_wrapper
    
    try:
        while True:
            start_time = time.time()
            # Receive message from client
            data = await websocket.receive_text()
            
            # Parse JSON with error handling
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}. Raw data: {data[:200]}")
                await websocket.send_json({
                    "type": "error",
                    "data": {"error": f"Invalid JSON: {str(e)}"},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                continue
            
            logger.debug(
                "WebSocket received message for session %s",
                message_data.get("session_id", "<unknown>"),
            )
            # Validate message
            if message_data.get("type") != "message":
                await websocket.send_json({
                    "type": "error",
                    "data": {"error": "Invalid message type"},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                continue
            
            # Extract model from message data
            selected_model = message_data.get("selectedModel")
            logger.info(f"Processing WebSocket message with model: {selected_model or 'default'}")
            
            with trace_span(
                "api.chat.websocket",
                attributes={
                    "endpoint": "/api/chat/ws",
                    "model": selected_model or "default",
                    "session_id": message_data.get("session_id", "none"),
                    "message_length": len(message_data.get("message", ""))
                }
            ) as span:
                # Process message with streaming
                event_count = 0
                async for event in adk_wrapper.process_message_stream(
                    message=message_data["message"],
                    session_id=message_data.get("session_id"),
                    model=selected_model
                ):
                    event_count += 1
                    await websocket.send_json({
                        "type": event["type"],
                        "data": event["data"],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                
                # Record latency
                latency_ms = (time.time() - start_time) * 1000
                record_metric("latency", latency_ms, {
                    "endpoint": "/api/chat/ws",
                    "model": selected_model or "default"
                })
                
                span.set_attribute("latency_ms", latency_ms)
                span.set_attribute("event_count", event_count)
            
            # Send completion signal
            await websocket.send_json({
                "type": "complete",
                "data": {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"error": str(e)},
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as send_error:
            logger.debug(f"Failed to send error message to WebSocket: {send_error}")


# ============================================================================
# METRICS ENDPOINTS
# ============================================================================

@metrics_router.get("/metrics")
async def get_metrics(
    metrics_collector: MetricsCollector = Depends(get_metrics_collector)
):
    """
    Get all collected metrics.
    
    Returns metrics from all phases, including:
    - Baseline metrics (Phase 0)
    - Agent metrics (Phase 1)
    - RAG metrics (Phase 2+)
    - Context engineering metrics
    """
    with trace_span("api.metrics.get", attributes={"endpoint": "/api/metrics"}):
        try:
            # Update memory usage before returning metrics
            update_memory_usage()
            
            metrics = metrics_collector.get_all_metrics()
            return {
                "metrics": metrics,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching metrics: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@metrics_router.get("/metrics/phase/{phase_id}")
async def get_phase_metrics(
    phase_id: str,
    metrics_collector: MetricsCollector = Depends(get_metrics_collector)
):
    """
    Get metrics for a specific phase.
    
    Args:
        phase_id: Phase identifier (e.g., "phase0", "phase1", "phase2")
    """
    try:
        metrics = metrics_collector.get_phase_metrics(phase_id)
        if metrics is None:
            raise HTTPException(status_code=404, detail=f"No metrics found for {phase_id}")
        
        return {
            "phase": phase_id,
            "metrics": metrics,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching phase metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@metrics_router.get("/metrics/comparison")
async def get_metrics_comparison(
    metrics_collector: MetricsCollector = Depends(get_metrics_collector)
):
    """
    Get a comparison of metrics across all phases.
    
    Returns a structured comparison showing improvements/degradations
    in key metrics across phases.
    """
    try:
        comparison = metrics_collector.get_metrics_comparison()
        return {
            "comparison": comparison,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating metrics comparison: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TOOLS ENDPOINTS
# ============================================================================

@tools_router.get("/tools", response_model=List[ToolInfo])
async def get_tools(
    adk_wrapper: ADKAgentWrapper = Depends(get_adk_wrapper)
):
    """
    Get list of available tools for the ADK agent.
    
    Returns information about each tool including name, description,
    and parameters.
    """
    with trace_span("api.tools.get", attributes={"endpoint": "/api/tools"}):
        try:
            tools = adk_wrapper.get_available_tools()
            return tools
        except Exception as e:
            logger.error(f"Error fetching tools: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@tools_router.get("/tools/{tool_name}")
async def get_tool_info(
    tool_name: str,
    adk_wrapper: ADKAgentWrapper = Depends(get_adk_wrapper)
):
    """
    Get detailed information about a specific tool.
    
    Args:
        tool_name: Name of the tool
    """
    try:
        tool_info = adk_wrapper.get_tool_info(tool_name)
        if not tool_info:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        return tool_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching tool info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MODELS ENDPOINTS
# ============================================================================

class OllamaModel(BaseModel):
    """Ollama model information."""
    name: str = Field(..., description="Model name")
    modified_at: str = Field(..., description="Last modified timestamp")
    size: int = Field(..., description="Model size in bytes")
    digest: Optional[str] = Field(None, description="Model digest/hash")


class RunningModel(BaseModel):
    """Information about a running Ollama model."""
    name: str = Field(..., description="Model name")
    size: int = Field(..., description="Model size in bytes")
    size_vram: int = Field(..., description="VRAM usage in bytes")


class ClearModelsResponse(BaseModel):
    """Response from clearing models operation."""
    success: bool = Field(..., description="Whether the operation succeeded")
    models_stopped: List[str] = Field(..., description="List of models that were stopped")
    message: str = Field(..., description="Status message")


@models_router.get("/models", response_model=List[OllamaModel])
async def get_ollama_models():
    """
    Get list of locally installed Ollama models.
    
    Connects to local Ollama instance and retrieves available models.
    """
    try:
        # Connect to local Ollama API
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:11434/api/tags", timeout=5.0)
            response.raise_for_status()
            
            data = response.json()
            models = data.get("models", [])
            
            # Transform Ollama API response to our model format
            return [
                OllamaModel(
                    name=model.get("name", "unknown"),
                    modified_at=model.get("modified_at", ""),
                    size=model.get("size", 0),
                    digest=model.get("digest")
                )
                for model in models
            ]
            
    except httpx.ConnectError:
        logger.error("Cannot connect to Ollama. Make sure Ollama is running on localhost:11434")
        raise HTTPException(
            status_code=503, 
            detail="Cannot connect to Ollama. Please ensure Ollama is running."
        )
    except httpx.TimeoutException:
        logger.error("Timeout connecting to Ollama")
        raise HTTPException(
            status_code=504,
            detail="Timeout connecting to Ollama service."
        )
    except Exception as e:
        logger.error(f"Error fetching Ollama models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@models_router.get("/models/running", response_model=List[RunningModel])
async def get_running_models():
    """
    Get list of currently running (loaded in memory) Ollama models.
    
    Equivalent to 'ollama ps' command.
    """
    try:
        # Try using Ollama API first
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:11434/api/ps", timeout=5.0)
            response.raise_for_status()
            
            data = response.json()
            models = data.get("models", [])
            
            return [
                RunningModel(
                    name=model.get("name", "unknown"),
                    size=model.get("size", 0),
                    size_vram=model.get("size_vram", 0)
                )
                for model in models
            ]
            
    except httpx.ConnectError:
        logger.error("Cannot connect to Ollama")
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Ollama. Please ensure Ollama is running."
        )
    except Exception as e:
        logger.error(f"Error fetching running models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@models_router.post("/models/clear", response_model=ClearModelsResponse)
async def clear_running_models():
    """
    Stop all currently running Ollama models to free up memory.
    
    This endpoint is system-agnostic and works on Windows, macOS, and Linux.
    """
    try:
        # First, get list of running models
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://localhost:11434/api/ps", timeout=5.0)
                response.raise_for_status()
                data = response.json()
                running_models = [model.get("name") for model in data.get("models", [])]
            except httpx.ConnectError:
                raise HTTPException(
                    status_code=503,
                    detail="Cannot connect to Ollama. Please ensure Ollama is running."
                )
        
        if not running_models:
            return ClearModelsResponse(
                success=True,
                models_stopped=[],
                message="No models are currently running"
            )
        
        logger.info(f"Attempting to stop {len(running_models)} running models: {running_models}")
        
        # Find ollama executable (system-agnostic)
        ollama_cmd = shutil.which("ollama")
        if not ollama_cmd:
            # Try common installation paths
            system = platform.system()
            if system == "Windows":
                possible_paths = [
                    "C:\\Program Files\\Ollama\\ollama.exe",
                    "C:\\Program Files (x86)\\Ollama\\ollama.exe",
                ]
            elif system == "Darwin":  # macOS
                possible_paths = [
                    "/usr/local/bin/ollama",
                    "/opt/homebrew/bin/ollama",
                ]
            else:  # Linux
                possible_paths = [
                    "/usr/local/bin/ollama",
                    "/usr/bin/ollama",
                ]
            
            for path in possible_paths:
                if shutil.which(path):
                    ollama_cmd = path
                    break
        
        if not ollama_cmd:
            raise HTTPException(
                status_code=500,
                detail="Could not find ollama executable. Please ensure Ollama is installed."
            )
        
        # Stop each running model
        stopped_models = []
        failed_models = []
        
        for model_name in running_models:
            try:
                logger.info(f"Stopping model: {model_name}")
                
                # Use subprocess to run 'ollama stop <model>'
                # This works cross-platform
                # Run subprocess off the event loop to avoid blocking
                process = await asyncio.to_thread(
                    lambda: subprocess.run(
                        [ollama_cmd, "stop", model_name],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        check=False
                    )
                )
                
                if process.returncode == 0:
                    stopped_models.append(model_name)
                    logger.info(f"Successfully stopped model: {model_name}")
                else:
                    logger.warning(f"Failed to stop model {model_name}: {process.stderr}")
                    failed_models.append(model_name)
                    
            except subprocess.TimeoutExpired:
                logger.error(f"Timeout while stopping model: {model_name}")
                failed_models.append(model_name)
            except Exception as e:
                logger.error(f"Error stopping model {model_name}: {e}")
                failed_models.append(model_name)
        
        # Prepare response message
        if failed_models:
            message = f"Stopped {len(stopped_models)} model(s). Failed to stop: {', '.join(failed_models)}"
        else:
            message = f"Successfully stopped {len(stopped_models)} model(s)"
        
        return ClearModelsResponse(
            success=len(failed_models) == 0,
            models_stopped=stopped_models,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

