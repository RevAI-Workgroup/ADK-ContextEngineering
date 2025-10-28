"""
Core module for Context Engineering project.

This module provides configuration management and re-exports the main agent.
The agent definition is in context_engineering_agent/agent.py (single source of truth).
"""

from .config import Config, get_config, reload_config

__all__ = [
    'Config',
    'get_config',
    'reload_config',
]
