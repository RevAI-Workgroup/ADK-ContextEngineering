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

from src.api.endpoints import chat_router, metrics_router, tools_router, models_router, runs_router, config_router, documents_router
from src.api.adk_wrapper import ADKAgentWrapper
from src.evaluation.metrics import MetricsCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API version
VERSION = "2.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    
    Handles initialization and cleanup of singleton instances:
    - ADK Agent Wrapper
    - Metrics Collector
    """
    # Startup: Initialize shared instances
    logger.info("Initializing application dependencies...")
    
    app.state.adk_wrapper = ADKAgentWrapper()
    app.state.metrics_collector = MetricsCollector()
    
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
    version=VERSION,
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
        "version": VERSION,
        "phase": "Phase 2 - Modular Pipeline Infrastructure",
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
app.include_router(runs_router, prefix="/api", tags=["runs"])
app.include_router(config_router, prefix="/api", tags=["config"])
app.include_router(documents_router, prefix="/api", tags=["documents"])


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

