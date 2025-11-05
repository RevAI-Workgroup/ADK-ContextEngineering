"""
Core module for Context Engineering project.

This module provides configuration management and re-exports the main agent.
The agent definition is in context_engineering_agent/agent.py (single source of truth).
"""

from .config import Config, get_config, reload_config
from .context_config import (
    ContextEngineeringConfig,
    RAGConfig,
    CompressionConfig,
    RerankingConfig,
    CachingConfig,
    HybridSearchConfig,
    MemoryConfig,
    ConfigPreset,
    get_default_config,
    get_preset_configs,
    get_preset_names,
)

__all__ = [
    'Config',
    'get_config',
    'reload_config',
    'ContextEngineeringConfig',
    'RAGConfig',
    'CompressionConfig',
    'RerankingConfig',
    'CachingConfig',
    'HybridSearchConfig',
    'MemoryConfig',
    'ConfigPreset',
    'get_default_config',
    'get_preset_configs',
    'get_preset_names',
]
