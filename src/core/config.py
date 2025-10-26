"""
Configuration management for the Context Engineering project.

This module provides centralized configuration loading and management
from YAML files and environment variables.
"""

from typing import Any, Dict, Optional
from pathlib import Path
import yaml
import os
from dotenv import load_dotenv


class Config:
    """
    Central configuration manager for the application.
    
    Loads configuration from YAML files and environment variables,
    with environment variables taking precedence.
    """
    
    def __init__(self, config_dir: str = "configs"):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory containing YAML configuration files
        """
        self.config_dir = Path(config_dir)
        self._configs: Dict[str, Any] = {}
        
        # Load environment variables
        load_dotenv()
        
        # Load all configuration files
        self._load_all_configs()
    
    def _load_all_configs(self) -> None:
        """Load all YAML configuration files from the config directory."""
        if not self.config_dir.exists():
            raise FileNotFoundError(f"Configuration directory not found: {self.config_dir}")
        
        for config_file in self.config_dir.glob("*.yaml"):
            config_name = config_file.stem
            with open(config_file, 'r', encoding='utf-8') as f:
                self._configs[config_name] = yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.
        
        Environment variables override YAML values with automatic type conversion.
        
        Args:
            key: Configuration key in dot notation (e.g., "models.ollama.base_url")
            default: Default value if key not found
            
        Returns:
            Configuration value or default (with proper type conversion from env vars)
            
        Examples:
            >>> config = Config()
            >>> config.get("models.ollama.base_url")
            'http://localhost:11434'
            
            >>> # Environment variable: MODELS_OLLAMA_TIMEOUT=60
            >>> config.get("models.ollama.timeout")  # Returns int 60, not string "60"
            60
        """
        # Get YAML value first to determine expected type
        keys = key.split(".")
        yaml_value = self._configs
        
        for k in keys:
            if isinstance(yaml_value, dict) and k in yaml_value:
                yaml_value = yaml_value[k]
            else:
                yaml_value = None
                break
        
        # Check environment variable (uppercase with underscores)
        env_key = key.upper().replace(".", "_")
        env_value = os.getenv(env_key)
        
        if env_value is not None:
            # Convert env_value to match YAML value type if possible
            if yaml_value is not None:
                return self._convert_env_value(env_value, yaml_value)
            # No YAML value, return env string as-is
            return env_value
        
        # Return YAML value or default
        return yaml_value if yaml_value is not None else default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.
        
        Args:
            section: Name of the configuration file/section
            
        Returns:
            Dictionary containing the entire section
        """
        return self._configs.get(section, {})
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value (runtime only, not persisted).
        
        Args:
            key: Configuration key in dot notation
            value: Value to set
        """
        keys = key.split(".")
        config = self._configs
        
        # Navigate to parent
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set value
        config[keys[-1]] = value
    
    def _convert_env_value(self, env_value: str, yaml_value: Any) -> Any:
        """
        Convert environment variable string to match YAML value type.
        
        Args:
            env_value: String value from environment variable
            yaml_value: Original YAML value (used to determine target type)
            
        Returns:
            Converted value matching the type of yaml_value
            
        Examples:
            >>> self._convert_env_value("120", 60)  # int
            120
            >>> self._convert_env_value("true", False)  # bool
            True
            >>> self._convert_env_value("3.14", 2.5)  # float
            3.14
        """
        target_type = type(yaml_value)
        
        try:
            # Handle boolean conversion specially
            if target_type is bool:
                return env_value.lower() in ('true', '1', 'yes', 'on')
            
            # Handle None type (return as string)
            if yaml_value is None:
                return env_value
            
            # For other types, try direct conversion
            return target_type(env_value)
            
        except (ValueError, TypeError) as e:
            # If conversion fails, log warning and return string
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Failed to convert env var {env_value} to type {target_type.__name__}: {e}. "
                f"Returning as string."
            )
            return env_value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Export all configurations as dictionary.
        
        Returns:
            Dictionary containing all configurations
        """
        return self._configs.copy()
    
    @classmethod
    def load(cls, config_dir: str = "configs") -> "Config":
        """
        Factory method to load configuration.
        
        Args:
            config_dir: Directory containing configuration files
            
        Returns:
            Configured Config instance
        """
        return cls(config_dir=config_dir)


# Global configuration instance
_global_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get global configuration instance (singleton pattern).
    
    Returns:
        Global Config instance
    """
    global _global_config
    if _global_config is None:
        _global_config = Config.load()
    return _global_config


def reload_config() -> Config:
    """
    Reload configuration from files.
    
    Returns:
        Reloaded Config instance
    """
    global _global_config
    _global_config = Config.load()
    return _global_config

