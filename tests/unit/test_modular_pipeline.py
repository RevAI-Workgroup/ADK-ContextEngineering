"""
Unit tests for the modular pipeline system.

Tests the ContextEngineeringModule base class, stub modules,
and ContextPipeline orchestrator.
"""

import pytest
from src.core.modular_pipeline import (
    ContextEngineeringModule,
    ContextPipeline,
    PipelineContext,
    ModuleMetrics,
    RAGModule,
    CompressionModule,
    RerankingModule,
    CachingModule,
    HybridSearchModule,
    MemoryModule
)
from src.core.context_config import ContextEngineeringConfig, ConfigPreset


class TestPipelineContext:
    """Test PipelineContext dataclass."""
    
    def test_pipeline_context_creation(self):
        """Test creating a pipeline context."""
        context = PipelineContext(query="What is Python?")
        assert context.query == "What is Python?"
        assert context.context == ""
        assert context.metadata == {}
        assert context.conversation_history == []
    
    def test_pipeline_context_to_dict(self):
        """Test converting context to dictionary."""
        context = PipelineContext(
            query="Test query",
            context="Test context",
            metadata={"key": "value"}
        )
        context_dict = context.to_dict()
        assert context_dict["query"] == "Test query"
        assert context_dict["context"] == "Test context"
        assert context_dict["metadata"] == {"key": "value"}


class TestModuleMetrics:
    """Test ModuleMetrics dataclass."""
    
    def test_module_metrics_creation(self):
        """Test creating module metrics."""
        metrics = ModuleMetrics(
            module_name="test_module",
            execution_time_ms=100.5,
            input_tokens=50,
            output_tokens=60
        )
        assert metrics.module_name == "test_module"
        assert metrics.execution_time_ms == 100.5
        assert metrics.input_tokens == 50
        assert metrics.output_tokens == 60
    
    def test_module_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = ModuleMetrics(
            module_name="test_module",
            execution_time_ms=100.5
        )
        metrics_dict = metrics.to_dict()
        assert metrics_dict["module_name"] == "test_module"
        assert metrics_dict["execution_time_ms"] == 100.5


class TestRAGModule:
    """Test RAG module stub implementation."""
    
    def test_rag_module_creation(self):
        """Test creating a RAG module."""
        module = RAGModule()
        assert module.name == "RAG"
        assert not module.is_enabled()
    
    def test_rag_module_configuration(self):
        """Test configuring RAG module."""
        module = RAGModule()
        config = {
            "chunk_size": 1024,
            "top_k": 10,
            "similarity_threshold": 0.8
        }
        module.configure(config)
        assert module.chunk_size == 1024
        assert module.top_k == 10
        assert module.similarity_threshold == 0.8
    
    def test_rag_module_process(self):
        """Test processing through RAG module (stub)."""
        module = RAGModule()
        module.enable()
        
        context = PipelineContext(query="What is RAG?")
        result = module.process(context)
        
        # Stub should pass through and add metadata
        assert result.query == "What is RAG?"
        assert "rag_status" in result.metadata
        assert result.metadata["rag_status"] == "stub - not yet implemented"
    
    def test_rag_module_metrics(self):
        """Test getting metrics from RAG module."""
        module = RAGModule()
        module.enable()
        
        context = PipelineContext(query="Test")
        module.process(context)
        
        metrics = module.get_metrics()
        assert metrics.module_name == "RAG"
        assert metrics.execution_time_ms >= 0
        assert "status" in metrics.technique_specific
        assert metrics.technique_specific["status"] == "stub"


class TestCompressionModule:
    """Test Compression module stub implementation."""
    
    def test_compression_module_creation(self):
        """Test creating a Compression module."""
        module = CompressionModule()
        assert module.name == "Compression"
        assert not module.is_enabled()
    
    def test_compression_module_configuration(self):
        """Test configuring Compression module."""
        module = CompressionModule()
        config = {
            "compression_ratio": 0.7,
            "preserve_entities": False
        }
        module.configure(config)
        assert module.compression_ratio == 0.7
        assert module.preserve_entities is False
    
    def test_compression_module_process(self):
        """Test processing through Compression module (stub)."""
        module = CompressionModule()
        module.enable()
        
        context = PipelineContext(query="Long text to compress")
        result = module.process(context)
        
        # Stub should pass through and add metadata
        assert result.query == "Long text to compress"
        assert "compression_status" in result.metadata


class TestContextPipeline:
    """Test ContextPipeline orchestrator."""
    
    def test_pipeline_creation_default(self):
        """Test creating pipeline with default config."""
        pipeline = ContextPipeline()
        
        # Default config should have all modules disabled
        assert len(pipeline.modules) == 6  # All 6 modules
        enabled = pipeline.get_enabled_modules()
        assert len(enabled) == 0
    
    def test_pipeline_creation_with_config(self):
        """Test creating pipeline with specific config."""
        config = ContextEngineeringConfig()
        config.rag.enabled = True
        config.compression.enabled = True
        
        pipeline = ContextPipeline(config)
        
        enabled = pipeline.get_enabled_modules()
        assert "rag" in enabled
        assert "compression" in enabled
        assert len(enabled) == 2
    
    def test_pipeline_with_preset(self):
        """Test creating pipeline with preset config."""
        config = ContextEngineeringConfig.from_preset(ConfigPreset.BASIC_RAG)
        pipeline = ContextPipeline(config)
        
        enabled = pipeline.get_enabled_modules()
        assert "rag" in enabled
        assert len(enabled) == 1
    
    def test_pipeline_process_no_modules(self):
        """Test processing with no modules enabled."""
        pipeline = ContextPipeline()
        
        result = pipeline.process("What is Python?")
        
        assert result.query == "What is Python?"
        assert result.context == ""
    
    def test_pipeline_process_with_modules(self):
        """Test processing with modules enabled."""
        config = ContextEngineeringConfig()
        config.rag.enabled = True
        config.compression.enabled = True
        
        pipeline = ContextPipeline(config)
        result = pipeline.process("What is Python?")
        
        assert result.query == "What is Python?"
        # Stub modules should add metadata
        assert "rag_status" in result.metadata
        assert "compression_status" in result.metadata
    
    def test_pipeline_get_metrics(self):
        """Test getting aggregated metrics from pipeline."""
        config = ContextEngineeringConfig()
        config.rag.enabled = True
        config.compression.enabled = True
        
        pipeline = ContextPipeline(config)
        pipeline.process("Test query")
        
        metrics = pipeline.get_aggregated_metrics()
        assert "enabled_modules" in metrics
        assert "rag" in metrics["enabled_modules"]
        assert "compression" in metrics["enabled_modules"]
        assert "total_execution_time_ms" in metrics
        assert metrics["total_execution_time_ms"] >= 0
    
    def test_pipeline_update_config(self):
        """Test updating pipeline configuration."""
        pipeline = ContextPipeline()
        assert len(pipeline.get_enabled_modules()) == 0
        
        # Update config to enable RAG
        new_config = ContextEngineeringConfig()
        new_config.rag.enabled = True
        pipeline.update_config(new_config)
        
        assert "rag" in pipeline.get_enabled_modules()
    
    def test_pipeline_get_module(self):
        """Test getting a specific module from pipeline."""
        pipeline = ContextPipeline()
        
        rag_module = pipeline.get_module("rag")
        assert rag_module is not None
        assert rag_module.name == "RAG"
        
        invalid_module = pipeline.get_module("nonexistent")
        assert invalid_module is None
    
    def test_pipeline_full_stack_preset(self):
        """Test pipeline with full stack preset."""
        config = ContextEngineeringConfig.from_preset(ConfigPreset.FULL_STACK)
        pipeline = ContextPipeline(config)
        
        enabled = pipeline.get_enabled_modules()
        # Full stack should enable all modules
        assert len(enabled) == 6
        assert "rag" in enabled
        assert "compression" in enabled
        assert "reranking" in enabled
        assert "caching" in enabled
        assert "hybrid_search" in enabled
        assert "memory" in enabled


class TestAllStubModules:
    """Test all stub modules behave correctly."""
    
    @pytest.mark.parametrize("module_class,module_name", [
        (RAGModule, "RAG"),
        (CompressionModule, "Compression"),
        (RerankingModule, "Reranking"),
        (CachingModule, "Caching"),
        (HybridSearchModule, "HybridSearch"),
        (MemoryModule, "Memory"),
    ])
    def test_module_interface(self, module_class, module_name):
        """Test that all modules implement the required interface."""
        module = module_class()
        
        # Check basic properties
        assert module.name == module_name
        assert not module.is_enabled()
        
        # Test enable/disable
        module.enable()
        assert module.is_enabled()
        module.disable()
        assert not module.is_enabled()
        
        # Test process returns context
        module.enable()
        context = PipelineContext(query="Test")
        result = module.process(context)
        assert isinstance(result, PipelineContext)
        assert result.query == "Test"
        
        # Test get_metrics returns ModuleMetrics
        metrics = module.get_metrics()
        assert isinstance(metrics, ModuleMetrics)
        assert metrics.module_name == module_name
        assert metrics.execution_time_ms >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

