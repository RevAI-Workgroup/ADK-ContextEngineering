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
from src.core.context_config import (
    ContextEngineeringConfig, 
    ConfigPreset,
    get_default_config,
    get_preset_configs,
    get_preset_names
)
from src.memory.run_history import RunRecord, get_run_history_manager

logger = logging.getLogger(__name__)

# Initialize routers
chat_router = APIRouter()
metrics_router = APIRouter()
tools_router = APIRouter()
models_router = APIRouter()
runs_router = APIRouter()
config_router = APIRouter()
documents_router = APIRouter()


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
    config: Optional[Dict[str, Any]] = Field(None, description="Context engineering configuration")


class ChatResponse(BaseModel):
    """Response from agent."""
    response: str = Field(..., description="Agent's response")
    thinking_steps: Optional[List[str]] = Field(None, description="Agent's thinking process")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tools called by agent")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Response metrics")
    timestamp: str = Field(..., description="Response timestamp")
    model: Optional[str] = Field(None, description="Model used for this response")
    pipeline_metadata: Optional[Dict[str, Any]] = Field(None, description="RAG and pipeline metadata")
    pipeline_metrics: Optional[Dict[str, Any]] = Field(None, description="Pipeline execution metrics")


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
    logger.debug(
        "Received chat message for model %s", message.model or "default"
    )
    
    try:
        # Parse config if provided
        context_config = None
        if message.config:
            try:
                context_config = ContextEngineeringConfig.from_dict(message.config)
            except (ValueError, TypeError, KeyError) as config_error:
                error_msg = f"Invalid configuration: {str(config_error)}"
                logger.error(
                    "Configuration parsing failed: %s. Config data: %s",
                    config_error,
                    message.config,
                    exc_info=True
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_configuration",
                        "message": error_msg,
                        "details": str(config_error)
                    }
                )
            
            # Validate configuration
            validation_errors = context_config.validate()
            if validation_errors:
                error_msg = f"Configuration validation failed: {validation_errors}"
                logger.error(
                    "Configuration validation failed: %s. Config data: %s",
                    validation_errors,
                    message.config,
                    exc_info=True
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_configuration",
                        "message": error_msg,
                        "details": str(validation_errors)
                    }
                )
        
        # Process message through ADK agent with specified model and config
        result = await adk_wrapper.process_message(
            message=message.message,
            session_id=message.session_id,
            include_thinking=message.include_thinking,
            model=message.model,
            config=context_config
        )
        
        # Collect metrics
        metrics = metrics_collector.collect_response_metrics(result)

        # Extract pipeline metrics from result if available
        metrics_data = result.get("metrics")
        pipeline_metrics = metrics_data.get("pipeline_metrics") if isinstance(metrics_data, dict) else None

        return ChatResponse(
            response=result.get("response", ""),
            thinking_steps=result.get("thinking_steps"),
            tool_calls=result.get("tool_calls"),
            metrics=metrics,
            timestamp=datetime.now(timezone.utc).isoformat(),
            model=result.get("model", message.model),
            pipeline_metadata=result.get("pipeline_metadata"),
            pipeline_metrics=pipeline_metrics,
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


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
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    # Get dependencies from app state
    adk_wrapper = websocket.app.state.adk_wrapper
    
    try:
        while True:
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
            
            # Parse config if provided
            context_config = None
            if message_data.get("config"):
                try:
                    context_config = ContextEngineeringConfig.from_dict(message_data["config"])
                except (ValueError, TypeError, KeyError) as config_error:
                    error_msg = f"Invalid configuration: {str(config_error)}"
                    logger.error(
                        "WebSocket configuration parsing failed: %s. Config data: %s",
                        config_error,
                        message_data.get("config"),
                        exc_info=True
                    )
                    await websocket.send_json({
                        "type": "error",
                        "data": {
                            "error": "invalid_configuration",
                            "message": error_msg,
                            "details": str(config_error)
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    continue
                
                # Validate configuration
                validation_errors = context_config.validate()
                if validation_errors:
                    error_msg = f"Configuration validation failed: {validation_errors}"
                    logger.error(
                        "WebSocket configuration validation failed: %s. Config data: %s",
                        validation_errors,
                        message_data.get("config"),
                        exc_info=True
                    )
                    await websocket.send_json({
                        "type": "error",
                        "data": {
                            "error": "invalid_configuration",
                            "message": error_msg,
                            "details": str(validation_errors)
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    continue
            
            # Process message with streaming
            async for event in adk_wrapper.process_message_stream(
                message=message_data["message"],
                session_id=message_data.get("session_id"),
                model=selected_model,
                config=context_config
            ):
                await websocket.send_json({
                    "type": event["type"],
                    "data": event["data"],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            
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
    try:
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

@tools_router.post("/tools", response_model=List[ToolInfo])
async def get_tools(
    config: Optional[Dict[str, Any]] = None,
    adk_wrapper: ADKAgentWrapper = Depends(get_adk_wrapper)
):
    """
    Get list of available tools for the ADK agent based on configuration.

    Returns information about each tool including name, description,
    and parameters. Tools list may vary based on enabled configuration.

    Args:
        config: Optional configuration dict to determine which tools are available
    """
    try:
        # Parse config if provided
        context_config = None
        if config:
            try:
                context_config = ContextEngineeringConfig.from_dict(config)
            except (ValueError, TypeError, KeyError) as config_error:
                logger.warning(f"Invalid config in get_tools, using default: {config_error}")

        tools = adk_wrapper.get_available_tools(context_config)
        return tools
    except Exception as e:
        logger.error(f"Error fetching tools: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@tools_router.get("/tools", response_model=List[ToolInfo])
async def get_tools_legacy(
    adk_wrapper: ADKAgentWrapper = Depends(get_adk_wrapper)
):
    """
    Get list of available tools (legacy GET endpoint).

    Returns base tools without configuration-dependent tools.
    Use POST /api/tools with config for full tool list.
    """
    try:
        tools = adk_wrapper.get_available_tools(None)
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


# ============================================================================
# RUN HISTORY ENDPOINTS
# ============================================================================

@runs_router.get("/runs")
async def get_runs(
    limit: Optional[int] = None,
    query: Optional[str] = None,
    technique: Optional[str] = None,
    model: Optional[str] = None
):
    """
    Get recent runs from history.
    
    Query parameters:
    - limit: Maximum number of runs to return (default: all)
    - query: Filter by query text (case-insensitive substring match)
    - technique: Filter by enabled technique (e.g., 'rag', 'compression')
    - model: Filter by model identifier
    """
    try:
        history_manager = get_run_history_manager()
        
        # Get runs based on filters
        if query:
            runs = history_manager.get_runs_by_query(query, case_sensitive=False)
        elif technique:
            runs = history_manager.get_runs_by_technique(technique)
        elif model:
            runs = history_manager.get_runs_by_model(model)
        else:
            runs = history_manager.get_recent_runs(limit=limit)
        
        # Always apply limit after fetching runs (regardless of filters used)
        if limit is not None and limit > 0:
            runs = runs[:limit]
        
        return {
            "runs": [run.to_dict() for run in runs],
            "count": len(runs),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@runs_router.get("/runs/{run_id}")
async def get_run_by_id(run_id: str):
    """
    Get a specific run by ID.
    
    Args:
        run_id: UUID of the run to retrieve
    """
    try:
        history_manager = get_run_history_manager()
        run = history_manager.get_run_by_id(run_id)
        
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run with ID '{run_id}' not found")
        
        return {
            "run": run.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching run by ID: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@runs_router.post("/runs/clear")
async def clear_runs():
    """
    Clear all run history.
    
    This is a destructive operation that removes all stored runs.
    """
    try:
        history_manager = get_run_history_manager()
        history_manager.clear_history()
        
        logger.info("Run history cleared")
        
        return {
            "success": True,
            "message": "Run history cleared successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@runs_router.get("/runs/compare")
async def compare_runs(run_ids: str):
    """
    Compare multiple runs.
    
    Query parameters:
    - run_ids: Comma-separated list of run IDs to compare
    
    Example: /api/runs/compare?run_ids=abc123,def456,ghi789
    """
    try:
        history_manager = get_run_history_manager()
        
        # Parse run IDs
        id_list = [rid.strip() for rid in run_ids.split(",") if rid.strip()]
        
        if len(id_list) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 run IDs are required for comparison"
            )
        
        # Fetch all runs
        runs = []
        missing_ids = []
        for run_id in id_list:
            run = history_manager.get_run_by_id(run_id)
            if run:
                runs.append(run)
            else:
                missing_ids.append(run_id)
        
        if missing_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Runs not found: {', '.join(missing_ids)}"
            )
        
        # Build comparison data
        comparison = {
            "runs": [run.to_dict() for run in runs],
            "query": runs[0].query if runs else None,  # Assumes same query
            "metrics_comparison": _compare_run_metrics(runs),
            "config_comparison": _compare_run_configs(runs),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return comparison
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


def _compare_run_metrics(runs: List[RunRecord]) -> Dict[str, Any]:
    """
    Compare metrics across multiple runs.
    
    Returns a structured comparison showing metrics for each run.
    """
    metrics_comparison = {}
    
    for run in runs:
        run_metrics = {}
        for key, value in run.metrics.items():
            if isinstance(value, (int, float)):
                run_metrics[key] = value
        
        metrics_comparison[run.id] = {
            "run_id": run.id,
            "duration_ms": run.duration_ms,
            "enabled_techniques": run.enabled_techniques,
            "metrics": run_metrics
        }
    
    return metrics_comparison


def _compare_run_configs(runs: List[RunRecord]) -> Dict[str, Any]:
    """
    Compare configurations across multiple runs.
    
    Highlights differences in enabled techniques and their settings.
    """
    config_comparison = {}
    
    for run in runs:
        config_comparison[run.id] = {
            "run_id": run.id,
            "enabled_techniques": run.enabled_techniques,
            "model": run.model,
            "config": run.config
        }
    
    return config_comparison


@runs_router.get("/runs/stats")
async def get_run_stats():
    """
    Get statistics about the run history.
    
    Returns summary information including:
    - Total number of runs
    - Models used
    - Techniques used
    - Date range
    - Average duration
    """
    try:
        history_manager = get_run_history_manager()
        stats = history_manager.get_history_stats()
        
        return {
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching run stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# CONFIG ENDPOINTS
# ============================================================================

@config_router.get("/config/default")
async def get_default_configuration():
    """
    Get the default context engineering configuration.
    
    This is the baseline configuration with all techniques disabled.
    """
    try:
        config = get_default_config()
        return {
            "config": config.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting default config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@config_router.get("/config/presets")
async def get_configuration_presets():
    """
    Get all available configuration presets.
    
    Returns:
    - baseline: All techniques disabled
    - basic_rag: Only RAG enabled
    - advanced_rag: RAG + reranking + hybrid search
    - full_stack: All techniques enabled
    """
    try:
        preset_names = get_preset_names()
        presets = get_preset_configs()
        
        return {
            "presets": {
                name: config.to_dict()
                for name, config in presets.items()
            },
            "preset_names": preset_names,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting config presets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@config_router.get("/config/presets/{preset_name}")
async def get_preset_configuration(preset_name: str):
    """
    Get a specific configuration preset by name.
    
    Args:
        preset_name: Name of the preset (baseline, basic_rag, advanced_rag, full_stack)
    """
    try:
        # Validate preset name
        valid_presets = get_preset_names()
        if preset_name not in valid_presets:
            raise HTTPException(
                status_code=404,
                detail=f"Preset '{preset_name}' not found. Valid presets: {', '.join(valid_presets)}"
            )
        
        preset_enum = ConfigPreset(preset_name)
        config = ContextEngineeringConfig.from_preset(preset_enum)
        
        return {
            "preset": preset_name,
            "config": config.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting preset config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


class ConfigValidationRequest(BaseModel):
    """Request to validate a configuration."""
    config: Dict[str, Any] = Field(..., description="Configuration to validate")


@config_router.post("/config/validate")
async def validate_configuration(request: ConfigValidationRequest):
    """
    Validate a context engineering configuration.
    
    Returns validation errors if any, or success message if valid.
    """
    try:
        # Parse configuration
        try:
            config = ContextEngineeringConfig.from_dict(request.config)
        except (ValueError, TypeError, KeyError) as config_error:
            error_msg = f"Configuration parsing failed: {str(config_error)}"
            logger.error(
                "Config validation - parsing failed: %s. Config data: %s",
                config_error,
                request.config,
                exc_info=True
            )
            return {
                "valid": False,
                "errors": [{
                    "field": "config",
                    "message": error_msg,
                    "details": str(config_error)
                }],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Validate
        errors = config.validate()
        
        if errors:
            return {
                "valid": False,
                "errors": errors,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "valid": True,
                "message": "Configuration is valid",
                "enabled_techniques": config.get_enabled_techniques(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        logger.error(f"Error validating config: {e}", exc_info=True)
        return {
            "valid": False,
            "errors": [f"Configuration parsing error: {str(e)}"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# ============================================================================
# DOCUMENT MANAGEMENT ENDPOINTS
# ============================================================================

from fastapi import UploadFile, File
from pathlib import Path
import re


def secure_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and remove unsafe characters.
    
    This function:
    - Extracts only the final basename (strips directory components)
    - Removes leading slashes and dots
    - Removes or replaces unsafe characters
    - Ensures the filename is safe for filesystem operations
    
    Args:
        filename: Original filename from user input
        
    Returns:
        Sanitized filename safe for filesystem use
        
    Raises:
        ValueError: If filename is empty or contains only unsafe characters
    """
    if not filename:
        raise ValueError("Filename cannot be empty")
    
    # Extract only the basename, removing any directory components
    # This prevents path traversal attacks like "../../../etc/passwd"
    basename = Path(filename).name
    
    # Remove leading dots and slashes
    basename = basename.lstrip('.\\/')
    
    if not basename:
        raise ValueError("Filename contains only unsafe characters")
    
    # Remove or replace unsafe characters
    # Keep alphanumeric, dots, hyphens, underscores, and spaces
    # Replace other characters with underscores
    safe_chars = re.sub(r'[^a-zA-Z0-9._\-\s]', '_', basename)
    
    # Remove multiple consecutive underscores
    safe_chars = re.sub(r'_+', '_', safe_chars)
    
    # Remove leading/trailing underscores and dots
    safe_chars = safe_chars.strip('_.')
    
    if not safe_chars:
        raise ValueError("Filename contains only unsafe characters")
    
    # Limit filename length to prevent filesystem issues
    max_length = 255
    if len(safe_chars) > max_length:
        # Preserve extension if present
        name_part = Path(safe_chars).stem[:max_length - 10]  # Reserve space for extension
        ext_part = Path(safe_chars).suffix
        safe_chars = name_part + ext_part
    
    return safe_chars


class DocumentIngestRequest(BaseModel):
    """Request model for bulk document ingestion."""
    directory: str = Field(..., description="Directory path to ingest documents from")
    recursive: bool = Field(True, description="Whether to search recursively")
    file_extensions: Optional[List[str]] = Field(None, description="File extensions to include")


class RAGToolExecuteRequest(BaseModel):
    """Request model for RAG tool execution."""
    query: str = Field(..., description="Search query")
    top_k: int = Field(5, description="Number of documents to retrieve")
    config: Optional[Dict[str, Any]] = Field(None, description="Optional context engineering configuration")


@documents_router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    description: Optional[str] = None
):
    """
    Upload a document to the vector store.

    Supports .txt and .md files.

    Args:
        file: File to upload
        description: Optional description for the document
    """
    try:
        from src.retrieval.vector_store import get_vector_store
        from src.retrieval.document_loader import load_document
        from src.retrieval.chunking import chunk_document

        # Validate and sanitize filename to prevent path traversal
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required"
            )
        
        try:
            sanitized_filename = secure_filename(file.filename)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid filename: {str(e)}"
            )
        
        # Validate file type using sanitized filename
        file_extension = Path(sanitized_filename).suffix.lower()
        if file_extension not in [".txt", ".md"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}. Supported: .txt, .md"
            )
        
        # Validate file size (e.g., 10MB limit)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )
        
        # Ensure knowledge base directory exists
        kb_dir = Path("data/knowledge_base")
        kb_dir.mkdir(parents=True, exist_ok=True)
        
        # Construct safe file path using sanitized filename
        file_path = kb_dir / sanitized_filename
        
        # Ensure the resolved path is still within kb_dir (defense in depth)
        try:
            file_path = file_path.resolve()
            kb_dir_resolved = kb_dir.resolve()
            if not file_path.is_relative_to(kb_dir_resolved):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file path detected"
                )
        except (ValueError, OSError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file path: {str(e)}"
            )
        
        # Save uploaded file
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"Saved uploaded file: {sanitized_filename} (original: {file.filename})")

        # Load document
        document = load_document(str(file_path))

        # Add description to metadata if provided
        if description:
            document.metadata["description"] = description

        # Chunk document
        chunks = chunk_document(
            text=document.content,
            metadata=document.metadata,
            strategy="fixed",
            chunk_size=512,
            chunk_overlap=50
        )

        # Add to vector store
        vector_store = get_vector_store()
        chunk_texts = [chunk.text for chunk in chunks]
        chunk_metadatas = [chunk.metadata for chunk in chunks]
        chunk_ids = vector_store.add_documents(
            texts=chunk_texts,
            metadatas=chunk_metadatas
        )

        logger.info(f"Added {len(chunks)} chunks to vector store")

        return {
            "success": True,
            "filename": sanitized_filename,
            "original_filename": file.filename,
            "file_size_bytes": len(content),
            "chunks_created": len(chunks),
            "doc_id": document.doc_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@documents_router.post("/documents/ingest")
async def ingest_documents(request: DocumentIngestRequest):
    """
    Bulk ingest documents from a directory.

    Processes all documents in the specified directory and adds them to the vector store.
    """
    try:
        from src.retrieval.vector_store import get_vector_store
        from src.retrieval.document_loader import load_documents_from_directory
        from src.retrieval.chunking import chunk_document

        # Load documents
        documents = load_documents_from_directory(
            directory=request.directory,
            recursive=request.recursive,
            file_extensions=request.file_extensions
        )

        if not documents:
            return {
                "success": True,
                "message": "No documents found to ingest",
                "documents_processed": 0,
                "total_chunks": 0
            }

        # Chunk all documents
        all_chunks = []
        for doc in documents:
            chunks = chunk_document(
                text=doc.content,
                metadata=doc.metadata,
                strategy="fixed",
                chunk_size=512,
                chunk_overlap=50
            )
            all_chunks.extend(chunks)

        # Add to vector store
        vector_store = get_vector_store()
        chunk_texts = [chunk.text for chunk in all_chunks]
        chunk_metadatas = [chunk.metadata for chunk in all_chunks]
        chunk_ids = vector_store.add_documents(
            texts=chunk_texts,
            metadatas=chunk_metadatas
        )

        logger.info(
            f"Ingested {len(documents)} documents, "
            f"created {len(all_chunks)} chunks"
        )

        return {
            "success": True,
            "documents_processed": len(documents),
            "total_chunks": len(all_chunks),
            "directory": request.directory,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error ingesting documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@documents_router.get("/documents")
async def list_documents():
    """
    List all documents in the knowledge base directory.
    """
    try:
        kb_dir = Path("data/knowledge_base")

        if not kb_dir.exists():
            return {
                "documents": [],
                "count": 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Get all files
        documents = []
        for file_path in kb_dir.iterdir():
            if file_path.is_file():
                documents.append({
                    "filename": file_path.name,
                    "path": str(file_path.relative_to(kb_dir)),
                    "size_bytes": file_path.stat().st_size,
                    "modified_at": datetime.fromtimestamp(
                        file_path.stat().st_mtime,
                        tz=timezone.utc
                    ).isoformat()
                })

        return {
            "documents": documents,
            "count": len(documents),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@documents_router.delete("/documents/{filename}")
async def delete_document(filename: str):
    """
    Delete a document from the knowledge base.

    Note: This only deletes the file, not the chunks from the vector store.
    Use /vector-store/clear to clear the vector store.
    """
    try:
        # Sanitize filename to prevent path traversal
        try:
            sanitized_filename = secure_filename(filename)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid filename: {str(e)}"
            )
        
        kb_dir = Path("data/knowledge_base")
        file_path = kb_dir / sanitized_filename
        
        # Ensure the resolved path is still within kb_dir (defense in depth)
        try:
            file_path = file_path.resolve()
            kb_dir_resolved = kb_dir.resolve()
            if not file_path.is_relative_to(kb_dir_resolved):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file path detected"
                )
        except (ValueError, OSError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file path: {str(e)}"
            )

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Document '{sanitized_filename}' not found")

        # Delete file
        file_path.unlink()
        logger.info(f"Deleted document: {sanitized_filename} (original: {filename})")

        return {
            "success": True,
            "filename": sanitized_filename,
            "original_filename": filename,
            "message": "Document deleted successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@documents_router.get("/vector-store/stats")
async def get_vector_store_stats():
    """
    Get statistics about the vector store.
    """
    try:
        from src.retrieval.vector_store import get_vector_store

        vector_store = get_vector_store()
        stats = vector_store.get_stats()

        return {
            **stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting vector store stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@documents_router.post("/vector-store/clear")
async def clear_vector_store():
    """
    Clear all documents from the vector store.

    This is a destructive operation that removes all embeddings.
    """
    try:
        from src.retrieval.vector_store import get_vector_store

        vector_store = get_vector_store()
        vector_store.clear()

        logger.info("Vector store cleared")

        return {
            "success": True,
            "message": "Vector store cleared successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error clearing vector store: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@documents_router.get("/vector-store/search")
async def search_vector_store(
    query: str,
    top_k: int = 5,
    similarity_threshold: float = 0.7
):
    """
    Search the vector store for similar documents.

    Args:
        query: Search query
        top_k: Number of results to return
        similarity_threshold: Minimum similarity score
    """
    try:
        from src.retrieval.vector_store import get_vector_store

        vector_store = get_vector_store()
        results = vector_store.search(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )

        return {
            "results": [result.to_dict() for result in results],
            "count": len(results),
            "query": query,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error searching vector store: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@documents_router.post("/rag-tool/execute")
async def execute_rag_tool(request: RAGToolExecuteRequest):
    """
    Execute the RAG tool to search the knowledge base.

    This endpoint is called by the LLM when it decides to use the RAG tool.

    Args:
        request: RAG tool execution request containing query, top_k, and optional config
    """
    try:
        from src.core.modular_pipeline import ContextPipeline, RAGToolModule

        # Parse config if provided
        context_config = None
        if request.config:
            try:
                context_config = ContextEngineeringConfig.from_dict(request.config)
            except (ValueError, TypeError, KeyError) as config_error:
                error_msg = f"Invalid configuration: {str(config_error)}"
                logger.error(
                    "RAG tool configuration parsing failed: %s. Config data: %s",
                    config_error,
                    request.config,
                    exc_info=True
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_configuration",
                        "message": error_msg,
                        "details": str(config_error)
                    }
                )
            
            # Validate configuration
            validation_errors = context_config.validate()
            if validation_errors:
                error_msg = f"Configuration validation failed: {validation_errors}"
                logger.error(
                    "RAG tool configuration validation failed: %s. Config data: %s",
                    validation_errors,
                    request.config,
                    exc_info=True
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_configuration",
                        "message": error_msg,
                        "details": str(validation_errors)
                    }
                )
        
        # Get or create configuration
        if context_config is None:
            context_config = ContextEngineeringConfig()
            # Enable RAG tool by default for this endpoint
            context_config.rag_tool.enabled = True

        # Create pipeline
        pipeline = ContextPipeline(context_config)

        # Get the RAG tool module
        rag_tool_module = pipeline.get_module("rag_tool")

        if not isinstance(rag_tool_module, RAGToolModule):
            raise HTTPException(
                status_code=400,
                detail="RAG tool module is not properly configured"
            )

        # Execute the tool
        result = rag_tool_module.execute_tool(query=request.query, top_k=request.top_k)

        return {
            **result,
            "query": request.query,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing RAG tool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e

