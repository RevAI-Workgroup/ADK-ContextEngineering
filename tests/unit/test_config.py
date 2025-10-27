"""
Unit tests for configuration management.
"""

import os
import pytest
from pathlib import Path
import tempfile
import yaml

from src.core.config import Config


class TestConfig:
    """Test suite for Config class."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory with test YAML files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            # Create test configuration file
            test_config = {
                'ollama': {
                    'base_url': 'http://localhost:11434',
                    'timeout': 120,
                    'temperature': 0.7,
                    'enabled': True,
                    'max_tokens': 4096
                },
                'strings': {
                    'name': 'test',
                    'version': '1.0.0'
                }
            }
            
            with open(config_dir / 'test.yaml', 'w') as f:
                yaml.dump(test_config, f)
            
            yield config_dir
    
    def test_load_yaml_configs(self, temp_config_dir):
        """Test loading YAML configuration files."""
        config = Config(str(temp_config_dir))
        
        assert config.get('test.ollama.base_url') == 'http://localhost:11434'
        assert config.get('test.ollama.timeout') == 120
        assert config.get('test.ollama.temperature') == 0.7
        assert config.get('test.ollama.enabled') is True
    
    def test_env_var_override_string(self, temp_config_dir):
        """Test environment variable override for string values."""
        os.environ['TEST_STRINGS_NAME'] = 'production'
        
        config = Config(str(temp_config_dir))
        assert config.get('test.strings.name') == 'production'
        
        del os.environ['TEST_STRINGS_NAME']
    
    def test_env_var_override_int(self, temp_config_dir):
        """Test environment variable override with type conversion for int."""
        os.environ['TEST_OLLAMA_TIMEOUT'] = '240'
        
        config = Config(str(temp_config_dir))
        value = config.get('test.ollama.timeout')
        
        # Should be converted to int, not string
        assert isinstance(value, int)
        assert value == 240
        
        del os.environ['TEST_OLLAMA_TIMEOUT']
    
    def test_env_var_override_float(self, temp_config_dir):
        """Test environment variable override with type conversion for float."""
        os.environ['TEST_OLLAMA_TEMPERATURE'] = '0.9'
        
        config = Config(str(temp_config_dir))
        value = config.get('test.ollama.temperature')
        
        # Should be converted to float, not string
        assert isinstance(value, float)
        assert value == 0.9
        
        del os.environ['TEST_OLLAMA_TEMPERATURE']
    
    def test_env_var_override_bool_true(self, temp_config_dir):
        """Test environment variable override with boolean conversion (true)."""
        test_cases = ['true', 'True', 'TRUE', '1', 'yes', 'YES', 'on', 'ON']
        
        for env_val in test_cases:
            os.environ['TEST_OLLAMA_ENABLED'] = env_val
            config = Config(str(temp_config_dir))
            value = config.get('test.ollama.enabled')
            
            assert isinstance(value, bool), f"Failed for {env_val}"
            assert value is True, f"Failed for {env_val}"
            
            del os.environ['TEST_OLLAMA_ENABLED']
    
    def test_env_var_override_bool_false(self, temp_config_dir):
        """Test environment variable override with boolean conversion (false)."""
        test_cases = ['false', 'False', 'FALSE', '0', 'no', 'NO', 'off', 'OFF']
        
        for env_val in test_cases:
            os.environ['TEST_OLLAMA_ENABLED'] = env_val
            config = Config(str(temp_config_dir))
            value = config.get('test.ollama.enabled')
            
            assert isinstance(value, bool), f"Failed for {env_val}"
            assert value is False, f"Failed for {env_val}"
            
            del os.environ['TEST_OLLAMA_ENABLED']
    
    def test_env_var_for_nonexistent_key(self, temp_config_dir):
        """Test environment variable for key not in YAML."""
        os.environ['TEST_OLLAMA_NEW_KEY'] = 'new_value'
        
        config = Config(str(temp_config_dir))
        value = config.get('test.ollama.new_key')
        
        # Should return string since no YAML value to infer type from
        assert value == 'new_value'
        
        del os.environ['TEST_OLLAMA_NEW_KEY']
    
    def test_default_value(self, temp_config_dir):
        """Test default value when key not found."""
        config = Config(str(temp_config_dir))
        
        assert config.get('test.nonexistent.key', 'default') == 'default'
    
    def test_get_section(self, temp_config_dir):
        """Test getting entire configuration section."""
        config = Config(str(temp_config_dir))
        
        ollama_section = config.get_section('test')
        assert 'ollama' in ollama_section
        assert ollama_section['ollama']['base_url'] == 'http://localhost:11434'
    
    def test_set_value(self, temp_config_dir):
        """Test setting configuration value at runtime."""
        config = Config(str(temp_config_dir))
        
        config.set('test.ollama.timeout', 300)
        assert config.get('test.ollama.timeout') == 300
    
    def test_invalid_type_conversion_fallback(self, temp_config_dir):
        """Test that invalid type conversion falls back to string."""
        os.environ['TEST_OLLAMA_MAX_TOKENS'] = 'not_a_number'
        
        config = Config(str(temp_config_dir))
        value = config.get('test.ollama.max_tokens')
        
        # Should fall back to string with warning
        assert value == 'not_a_number'
        
        del os.environ['TEST_OLLAMA_MAX_TOKENS']
    
    def test_to_dict(self, temp_config_dir):
        """Test exporting config to dictionary."""
        config = Config(str(temp_config_dir))
        
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert 'test' in config_dict

