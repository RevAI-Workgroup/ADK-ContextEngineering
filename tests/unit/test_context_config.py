"""
Unit tests for context engineering configuration system.
"""

import pytest
import json
from src.core.context_config import (
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


class TestRAGConfig:
    """Test RAG configuration."""
    
    def test_default_values(self):
        """Test RAG config has correct default values."""
        config = RAGConfig()
        assert config.enabled is False
        assert config.chunk_size == 512
        assert config.chunk_overlap == 50
        assert config.top_k == 5
        assert config.similarity_threshold == 0.7
    
    def test_custom_values(self):
        """Test RAG config with custom values."""
        config = RAGConfig(
            enabled=True,
            chunk_size=1024,
            top_k=10
        )
        assert config.enabled is True
        assert config.chunk_size == 1024
        assert config.top_k == 10


class TestContextEngineeringConfig:
    """Test main context engineering configuration."""
    
    def test_default_configuration(self):
        """Test default configuration has all techniques disabled."""
        config = ContextEngineeringConfig()
        assert config.rag_enabled is False
        assert config.compression_enabled is False
        assert config.reranking_enabled is False
        assert config.caching_enabled is False
        assert config.hybrid_search_enabled is False
        assert config.memory_enabled is False
    
    def test_enable_rag(self):
        """Test enabling RAG technique."""
        config = ContextEngineeringConfig()
        config.rag.enabled = True
        assert config.rag_enabled is True
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = ContextEngineeringConfig()
        config.rag.enabled = True
        
        data = config.to_dict()
        assert isinstance(data, dict)
        assert 'rag' in data
        assert data['rag']['enabled'] is True
    
    def test_to_json(self):
        """Test conversion to JSON."""
        config = ContextEngineeringConfig()
        json_str = config.to_json()
        
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert 'rag' in data
        assert 'compression' in data
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            'rag': {'enabled': True, 'top_k': 10},
            'compression': {'enabled': True},
            'model': 'qwen2.5:3b',
        }
        
        config = ContextEngineeringConfig.from_dict(data)
        assert config.rag_enabled is True
        assert config.rag.top_k == 10
        assert config.compression_enabled is True
        assert config.model == 'qwen2.5:3b'
    
    def test_from_json(self):
        """Test creation from JSON string."""
        json_str = json.dumps({
            'rag': {'enabled': True, 'chunk_size': 1024},
            'model': 'qwen2.5:7b',
        })
        
        config = ContextEngineeringConfig.from_json(json_str)
        assert config.rag_enabled is True
        assert config.rag.chunk_size == 1024
    
    def test_get_enabled_techniques(self):
        """Test getting list of enabled techniques."""
        config = ContextEngineeringConfig()
        assert config.get_enabled_techniques() == []
        
        config.rag.enabled = True
        config.compression.enabled = True
        
        techniques = config.get_enabled_techniques()
        assert len(techniques) == 2
        assert 'rag' in techniques
        assert 'compression' in techniques
    
    def test_copy(self):
        """Test creating a deep copy."""
        config1 = ContextEngineeringConfig()
        config1.rag.enabled = True
        config1.rag.top_k = 10
        
        config2 = config1.copy()
        
        # Verify copy has same values
        assert config2.rag_enabled is True
        assert config2.rag.top_k == 10
        
        # Verify it's a deep copy
        config2.rag.top_k = 20
        assert config1.rag.top_k == 10


class TestConfigPresets:
    """Test configuration presets."""
    
    def test_baseline_preset(self):
        """Test baseline preset has all techniques disabled."""
        config = ContextEngineeringConfig.from_preset(ConfigPreset.BASELINE)
        assert config.get_enabled_techniques() == []
    
    def test_basic_rag_preset(self):
        """Test basic RAG preset."""
        config = ContextEngineeringConfig.from_preset(ConfigPreset.BASIC_RAG)
        assert config.rag_enabled is True
        assert config.compression_enabled is False
        assert config.reranking_enabled is False
    
    def test_advanced_rag_preset(self):
        """Test advanced RAG preset."""
        config = ContextEngineeringConfig.from_preset(ConfigPreset.ADVANCED_RAG)
        assert config.rag_enabled is True
        assert config.reranking_enabled is True
        assert config.hybrid_search_enabled is True
        assert config.rag.top_k == 10  # More for reranking
    
    def test_full_stack_preset(self):
        """Test full stack preset has all techniques enabled."""
        config = ContextEngineeringConfig.from_preset(ConfigPreset.FULL_STACK)
        techniques = config.get_enabled_techniques()
        assert len(techniques) == 6
        assert 'rag' in techniques
        assert 'compression' in techniques
        assert 'reranking' in techniques
        assert 'caching' in techniques
        assert 'hybrid_search' in techniques
        assert 'memory' in techniques
    
    def test_get_preset_names(self):
        """Test getting list of preset names."""
        names = get_preset_names()
        assert len(names) == 4
        assert 'baseline' in names
        assert 'basic_rag' in names
        assert 'advanced_rag' in names
        assert 'full_stack' in names
    
    def test_get_preset_configs(self):
        """Test getting all preset configurations."""
        presets = get_preset_configs()
        assert len(presets) == 4
        assert 'baseline' in presets
        assert isinstance(presets['baseline'], ContextEngineeringConfig)


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_valid_baseline_config(self):
        """Test baseline config is valid."""
        config = ContextEngineeringConfig()
        assert config.is_valid()
        assert config.validate() == []
    
    def test_valid_rag_config(self):
        """Test valid RAG configuration."""
        config = ContextEngineeringConfig()
        config.rag.enabled = True
        config.rag.chunk_size = 512
        config.rag.chunk_overlap = 50
        config.rag.top_k = 5
        
        assert config.is_valid()
    
    def test_invalid_chunk_size(self):
        """Test validation catches invalid chunk size."""
        config = ContextEngineeringConfig()
        config.rag.enabled = True
        config.rag.chunk_size = 0
        
        errors = config.validate()
        assert len(errors) > 0
        assert any('chunk_size' in error for error in errors)
    
    def test_invalid_chunk_overlap(self):
        """Test validation catches invalid chunk overlap."""
        config = ContextEngineeringConfig()
        config.rag.enabled = True
        config.rag.chunk_size = 100
        config.rag.chunk_overlap = 150  # Greater than chunk_size
        
        errors = config.validate()
        assert len(errors) > 0
        assert any('overlap' in error.lower() for error in errors)
    
    def test_invalid_similarity_threshold(self):
        """Test validation catches invalid similarity threshold."""
        config = ContextEngineeringConfig()
        config.rag.enabled = True
        config.rag.similarity_threshold = 1.5  # Must be 0-1
        
        errors = config.validate()
        assert len(errors) > 0
        assert any('similarity_threshold' in error for error in errors)
    
    def test_reranking_requires_rag(self):
        """Test validation catches reranking without RAG."""
        config = ContextEngineeringConfig()
        config.reranking.enabled = True
        config.rag.enabled = False
        
        errors = config.validate()
        assert len(errors) > 0
        assert any('requires RAG' in error for error in errors)
    
    def test_reranking_top_n_exceeds_rag_top_k(self):
        """Test validation catches reranking top_n > RAG top_k."""
        config = ContextEngineeringConfig()
        config.rag.enabled = True
        config.rag.top_k = 5
        config.reranking.enabled = True
        config.reranking.top_n_after_rerank = 10
        
        errors = config.validate()
        assert len(errors) > 0
        assert any('top_n' in error.lower() for error in errors)
    
    def test_hybrid_search_requires_rag(self):
        """Test validation catches hybrid search without RAG."""
        config = ContextEngineeringConfig()
        config.hybrid_search.enabled = True
        config.rag.enabled = False
        
        errors = config.validate()
        assert len(errors) > 0
        assert any('requires RAG' in error for error in errors)
    
    def test_hybrid_search_weights_sum_to_one(self):
        """Test validation catches hybrid search weights not summing to 1."""
        config = ContextEngineeringConfig()
        config.rag.enabled = True
        config.hybrid_search.enabled = True
        config.hybrid_search.bm25_weight = 0.5
        config.hybrid_search.vector_weight = 0.6  # Sum = 1.1
        
        errors = config.validate()
        assert len(errors) > 0
        assert any('sum to 1' in error.lower() for error in errors)
    
    def test_invalid_compression_ratio(self):
        """Test validation catches invalid compression ratio."""
        config = ContextEngineeringConfig()
        config.compression.enabled = True
        config.compression.compression_ratio = 1.5  # Must be 0-1
        
        errors = config.validate()
        assert len(errors) > 0
        assert any('compression ratio' in error.lower() for error in errors)
    
    def test_invalid_temperature(self):
        """Test validation catches invalid temperature."""
        config = ContextEngineeringConfig()
        config.temperature = 3.0  # Must be 0-2
        
        errors = config.validate()
        assert len(errors) > 0
        assert any('temperature' in error for error in errors)
    
    def test_empty_model(self):
        """Test validation catches empty model."""
        config = ContextEngineeringConfig()
        config.model = ""
        
        errors = config.validate()
        assert len(errors) > 0
        assert any('model' in error for error in errors)


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_get_default_config(self):
        """Test getting default configuration."""
        config = get_default_config()
        assert isinstance(config, ContextEngineeringConfig)
        assert config.get_enabled_techniques() == []
    
    def test_get_preset_configs_returns_dict(self):
        """Test get_preset_configs returns dictionary."""
        presets = get_preset_configs()
        assert isinstance(presets, dict)
        assert all(isinstance(v, ContextEngineeringConfig) for v in presets.values())
    
    def test_get_preset_names_returns_list(self):
        """Test get_preset_names returns list of strings."""
        names = get_preset_names()
        assert isinstance(names, list)
        assert all(isinstance(name, str) for name in names)

