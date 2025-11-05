"""
Context Engineering Configuration System.

This module provides a dataclass-based configuration system for managing
context engineering techniques that can be toggled on/off and configured
dynamically for experimentation and comparison.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
import json
from enum import Enum


class ConfigPreset(str, Enum):
    """Predefined configuration presets for common use cases."""
    BASELINE = "baseline"
    BASIC_RAG = "basic_rag"
    ADVANCED_RAG = "advanced_rag"
    FULL_STACK = "full_stack"


@dataclass
class NaiveRAGConfig:
    """
    Configuration for Naive RAG (Retrieval-Augmented Generation) module.

    Naive RAG automatically retrieves and injects relevant documents into the context
    before every LLM call, without giving the LLM control over when retrieval happens.
    """
    enabled: bool = False
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 5
    similarity_threshold: float = 0.2  # Optimized for better recall with acceptable precision
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class RAGToolConfig:
    """
    Configuration for RAG-as-tool module.

    RAG-as-tool provides the LLM with a retrieval tool that it can choose to invoke
    when it determines that external knowledge is needed to answer a query.
    This approach gives the LLM more control over the retrieval process.
    """
    enabled: bool = False
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 5
    similarity_threshold: float = 0.2
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    tool_name: str = "search_knowledge_base"
    tool_description: str = "Search the knowledge base for relevant information about a specific topic or question"


@dataclass
class CompressionConfig:
    """Configuration for context compression module."""
    enabled: bool = False
    compression_ratio: float = 0.5
    preserve_entities: bool = True
    preserve_questions: bool = True
    max_compressed_tokens: int = 2048


@dataclass
class RerankingConfig:
    """Configuration for document reranking module."""
    enabled: bool = False
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_n_after_rerank: int = 3
    rerank_threshold: float = 0.6


@dataclass
class CachingConfig:
    """Configuration for semantic caching module."""
    enabled: bool = False
    similarity_threshold: float = 0.95
    max_cache_size: int = 1000
    ttl_seconds: int = 3600


@dataclass
class HybridSearchConfig:
    """Configuration for hybrid (BM25 + vector) search module."""
    enabled: bool = False
    bm25_weight: float = 0.3
    vector_weight: float = 0.7
    top_k_per_method: int = 10


@dataclass
class MemoryConfig:
    """Configuration for conversation memory module."""
    enabled: bool = False
    max_conversation_turns: int = 10
    include_summaries: bool = True
    summary_trigger_turns: int = 5


@dataclass
class ContextEngineeringConfig:
    """
    Main configuration dataclass for context engineering techniques.

    This class manages all toggleable techniques and their detailed parameters.
    Each technique can be independently enabled/disabled and configured.

    Attributes:
        naive_rag: Naive RAG module configuration (automatic retrieval)
        rag_tool: RAG-as-tool module configuration (LLM-controlled retrieval)
        compression: Compression module configuration
        reranking: Reranking module configuration
        caching: Caching module configuration
        hybrid_search: Hybrid search module configuration
        memory: Memory module configuration
        model: LLM model identifier
        max_context_tokens: Maximum tokens allowed in context window
        temperature: Sampling temperature for LLM
    """

    naive_rag: NaiveRAGConfig = field(default_factory=NaiveRAGConfig)
    rag_tool: RAGToolConfig = field(default_factory=RAGToolConfig)
    compression: CompressionConfig = field(default_factory=CompressionConfig)
    reranking: RerankingConfig = field(default_factory=RerankingConfig)
    caching: CachingConfig = field(default_factory=CachingConfig)
    hybrid_search: HybridSearchConfig = field(default_factory=HybridSearchConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    
    # General settings
    model: str = "qwen2.5:7b"
    max_context_tokens: int = 4096
    temperature: float = 0.7
    
    @property
    def naive_rag_enabled(self) -> bool:
        """Check if Naive RAG is enabled."""
        return self.naive_rag.enabled

    @property
    def rag_tool_enabled(self) -> bool:
        """Check if RAG-as-tool is enabled."""
        return self.rag_tool.enabled

    @property
    def rag_enabled(self) -> bool:
        """Check if any RAG variant is enabled (backward compatibility)."""
        return self.naive_rag.enabled or self.rag_tool.enabled
    
    @property
    def compression_enabled(self) -> bool:
        """Check if compression is enabled."""
        return self.compression.enabled
    
    @property
    def reranking_enabled(self) -> bool:
        """Check if reranking is enabled."""
        return self.reranking.enabled
    
    @property
    def caching_enabled(self) -> bool:
        """Check if caching is enabled."""
        return self.caching.enabled
    
    @property
    def hybrid_search_enabled(self) -> bool:
        """Check if hybrid search is enabled."""
        return self.hybrid_search.enabled
    
    @property
    def memory_enabled(self) -> bool:
        """Check if memory is enabled."""
        return self.memory.enabled
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of the configuration
        """
        return asdict(self)
    
    def to_json(self) -> str:
        """
        Convert configuration to JSON string.
        
        Returns:
            JSON string representation of the configuration
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextEngineeringConfig":
        """
        Create configuration from dictionary.
        
        Args:
            data: Dictionary containing configuration data
            
        Returns:
            ContextEngineeringConfig instance
        """
        # Extract nested configurations
        # Support both old 'rag' and new 'naive_rag' for backward compatibility
        naive_rag_data = data.get('naive_rag', data.get('rag', {}))
        rag_tool_data = data.get('rag_tool', {})
        compression_data = data.get('compression', {})
        reranking_data = data.get('reranking', {})
        caching_data = data.get('caching', {})
        hybrid_search_data = data.get('hybrid_search', {})
        memory_data = data.get('memory', {})

        return cls(
            naive_rag=NaiveRAGConfig(**naive_rag_data),
            rag_tool=RAGToolConfig(**rag_tool_data),
            compression=CompressionConfig(**compression_data),
            reranking=RerankingConfig(**reranking_data),
            caching=CachingConfig(**caching_data),
            hybrid_search=HybridSearchConfig(**hybrid_search_data),
            memory=MemoryConfig(**memory_data),
            model=data.get('model', 'qwen2.5:7b'),
            max_context_tokens=data.get('max_context_tokens', 4096),
            temperature=data.get('temperature', 0.7)
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "ContextEngineeringConfig":
        """
        Create configuration from JSON string.
        
        Args:
            json_str: JSON string containing configuration data
            
        Returns:
            ContextEngineeringConfig instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_preset(cls, preset: ConfigPreset) -> "ContextEngineeringConfig":
        """
        Create configuration from a predefined preset.
        
        Args:
            preset: ConfigPreset enum value
            
        Returns:
            ContextEngineeringConfig instance with preset settings
        """
        if preset == ConfigPreset.BASELINE:
            # All techniques disabled - baseline performance
            return cls()
        
        elif preset == ConfigPreset.BASIC_RAG:
            # Only Naive RAG enabled with basic settings
            config = cls()
            config.naive_rag.enabled = True
            return config

        elif preset == ConfigPreset.ADVANCED_RAG:
            # Naive RAG + reranking + hybrid search
            config = cls()
            config.naive_rag.enabled = True
            config.naive_rag.top_k = 10  # Retrieve more for reranking
            config.reranking.enabled = True
            config.hybrid_search.enabled = True
            return config

        elif preset == ConfigPreset.FULL_STACK:
            # All techniques enabled with optimal settings
            config = cls()
            config.naive_rag.enabled = True
            config.naive_rag.top_k = 10
            config.rag_tool.enabled = True  # Also enable RAG-as-tool
            config.compression.enabled = True
            config.reranking.enabled = True
            config.caching.enabled = True
            config.hybrid_search.enabled = True
            config.memory.enabled = True
            return config
        
        else:
            raise ValueError(f"Unknown preset: {preset}")
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of validation errors.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate Naive RAG settings
        if self.naive_rag.enabled:
            if self.naive_rag.chunk_size <= 0:
                errors.append("Naive RAG chunk_size must be positive")
            if self.naive_rag.chunk_overlap < 0:
                errors.append("Naive RAG chunk_overlap must be non-negative")
            if self.naive_rag.chunk_overlap >= self.naive_rag.chunk_size:
                errors.append("Naive RAG chunk_overlap must be less than chunk_size")
            if self.naive_rag.top_k <= 0:
                errors.append("Naive RAG top_k must be positive")
            if not (0.0 <= self.naive_rag.similarity_threshold <= 1.0):
                errors.append("Naive RAG similarity_threshold must be between 0 and 1")

        # Validate RAG-as-tool settings
        if self.rag_tool.enabled:
            if self.rag_tool.chunk_size <= 0:
                errors.append("RAG-as-tool chunk_size must be positive")
            if self.rag_tool.chunk_overlap < 0:
                errors.append("RAG-as-tool chunk_overlap must be non-negative")
            if self.rag_tool.chunk_overlap >= self.rag_tool.chunk_size:
                errors.append("RAG-as-tool chunk_overlap must be less than chunk_size")
            if self.rag_tool.top_k <= 0:
                errors.append("RAG-as-tool top_k must be positive")
            if not (0.0 <= self.rag_tool.similarity_threshold <= 1.0):
                errors.append("RAG-as-tool similarity_threshold must be between 0 and 1")
            if not self.rag_tool.tool_name:
                errors.append("RAG-as-tool tool_name must be specified")
        
        # Validate compression settings
        if self.compression.enabled:
            if not (0.0 < self.compression.compression_ratio < 1.0):
                errors.append("Compression ratio must be between 0 and 1")
            if self.compression.max_compressed_tokens <= 0:
                errors.append("Compression max_compressed_tokens must be positive")
        
        # Validate reranking settings
        if self.reranking.enabled:
            if not self.naive_rag.enabled:
                errors.append("Reranking requires Naive RAG to be enabled")
            if self.reranking.top_n_after_rerank <= 0:
                errors.append("Reranking top_n_after_rerank must be positive")
            if self.reranking.top_n_after_rerank > self.naive_rag.top_k:
                errors.append("Reranking top_n cannot exceed Naive RAG top_k")
            if not (0.0 <= self.reranking.rerank_threshold <= 1.0):
                errors.append("Reranking threshold must be between 0 and 1")
        
        # Validate caching settings
        if self.caching.enabled:
            if not (0.0 <= self.caching.similarity_threshold <= 1.0):
                errors.append("Caching similarity_threshold must be between 0 and 1")
            if self.caching.max_cache_size <= 0:
                errors.append("Caching max_cache_size must be positive")
            if self.caching.ttl_seconds <= 0:
                errors.append("Caching ttl_seconds must be positive")
        
        # Validate hybrid search settings
        if self.hybrid_search.enabled:
            if not self.naive_rag.enabled:
                errors.append("Hybrid search requires Naive RAG to be enabled")
            if not (0.0 <= self.hybrid_search.bm25_weight <= 1.0):
                errors.append("Hybrid search bm25_weight must be between 0 and 1")
            if not (0.0 <= self.hybrid_search.vector_weight <= 1.0):
                errors.append("Hybrid search vector_weight must be between 0 and 1")
            if abs(self.hybrid_search.bm25_weight + self.hybrid_search.vector_weight - 1.0) > 0.01:
                errors.append("Hybrid search weights must sum to 1.0")
            if self.hybrid_search.top_k_per_method <= 0:
                errors.append("Hybrid search top_k_per_method must be positive")
        
        # Validate memory settings
        if self.memory.enabled:
            if self.memory.max_conversation_turns <= 0:
                errors.append("Memory max_conversation_turns must be positive")
            if self.memory.summary_trigger_turns <= 0:
                errors.append("Memory summary_trigger_turns must be positive")
            if self.memory.summary_trigger_turns > self.memory.max_conversation_turns:
                errors.append("Memory summary_trigger_turns cannot exceed max_conversation_turns")
        
        # Validate general settings
        if self.max_context_tokens <= 0:
            errors.append("max_context_tokens must be positive")
        if not (0.0 <= self.temperature <= 2.0):
            errors.append("temperature must be between 0 and 2")
        if not self.model:
            errors.append("model must be specified")
        
        return errors
    
    def is_valid(self) -> bool:
        """
        Check if configuration is valid.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        return len(self.validate()) == 0
    
    def get_enabled_techniques(self) -> List[str]:
        """
        Get list of enabled technique names.
        
        Returns:
            List of enabled technique names
        """
        techniques = []
        if self.naive_rag_enabled:
            techniques.append("naive_rag")
        if self.rag_tool_enabled:
            techniques.append("rag_tool")
        if self.compression_enabled:
            techniques.append("compression")
        if self.reranking_enabled:
            techniques.append("reranking")
        if self.caching_enabled:
            techniques.append("caching")
        if self.hybrid_search_enabled:
            techniques.append("hybrid_search")
        if self.memory_enabled:
            techniques.append("memory")
        return techniques
    
    def copy(self) -> "ContextEngineeringConfig":
        """
        Create a deep copy of the configuration.
        
        Returns:
            New ContextEngineeringConfig instance with same values
        """
        return ContextEngineeringConfig.from_dict(self.to_dict())


def get_default_config() -> ContextEngineeringConfig:
    """
    Get the default configuration (baseline).
    
    Returns:
        Default ContextEngineeringConfig instance
    """
    return ContextEngineeringConfig()


def get_preset_configs() -> Dict[str, ContextEngineeringConfig]:
    """
    Get all available preset configurations.
    
    Returns:
        Dictionary mapping preset names to configurations
    """
    return {
        preset.value: ContextEngineeringConfig.from_preset(preset)
        for preset in ConfigPreset
    }


def get_preset_names() -> List[str]:
    """
    Get list of available preset names.
    
    Returns:
        List of preset names
    """
    return [preset.value for preset in ConfigPreset]

