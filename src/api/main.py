"""
FastAPI backend for Context Engineering Sandbox.

This API wraps the ADK agent and provides endpoints for:
- Chat interactions with WebSocket support
- Metrics retrieval
- Tool information
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# OpenTelemetry FastAPI instrumentation
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FASTAPI_INSTRUMENTATION_AVAILABLE = True
except ImportError:
    FASTAPI_INSTRUMENTATION_AVAILABLE = False
    logger.warning("OpenTelemetry FastAPI instrumentation not available")

from src.api.endpoints import chat_router, metrics_router, tools_router, models_router
from src.api.adk_wrapper import ADKAgentWrapper
from src.evaluation.metrics import MetricsCollector
from src.core.tracing import initialize_tracing, update_memory_usage, record_throughput


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    
    Handles initialization and cleanup of singleton instances:
    - ADK Agent Wrapper
    - Metrics Collector
    - OpenTelemetry tracing
    """
    # Startup: Initialize shared instances
    logger.info("Initializing application dependencies...")
    
    # Initialize OpenTelemetry tracing (must be done before recording metrics)
    try:
        initialize_tracing()
        logger.info("OpenTelemetry tracing initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry tracing: {e}", exc_info=True)
        # Don't fail startup, but log the error clearly
    
    app.state.adk_wrapper = ADKAgentWrapper()
    app.state.metrics_collector = MetricsCollector()
    
    # Update memory usage metric on startup
    try:
        update_memory_usage()
    except Exception as e:
        logger.debug(f"Could not update memory metric: {e}")
    
    logger.info("Application dependencies initialized successfully")
    
    yield
    
    # Shutdown: Clean up resources
    logger.info("Cleaning up application resources...")
    # Add any cleanup logic here if needed
    logger.info("Application shutdown complete")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Context Engineering Sandbox API",
    description="Backend API for demonstrating context engineering techniques with ADK agents",
    version="1.5.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default + fallback
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "status": "healthy",
        "service": "Context Engineering Sandbox API",
        "version": "1.5.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


# Include routers
app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(metrics_router, prefix="/api", tags=["metrics"])
app.include_router(tools_router, prefix="/api", tags=["tools"])
app.include_router(models_router, prefix="/api", tags=["models"])

# Instrument FastAPI with OpenTelemetry
if FASTAPI_INSTRUMENTATION_AVAILABLE:
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented with OpenTelemetry")
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

