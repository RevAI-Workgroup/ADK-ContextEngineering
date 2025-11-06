"""
Context Engineering Configuration System.

This module provides a dataclass-based configuration system for managing
context engineering techniques that can be toggled on/off and configured
dynamically for experimentation and comparison.
"""

from dataclasses import dataclass, field, asdict, fields
from typing import Dict, Any, List
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
    similarity_threshold: float = 0.75  # Conservative industry-standard for ensuring relevant results
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
    similarity_threshold: float = 0.75
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
        """
        Indicates whether the Naive RAG module is enabled.
        
        Returns:
            True if Naive RAG is enabled, False otherwise.
        """
        return self.naive_rag.enabled

    @property
    def rag_tool_enabled(self) -> bool:
        """
        Return whether the RAG-as-tool module is enabled.
        
        Returns:
            True if the RAG-as-tool configuration is enabled, False otherwise.
        """
        return self.rag_tool.enabled

    @property
    def rag_enabled(self) -> bool:
        """
        Determine whether any retrieval-augmented generation variant is enabled.
        
        Returns:
            `true` if either naive RAG or RAG-as-tool is enabled, `false` otherwise.
        """
        return self.naive_rag.enabled or self.rag_tool.enabled
    
    @property
    def compression_enabled(self) -> bool:
        """
        Indicates whether the context compression module is enabled.
        
        Returns:
            True if compression is enabled, False otherwise.
        """
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
        Serialize the configuration to a pretty-printed JSON string.
        
        Returns:
            A JSON-formatted string representing the configuration.
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @staticmethod
    def _filter_dict_for_dataclass(dataclass_type: type, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter a mapping to the keys that correspond to the fields of a given dataclass.
        
        Unknown keys are ignored to allow forward-compatible deserialization.
        
        Parameters:
            dataclass_type: The dataclass type whose field names should be preserved.
            data: The input mapping to filter.
        
        Returns:
            A dictionary containing only the items from `data` whose keys match the dataclass's field names.
        """
        if not data:
            return {}
        
        # Get set of valid field names from the dataclass
        valid_fields = {f.name for f in fields(dataclass_type)}
        
        # Return only keys that are valid field names
        return {k: v for k, v in data.items() if k in valid_fields}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextEngineeringConfig":
        """
        Construct a ContextEngineeringConfig from a dictionary, with forward- and backward-compatible handling of nested sections.
        
        This classmethod builds nested dataclass instances for each sub-configuration, ignoring unknown keys in those nested dictionaries. It accepts legacy input where the old `'rag'` key may be present in place of the new `'naive_rag'` key.
        
        Parameters:
            data (Dict[str, Any]): Mapping with top-level keys for components (e.g., 'naive_rag' or legacy 'rag', 'rag_tool', 'compression', 'reranking', 'caching', 'hybrid_search', 'memory', 'model', 'max_context_tokens', 'temperature').
        
        Returns:
            ContextEngineeringConfig: A fully populated configuration instance constructed from the provided data, using default values for any missing fields.
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

        # Filter each nested dict to only include valid dataclass field names
        return cls(
            naive_rag=NaiveRAGConfig(**cls._filter_dict_for_dataclass(NaiveRAGConfig, naive_rag_data)),
            rag_tool=RAGToolConfig(**cls._filter_dict_for_dataclass(RAGToolConfig, rag_tool_data)),
            compression=CompressionConfig(**cls._filter_dict_for_dataclass(CompressionConfig, compression_data)),
            reranking=RerankingConfig(**cls._filter_dict_for_dataclass(RerankingConfig, reranking_data)),
            caching=CachingConfig(**cls._filter_dict_for_dataclass(CachingConfig, caching_data)),
            hybrid_search=HybridSearchConfig(**cls._filter_dict_for_dataclass(HybridSearchConfig, hybrid_search_data)),
            memory=MemoryConfig(**cls._filter_dict_for_dataclass(MemoryConfig, memory_data)),
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
        Validate the entire ContextEngineeringConfig and collect configuration errors.
        
        Performs checks across Naive RAG, RAG-as-tool, hybrid search, caching, memory, and general settings and returns a list of human-readable error messages describing any invalid fields (empty list if the configuration is valid).
        
        Returns:
            List[str]: Validation error messages (empty if valid)
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
        # Validate hybrid search settings
        if self.hybrid_search.enabled:
            if not (self.naive_rag.enabled or self.rag_tool.enabled):
                errors.append("Hybrid search requires either Naive RAG or RAG-as-tool to be enabled")
            if not (0.0 <= self.hybrid_search.bm25_weight <= 1.0):
                errors.append("Hybrid search bm25_weight must be between 0 and 1")
            if not (0.0 <= self.hybrid_search.vector_weight <= 1.0):
                errors.append("Hybrid search vector_weight must be between 0 and 1")
            if abs(self.hybrid_search.bm25_weight + self.hybrid_search.vector_weight - 1.0) > 0.01:
                errors.append("Hybrid search weights must sum to 1.0")
            if self.hybrid_search.top_k_per_method <= 0:
                errors.append("Hybrid search top_k_per_method must be positive")
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
        Return the list of enabled context-engineering technique names.
        
        Returns:
            List[str]: A list of enabled technique identifiers chosen from:
                "naive_rag", "rag_tool", "compression", "reranking",
                "caching", "hybrid_search", "memory".
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
