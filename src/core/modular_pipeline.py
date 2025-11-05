"""
Modular Context Engineering Pipeline.

This module provides the core infrastructure for pluggable context engineering
techniques. Each technique is implemented as a module that can be independently
enabled, configured, and evaluated.

The pipeline orchestrates the execution of enabled modules and aggregates metrics
from all active modules.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import logging
import time

from src.core.context_config import ContextEngineeringConfig

logger = logging.getLogger(__name__)


@dataclass
class ModuleMetrics:
    """
    Metrics collected from a context engineering module.
    
    Attributes:
        module_name: Name of the module
        execution_time_ms: Time taken to execute the module
        input_tokens: Number of tokens in input
        output_tokens: Number of tokens in output
        technique_specific: Dictionary of technique-specific metrics
    """
    module_name: str
    execution_time_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    technique_specific: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "module_name": self.module_name,
            "execution_time_ms": self.execution_time_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "technique_specific": self.technique_specific
        }


@dataclass
class PipelineContext:
    """
    Context passed through the pipeline.
    
    Contains the query, accumulated context, and metadata that modules
    can read from and write to.
    
    Attributes:
        query: Original user query
        context: Accumulated context text
        metadata: Additional metadata (e.g., retrieved documents, entities)
        conversation_history: Previous conversation turns
    """
    query: str
    context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "query": self.query,
            "context": self.context,
            "metadata": self.metadata,
            "conversation_history": self.conversation_history
        }


class ContextEngineeringModule(ABC):
    """
    Abstract base class for context engineering modules.
    
    Each technique (RAG, compression, reranking, etc.) extends this class
    and implements the required methods.
    """
    
    def __init__(self, name: str):
        """
        Initialize the module.
        
        Args:
            name: Unique name for this module
        """
        self.name = name
        self.enabled = False
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the module with specific settings.
        
        Args:
            config: Configuration dictionary for this module
        """
        pass
    
    @abstractmethod
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process the context through this module.
        
        Modules should read from the context, perform their technique,
        and update the context with new information.
        
        Args:
            context: Current pipeline context
            
        Returns:
            Updated pipeline context
        """
        pass
    
    @abstractmethod
    def get_metrics(self) -> ModuleMetrics:
        """
        Get metrics collected during the last process() call.
        
        Returns:
            ModuleMetrics object with execution metrics
        """
        pass
    
    def is_enabled(self) -> bool:
        """Check if the module is enabled."""
        return self.enabled
    
    def enable(self) -> None:
        """Enable the module."""
        self.enabled = True
        self.logger.info(f"{self.name} module enabled")
    
    def disable(self) -> None:
        """Disable the module."""
        self.enabled = False
        self.logger.info(f"{self.name} module disabled")


# ============================================================================
# STUB MODULE IMPLEMENTATIONS
# ============================================================================
# These are placeholders that will be fully implemented in future phases.
# They currently pass through the context unchanged but provide the interface
# for future implementation.
# ============================================================================


class RAGModule(ContextEngineeringModule):
    """
    Retrieval-Augmented Generation module (Phase 3).
    
    This module will retrieve relevant documents from a vector database
    and inject them into the context.
    
    Future implementation will include:
    - Vector database integration
    - Document chunking and embedding
    - Similarity search
    - Context assembly
    """
    
    def __init__(self):
        super().__init__("RAG")
        self.chunk_size = 512
        self.chunk_overlap = 50
        self.top_k = 5
        self.similarity_threshold = 0.7
        self.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        self._last_metrics = ModuleMetrics(module_name=self.name)
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure RAG parameters."""
        self.chunk_size = config.get("chunk_size", self.chunk_size)
        self.chunk_overlap = config.get("chunk_overlap", self.chunk_overlap)
        self.top_k = config.get("top_k", self.top_k)
        self.similarity_threshold = config.get("similarity_threshold", self.similarity_threshold)
        self.embedding_model = config.get("embedding_model", self.embedding_model)
        self.logger.info(
            f"RAG configured: chunk_size={self.chunk_size}, "
            f"top_k={self.top_k}, threshold={self.similarity_threshold}"
        )
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process context through RAG (stub implementation).
        
        Future: Will retrieve relevant documents and inject into context.
        """
        start_time = time.time()
        
        # Stub: Just pass through for now
        # TODO Phase 3: Implement vector retrieval
        self.logger.info(f"RAG processing query: {context.query[:50]}...")
        
        # Placeholder: Add a note that RAG would be applied here
        context.metadata["rag_status"] = "stub - not yet implemented"
        context.metadata["rag_config"] = {
            "chunk_size": self.chunk_size,
            "top_k": self.top_k,
            "similarity_threshold": self.similarity_threshold
        }
        
        execution_time = (time.time() - start_time) * 1000
        self._last_metrics = ModuleMetrics(
            module_name=self.name,
            execution_time_ms=execution_time,
            technique_specific={
                "retrieved_docs": 0,  # Placeholder
                "status": "stub"
            }
        )
        
        return context
    
    def get_metrics(self) -> ModuleMetrics:
        """Get RAG metrics from last execution."""
        return self._last_metrics


class CompressionModule(ContextEngineeringModule):
    """
    Context compression module (Phase 4).
    
    This module will compress context to reduce token usage while
    preserving important information.
    
    Future implementation will include:
    - Extractive summarization
    - Importance scoring
    - Token budget management
    """
    
    def __init__(self):
        super().__init__("Compression")
        self.compression_ratio = 0.5
        self.preserve_entities = True
        self.preserve_questions = True
        self.max_compressed_tokens = 2048
        self._last_metrics = ModuleMetrics(module_name=self.name)
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure compression parameters."""
        self.compression_ratio = config.get("compression_ratio", self.compression_ratio)
        self.preserve_entities = config.get("preserve_entities", self.preserve_entities)
        self.preserve_questions = config.get("preserve_questions", self.preserve_questions)
        self.max_compressed_tokens = config.get("max_compressed_tokens", self.max_compressed_tokens)
        self.logger.info(f"Compression configured: ratio={self.compression_ratio}")
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process context through compression (stub implementation).
        
        Future: Will compress context to reduce token usage.
        """
        start_time = time.time()
        
        # Stub: Just pass through for now
        # TODO Phase 4: Implement compression
        self.logger.info("Compression processing (stub)")
        
        context.metadata["compression_status"] = "stub - not yet implemented"
        context.metadata["compression_config"] = {
            "compression_ratio": self.compression_ratio,
            "preserve_entities": self.preserve_entities
        }
        
        execution_time = (time.time() - start_time) * 1000
        self._last_metrics = ModuleMetrics(
            module_name=self.name,
            execution_time_ms=execution_time,
            technique_specific={
                "compression_ratio": 1.0,  # No compression in stub
                "tokens_saved": 0,
                "status": "stub"
            }
        )
        
        return context
    
    def get_metrics(self) -> ModuleMetrics:
        """Get compression metrics from last execution."""
        return self._last_metrics


class RerankingModule(ContextEngineeringModule):
    """
    Document reranking module (Phase 5).
    
    This module will rerank retrieved documents to improve relevance.
    
    Future implementation will include:
    - Cross-encoder reranking
    - Multi-stage retrieval
    - Diversity-aware reranking
    """
    
    def __init__(self):
        super().__init__("Reranking")
        self.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self.top_n_after_rerank = 3
        self.rerank_threshold = 0.6
        self._last_metrics = ModuleMetrics(module_name=self.name)
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure reranking parameters."""
        self.reranker_model = config.get("reranker_model", self.reranker_model)
        self.top_n_after_rerank = config.get("top_n_after_rerank", self.top_n_after_rerank)
        self.rerank_threshold = config.get("rerank_threshold", self.rerank_threshold)
        self.logger.info(f"Reranking configured: top_n={self.top_n_after_rerank}")
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process context through reranking (stub implementation).
        
        Future: Will rerank retrieved documents for better relevance.
        """
        start_time = time.time()
        
        # Stub: Just pass through for now
        # TODO Phase 5: Implement reranking
        self.logger.info("Reranking processing (stub)")
        
        context.metadata["reranking_status"] = "stub - not yet implemented"
        
        execution_time = (time.time() - start_time) * 1000
        self._last_metrics = ModuleMetrics(
            module_name=self.name,
            execution_time_ms=execution_time,
            technique_specific={
                "reranked_docs": 0,
                "status": "stub"
            }
        )
        
        return context
    
    def get_metrics(self) -> ModuleMetrics:
        """Get reranking metrics from last execution."""
        return self._last_metrics


class CachingModule(ContextEngineeringModule):
    """
    Semantic caching module (Phase 4).
    
    This module will cache responses for similar queries to reduce
    redundant processing.
    
    Future implementation will include:
    - Semantic similarity for cache keys
    - Cache invalidation strategies
    - Cache hit rate monitoring
    """
    
    def __init__(self):
        super().__init__("Caching")
        self.similarity_threshold = 0.95
        self.max_cache_size = 1000
        self.ttl_seconds = 3600
        self._last_metrics = ModuleMetrics(module_name=self.name)
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure caching parameters."""
        self.similarity_threshold = config.get("similarity_threshold", self.similarity_threshold)
        self.max_cache_size = config.get("max_cache_size", self.max_cache_size)
        self.ttl_seconds = config.get("ttl_seconds", self.ttl_seconds)
        self.logger.info(f"Caching configured: threshold={self.similarity_threshold}")
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process context through caching (stub implementation).
        
        Future: Will check cache and return cached response if found.
        """
        start_time = time.time()
        
        # Stub: Just pass through for now
        # TODO Phase 4: Implement caching
        self.logger.info("Caching processing (stub)")
        
        context.metadata["caching_status"] = "stub - not yet implemented"
        context.metadata["cache_hit"] = False
        
        execution_time = (time.time() - start_time) * 1000
        self._last_metrics = ModuleMetrics(
            module_name=self.name,
            execution_time_ms=execution_time,
            technique_specific={
                "cache_hit": False,
                "cache_size": 0,
                "status": "stub"
            }
        )
        
        return context
    
    def get_metrics(self) -> ModuleMetrics:
        """Get caching metrics from last execution."""
        return self._last_metrics


class HybridSearchModule(ContextEngineeringModule):
    """
    Hybrid search module (Phase 5).
    
    This module will combine BM25 keyword search with vector search
    for improved retrieval.
    
    Future implementation will include:
    - BM25 keyword search
    - Hybrid scoring
    - Search result fusion
    """
    
    def __init__(self):
        super().__init__("HybridSearch")
        self.bm25_weight = 0.3
        self.vector_weight = 0.7
        self.top_k_per_method = 10
        self._last_metrics = ModuleMetrics(module_name=self.name)
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure hybrid search parameters."""
        self.bm25_weight = config.get("bm25_weight", self.bm25_weight)
        self.vector_weight = config.get("vector_weight", self.vector_weight)
        self.top_k_per_method = config.get("top_k_per_method", self.top_k_per_method)
        self.logger.info(
            f"HybridSearch configured: bm25_weight={self.bm25_weight}, "
            f"vector_weight={self.vector_weight}"
        )
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process context through hybrid search (stub implementation).
        
        Future: Will perform hybrid BM25+vector search.
        """
        start_time = time.time()
        
        # Stub: Just pass through for now
        # TODO Phase 5: Implement hybrid search
        self.logger.info("HybridSearch processing (stub)")
        
        context.metadata["hybrid_search_status"] = "stub - not yet implemented"
        
        execution_time = (time.time() - start_time) * 1000
        self._last_metrics = ModuleMetrics(
            module_name=self.name,
            execution_time_ms=execution_time,
            technique_specific={
                "bm25_results": 0,
                "vector_results": 0,
                "status": "stub"
            }
        )
        
        return context
    
    def get_metrics(self) -> ModuleMetrics:
        """Get hybrid search metrics from last execution."""
        return self._last_metrics


class MemoryModule(ContextEngineeringModule):
    """
    Conversation memory module (Phase 4).
    
    This module will manage conversation history and inject
    relevant context from previous turns.
    
    Future implementation will include:
    - Conversation history management
    - Summarization of long conversations
    - Temporal weighting
    """
    
    def __init__(self):
        super().__init__("Memory")
        self.max_conversation_turns = 10
        self.include_summaries = True
        self.summary_trigger_turns = 5
        self._last_metrics = ModuleMetrics(module_name=self.name)
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure memory parameters."""
        self.max_conversation_turns = config.get("max_conversation_turns", self.max_conversation_turns)
        self.include_summaries = config.get("include_summaries", self.include_summaries)
        self.summary_trigger_turns = config.get("summary_trigger_turns", self.summary_trigger_turns)
        self.logger.info(f"Memory configured: max_turns={self.max_conversation_turns}")
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process context through memory (stub implementation).
        
        Future: Will inject relevant conversation history.
        """
        start_time = time.time()
        
        # Stub: Just pass through for now
        # TODO Phase 4: Implement memory
        self.logger.info("Memory processing (stub)")
        
        context.metadata["memory_status"] = "stub - not yet implemented"
        context.metadata["conversation_turns_used"] = 0
        
        execution_time = (time.time() - start_time) * 1000
        self._last_metrics = ModuleMetrics(
            module_name=self.name,
            execution_time_ms=execution_time,
            technique_specific={
                "conversation_turns": len(context.conversation_history),
                "memory_tokens": 0,
                "status": "stub"
            }
        )
        
        return context
    
    def get_metrics(self) -> ModuleMetrics:
        """Get memory metrics from last execution."""
        return self._last_metrics


# ============================================================================
# PIPELINE ORCHESTRATOR
# ============================================================================


class ContextPipeline:
    """
    Orchestrates the execution of enabled context engineering modules.
    
    The pipeline:
    1. Initializes all available modules
    2. Configures enabled modules based on ContextEngineeringConfig
    3. Executes modules in sequence
    4. Aggregates metrics from all modules
    
    Attributes:
        config: Context engineering configuration
        modules: Dictionary of available modules
    """
    
    def __init__(self, config: Optional[ContextEngineeringConfig] = None):
        """
        Initialize the context pipeline.
        
        Args:
            config: Optional configuration (default: baseline with all disabled)
        """
        self.config = config or ContextEngineeringConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize all available modules
        self.modules: Dict[str, ContextEngineeringModule] = {
            "rag": RAGModule(),
            "compression": CompressionModule(),
            "reranking": RerankingModule(),
            "caching": CachingModule(),
            "hybrid_search": HybridSearchModule(),
            "memory": MemoryModule()
        }
        
        # Configure modules based on config
        self._configure_modules()
        
        self.logger.info("Context pipeline initialized with %d modules", len(self.modules))
    
    def _configure_modules(self) -> None:
        """Configure all modules based on the current config."""
        # RAG
        if self.config.rag_enabled:
            self.modules["rag"].enable()
            self.modules["rag"].configure(self.config.rag.__dict__)
        else:
            self.modules["rag"].disable()
        
        # Compression
        if self.config.compression_enabled:
            self.modules["compression"].enable()
            self.modules["compression"].configure(self.config.compression.__dict__)
        else:
            self.modules["compression"].disable()
        
        # Reranking
        if self.config.reranking_enabled:
            self.modules["reranking"].enable()
            self.modules["reranking"].configure(self.config.reranking.__dict__)
        else:
            self.modules["reranking"].disable()
        
        # Caching
        if self.config.caching_enabled:
            self.modules["caching"].enable()
            self.modules["caching"].configure(self.config.caching.__dict__)
        else:
            self.modules["caching"].disable()
        
        # Hybrid search
        if self.config.hybrid_search_enabled:
            self.modules["hybrid_search"].enable()
            self.modules["hybrid_search"].configure(self.config.hybrid_search.__dict__)
        else:
            self.modules["hybrid_search"].disable()
        
        # Memory
        if self.config.memory_enabled:
            self.modules["memory"].enable()
            self.modules["memory"].configure(self.config.memory.__dict__)
        else:
            self.modules["memory"].disable()
        
        enabled = [name for name, module in self.modules.items() if module.is_enabled()]
        self.logger.info(f"Enabled modules: {enabled}")
    
    def update_config(self, config: ContextEngineeringConfig) -> None:
        """
        Update pipeline configuration.
        
        Args:
            config: New configuration to apply
        """
        self.config = config
        self._configure_modules()
        self.logger.info("Pipeline configuration updated")
    
    def process(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> PipelineContext:
        """
        Process a query through all enabled modules.
        
        Modules are executed in this order:
        1. Memory (inject conversation history)
        2. Caching (check if cached response exists)
        3. RAG (retrieve relevant documents)
        4. Hybrid Search (combine with keyword search)
        5. Reranking (improve retrieval quality)
        6. Compression (reduce token usage)
        
        Args:
            query: User query to process
            conversation_history: Optional conversation history
            
        Returns:
            PipelineContext with accumulated context and metadata
        """
        start_time = time.time()
        
        # Initialize context
        context = PipelineContext(
            query=query,
            conversation_history=conversation_history or []
        )
        
        # Execute enabled modules in order
        module_order = ["memory", "caching", "rag", "hybrid_search", "reranking", "compression"]
        
        for module_name in module_order:
            module = self.modules.get(module_name)
            if module and module.is_enabled():
                self.logger.debug(f"Executing module: {module_name}")
                try:
                    context = module.process(context)
                except Exception as e:
                    self.logger.error(f"Error in module {module_name}: {e}", exc_info=True)
                    # Continue with other modules even if one fails
                    context.metadata[f"{module_name}_error"] = str(e)
        
        total_time = (time.time() - start_time) * 1000
        self.logger.info(f"Pipeline execution completed in {total_time:.2f}ms")
        
        return context
    
    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated metrics from all enabled modules.
        
        Returns:
            Dictionary with metrics from each enabled module
        """
        metrics = {
            "enabled_modules": [],
            "total_execution_time_ms": 0.0,
            "modules": {}
        }
        
        for name, module in self.modules.items():
            if module.is_enabled():
                module_metrics = module.get_metrics()
                metrics["enabled_modules"].append(name)
                metrics["total_execution_time_ms"] += module_metrics.execution_time_ms
                metrics["modules"][name] = module_metrics.to_dict()
        
        return metrics
    
    def get_enabled_modules(self) -> List[str]:
        """
        Get list of currently enabled module names.
        
        Returns:
            List of enabled module names
        """
        return [name for name, module in self.modules.items() if module.is_enabled()]
    
    def get_module(self, name: str) -> Optional[ContextEngineeringModule]:
        """
        Get a specific module by name.
        
        Args:
            name: Module name
            
        Returns:
            Module instance or None if not found
        """
        return self.modules.get(name)

