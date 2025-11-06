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

try:
    import tiktoken
except ImportError:
    tiktoken = None

from src.core.context_config import ContextEngineeringConfig

logger = logging.getLogger(__name__)


@dataclass
class ModuleMetrics:
    """
    Metrics collected from a context engineering module.
    
    Attributes:
        module_name: Name of the module
        execution_time_ms: Time taken to execute the module
        input_tokens: Number of tokens in input (uses tiktoken when available, 
                     otherwise word count approximation)
        output_tokens: Number of tokens in output (uses tiktoken when available,
                      otherwise word count approximation)
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


class NaiveRAGModule(ContextEngineeringModule):
    """
    Naive Retrieval-Augmented Generation module (Phase 3).

    This module automatically retrieves relevant documents from a vector database
    and injects them into the context before every LLM call, without giving the LLM
    control over when retrieval happens.

    Features:
    - Vector database integration (ChromaDB)
    - Document chunking and embedding
    - Similarity search
    - Context assembly
    """

    def __init__(self):
        """
        Initialize the NaiveRAG module with default retrieval and tokenization settings.
        
        Sets module name to "NaiveRAG", default retrieval parameters (chunk size, chunk overlap, top-k, similarity threshold, and embedding model), and prepares a ModuleMetrics container for the last run. Initializes lazy state for the vector store and attempts to initialize a tokenizer (tiktoken) for accurate token counting; if tokenizer initialization fails or tiktoken is unavailable, the module falls back to a word-count approximation and logs a warning.
        """
        super().__init__("NaiveRAG")
        self.chunk_size = 512
        self.chunk_overlap = 50
        self.top_k = 5
        self.similarity_threshold = 0.75  # Conservative industry-standard for ensuring relevant results
        self.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        self._last_metrics = ModuleMetrics(module_name=self.name)

        # Lazy initialization of vector store (only when needed)
        self._vector_store = None
        
        # Initialize tokenizer for accurate token counting (initialized once, not per-call)
        self._tokenizer_encoding = None
        if tiktoken is not None:
            try:
                # Use cl100k_base encoding (GPT-4/GPT-3.5 compatible)
                self._tokenizer_encoding = tiktoken.get_encoding("cl100k_base")
                self.logger.debug("Tokenizer initialized for accurate token counting")
            except Exception as e:
                self.logger.warning(f"Failed to initialize tiktoken, falling back to word count approximation: {e}")
                self._tokenizer_encoding = None
        else:
            self.logger.warning("tiktoken not available, using word count approximation for token counting")
    
    def _count_tokens(self, text: Optional[str]) -> int:
        """
        Return token count for a piece of text using the configured tokenizer when available, otherwise approximate by word count.
        
        Parameters:
            text (Optional[str]): Input text; if None or empty, returns 0.
        
        Returns:
            int: Number of tokens (uses tokenizer encoding if available; falls back to a word-count approximation).
        """
        if text is None or not text.strip():
            return 0
        
        if self._tokenizer_encoding is not None:
            try:
                return len(self._tokenizer_encoding.encode(text))
            except Exception as e:
                self.logger.warning(f"Token counting failed, falling back to word count: {e}")
                # Fall back to word count on error
                return len(text.split())
        else:
            # Fallback to word count approximation when tiktoken unavailable
            return len(text.split())
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Update the module's RAG configuration parameters from the given mapping.
        
        Parameters:
            config (Dict[str, Any]): Mapping of configuration values. Recognized keys:
                - "chunk_size" (int): Size of text chunks used for embeddings/search. Defaults to current value.
                - "chunk_overlap" (int): Overlap between adjacent chunks. Defaults to current value.
                - "top_k" (int): Number of top documents to retrieve. Defaults to current value.
                - "similarity_threshold" (float): Minimum similarity score required to include a retrieved document. Defaults to current value.
                - "embedding_model" (str): Name/identifier of the embedding model to use. Defaults to current value.
        
        Side effects:
            Updates instance attributes (chunk_size, chunk_overlap, top_k, similarity_threshold, embedding_model)
            and logs the new configuration summary.
        """
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
        Retrieve relevant documents for the pipeline query and inject retrieval results into the provided PipelineContext.
        
        This updates the context's `context` text with concatenated retrieved chunks and populates `context.metadata` with retrieval details (e.g., `rag_status`, `rag_retrieved_docs`, `rag_sources`, `rag_avg_similarity`, `rag_documents`, and error fields on failure). The method also records execution metrics in the module's `get_metrics()` via `_last_metrics`.
        
        Parameters:
            context (PipelineContext): Pipeline context containing the `query`; will be mutated to include retrieved content and metadata.
        
        Returns:
            PipelineContext: The same PipelineContext instance with retrieval results and metadata applied.
        """
        start_time = time.time()

        self.logger.info(f"RAG processing query: {context.query[:50]}...")

        # Initialize vector store if not already initialized
        if self._vector_store is None:
            try:
                from src.retrieval.vector_store import get_vector_store
                self._vector_store = get_vector_store()
                self.logger.info("Vector store initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize vector store: {e}", exc_info=True)
                # Mark as error and continue
                context.metadata["rag_status"] = "error"
                context.metadata["rag_error"] = str(e)
                self._last_metrics = ModuleMetrics(
                    module_name=self.name,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    technique_specific={"status": "error", "error": str(e)}
                )
                return context

        # Check if vector store has documents
        doc_count = self._vector_store.count()
        if doc_count == 0:
            self.logger.warning("Vector store is empty - no documents to retrieve")
            context.metadata["rag_status"] = "empty"
            context.metadata["rag_message"] = "No documents in vector store"
            self._last_metrics = ModuleMetrics(
                module_name=self.name,
                execution_time_ms=(time.time() - start_time) * 1000,
                technique_specific={
                    "status": "empty",
                    "retrieved_docs": 0,
                    "total_docs_in_store": 0
                }
            )
            return context

        # Perform retrieval
        try:
            results = self._vector_store.search(
                query=context.query,
                top_k=self.top_k,
                similarity_threshold=self.similarity_threshold
            )

            # Assemble context from retrieved documents
            if results:
                retrieved_texts = []
                sources = []
                retrieved_documents = []  # Store detailed document info

                for i, result in enumerate(results):
                    # Format retrieved chunk
                    source = result.metadata.get("source", "unknown")
                    chunk_idx = result.metadata.get("chunk_index", "")
                    similarity = result.similarity

                    # Add to context
                    retrieved_texts.append(
                        f"[Document {i+1}] (similarity: {similarity:.3f}, source: {source})\n"
                        f"{result.text}"
                    )
                    sources.append(source)

                    # Store document details for frontend display
                    retrieved_documents.append({
                        "text": result.text,
                        "source": source,
                        "similarity": float(similarity),
                        "chunk_index": chunk_idx,
                        "metadata": result.metadata
                    })

                # Join all retrieved texts
                context.context = "\n\n---\n\n".join(retrieved_texts)

                # Store metadata
                context.metadata["rag_status"] = "success"
                context.metadata["rag_retrieved_docs"] = len(results)
                context.metadata["rag_sources"] = list(set(sources))  # Unique sources
                context.metadata["rag_avg_similarity"] = (
                    sum(r.similarity for r in results) / len(results)
                )
                context.metadata["rag_documents"] = retrieved_documents  # Add detailed docs

                self.logger.info(
                    f"Retrieved {len(results)} documents "
                    f"(avg similarity: {context.metadata['rag_avg_similarity']:.3f})"
                )

            else:
                # No results above threshold
                context.metadata["rag_status"] = "no_results"
                context.metadata["rag_message"] = (
                    f"No documents found above similarity threshold {self.similarity_threshold}"
                )
                self.logger.warning("No documents retrieved above threshold")

            # Calculate metrics
            execution_time = (time.time() - start_time) * 1000
            self._last_metrics = ModuleMetrics(
                module_name=self.name,
                execution_time_ms=execution_time,
                input_tokens=self._count_tokens(context.query),
                output_tokens=self._count_tokens(context.context),
                technique_specific={
                    "status": context.metadata.get("rag_status"),
                    "retrieved_docs": len(results),
                    "total_docs_in_store": doc_count,
                    "avg_similarity": context.metadata.get("rag_avg_similarity", 0.0),
                    "sources": context.metadata.get("rag_sources", []),
                    "threshold": self.similarity_threshold,
                    "top_k": self.top_k
                }
            )

        except Exception as e:
            self.logger.error(f"RAG retrieval failed: {e}", exc_info=True)
            context.metadata["rag_status"] = "error"
            context.metadata["rag_error"] = str(e)
            self._last_metrics = ModuleMetrics(
                module_name=self.name,
                execution_time_ms=(time.time() - start_time) * 1000,
                technique_specific={"status": "error", "error": str(e)}
            )

        return context
    
    def get_metrics(self) -> ModuleMetrics:
        """
        Retrieve metrics recorded by the last Naive RAG execution.
        
        Returns:
            ModuleMetrics: Metrics from the module's most recent run, including execution time, input/output token counts, and technique-specific data.
        """
        return self._last_metrics


class RAGToolModule(ContextEngineeringModule):
    """
    RAG-as-tool module (Phase 3).

    This module provides the LLM with a retrieval tool that it can choose to invoke
    when it determines that external knowledge is needed to answer a query.
    This gives the LLM more control over the retrieval process.

    The tool is registered and the LLM decides when to use it through function calling.

    Features:
    - Vector database integration (ChromaDB)
    - LLM-controlled retrieval via tool calling
    - Document chunking and embedding
    - Similarity search
    """

    def __init__(self):
        """
        Initialize the RAGToolModule with default retrieval parameters and a tool definition.
        
        Sets default values for chunk_size (512), chunk_overlap (50), top_k (5), similarity_threshold (0.75), and embedding_model ("sentence-transformers/all-MiniLM-L6-v2"); defines the tool name ("search_knowledge_base") and description; initializes _last_metrics for recording module metrics and leaves _vector_store as None for lazy initialization.
        """
        super().__init__("RAGTool")
        self.chunk_size = 512
        self.chunk_overlap = 50
        self.top_k = 5
        self.similarity_threshold = 0.75
        self.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        self.tool_name = "search_knowledge_base"
        self.tool_description = "Search the knowledge base for relevant information about a specific topic or question"
        self._last_metrics = ModuleMetrics(module_name=self.name)

        # Lazy initialization of vector store (only when needed)
        self._vector_store = None

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Update RAG-as-tool configuration from the provided dictionary.
        
        Reads known keys from `config` and updates the module's parameters (chunk_size, chunk_overlap, top_k,
        similarity_threshold, embedding_model, tool_name, tool_description). If a key is missing, the existing
        attribute value is preserved. Logs a short summary of the applied configuration.
        
        Parameters:
            config (Dict[str, Any]): Mapping of configuration keys to values. Recognized keys:
                - "chunk_size"
                - "chunk_overlap"
                - "top_k"
                - "similarity_threshold"
                - "embedding_model"
                - "tool_name"
                - "tool_description"
        """
        self.chunk_size = config.get("chunk_size", self.chunk_size)
        self.chunk_overlap = config.get("chunk_overlap", self.chunk_overlap)
        self.top_k = config.get("top_k", self.top_k)
        self.similarity_threshold = config.get("similarity_threshold", self.similarity_threshold)
        self.embedding_model = config.get("embedding_model", self.embedding_model)
        self.tool_name = config.get("tool_name", self.tool_name)
        self.tool_description = config.get("tool_description", self.tool_description)
        self.logger.info(
            f"RAG-as-tool configured: tool_name={self.tool_name}, "
            f"top_k={self.top_k}, threshold={self.similarity_threshold}"
        )

    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Provide a function-style tool definition for LLM function calling.
        
        Returns:
            A dict representing a function tool definition compatible with OpenAI/Ollama function-calling schemas. The dictionary contains the function name, description, and a JSON schema for parameters including a required `query` string and an optional `top_k` integer (default set to the module's `top_k`).
        """
        return {
            "type": "function",
            "function": {
                "name": self.tool_name,
                "description": self.tool_description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to find relevant information in the knowledge base"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": f"Number of documents to retrieve (default: {self.top_k})",
                            "default": self.top_k
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    def execute_tool(self, query: str, top_k: Optional[int] = None) -> Dict[str, Any]:
        """
        Perform a retrieval search using the RAG tool and return structured retrieval results.
        
        Execute a similarity search against the module's vector store for the given query and return retrieved documents and metadata about the retrieval operation.
        
        Parameters:
            query (str): The natural-language query to search for.
            top_k (Optional[int]): Maximum number of documents to retrieve; if omitted, the module's configured default is used.
        
        Returns:
            Dict[str, Any]: A dictionary describing the outcome. Common keys include:
                - `status`: One of `"success"`, `"no_results"`, `"empty"`, or `"error"`.
                - On `"success"`:
                    - `documents` (List[Dict]): Retrieved items with keys `text`, `source`, `similarity`, `chunk_index`, and `metadata`.
                    - `retrieved_count` (int): Number of documents returned.
                    - `sources` (List[str]): Unique source identifiers for the retrieved documents.
                    - `avg_similarity` (float): Average similarity score of the returned documents.
                    - `execution_time_ms` (float): Retrieval latency in milliseconds.
                - On `"no_results"` or `"empty"`:
                    - `message` (str): Human-readable explanation.
                    - `documents` (List): Empty list.
                - On `"error"`:
                    - `error` (str): Error message.
                    - `documents` (List): Empty list.
        """
        start_time = time.time()
        top_k = top_k or self.top_k

        self.logger.info(f"RAG tool executing search: {query[:50]}...")

        # Initialize vector store if not already initialized
        if self._vector_store is None:
            try:
                from src.retrieval.vector_store import get_vector_store
                self._vector_store = get_vector_store()
                self.logger.info("Vector store initialized for RAG tool")
            except Exception as e:
                self.logger.error(f"Failed to initialize vector store: {e}", exc_info=True)
                return {
                    "status": "error",
                    "error": str(e),
                    "documents": []
                }

        # Check if vector store has documents
        doc_count = self._vector_store.count()
        if doc_count == 0:
            self.logger.warning("Vector store is empty - no documents to retrieve")
            return {
                "status": "empty",
                "message": "No documents in vector store",
                "documents": []
            }

        # Perform retrieval
        try:
            results = self._vector_store.search(
                query=query,
                top_k=top_k,
                similarity_threshold=self.similarity_threshold
            )

            if results:
                retrieved_documents = []
                sources = []

                for i, result in enumerate(results):
                    source = result.metadata.get("source", "unknown")
                    chunk_idx = result.metadata.get("chunk_index", "")
                    similarity = result.similarity

                    sources.append(source)
                    retrieved_documents.append({
                        "text": result.text,
                        "source": source,
                        "similarity": float(similarity),
                        "chunk_index": chunk_idx,
                        "metadata": result.metadata
                    })

                execution_time = (time.time() - start_time) * 1000
                self.logger.info(
                    f"RAG tool retrieved {len(results)} documents in {execution_time:.2f}ms"
                )

                return {
                    "status": "success",
                    "documents": retrieved_documents,
                    "retrieved_count": len(results),
                    "sources": list(set(sources)),
                    "avg_similarity": sum(r.similarity for r in results) / len(results),
                    "execution_time_ms": execution_time
                }
            else:
                return {
                    "status": "no_results",
                    "message": f"No documents found above similarity threshold {self.similarity_threshold}",
                    "documents": []
                }

        except Exception as e:
            self.logger.error(f"RAG tool search failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "documents": []
            }

    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Register the RAG-as-tool definition in the pipeline context metadata.
        
        Adds this module's tool definition to context.metadata["tools"] and records registration status and tool name in metadata. Updates the module's last metrics with execution time and registration status.
        
        Parameters:
        	context (PipelineContext): The pipeline context to update.
        
        Returns:
        	PipelineContext: The updated pipeline context containing the registered tool definition and related metadata.
        """
        start_time = time.time()

        self.logger.info("RAG-as-tool registering tool definition")

        # Register the tool definition in context metadata
        if "tools" not in context.metadata:
            context.metadata["tools"] = []

        context.metadata["tools"].append(self.get_tool_definition())
        context.metadata["rag_tool_status"] = "registered"
        context.metadata["rag_tool_name"] = self.tool_name

        execution_time = (time.time() - start_time) * 1000
        self._last_metrics = ModuleMetrics(
            module_name=self.name,
            execution_time_ms=execution_time,
            technique_specific={
                "status": "registered",
                "tool_name": self.tool_name
            }
        )

        return context

    def get_metrics(self) -> ModuleMetrics:
        """
        Provide metrics for the last RAG-as-tool execution.
        
        Returns:
            ModuleMetrics: Metrics recorded from the most recent RAG tool invocation.
        """
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
        Initialize the context pipeline, instantiate all available modules, and apply the provided configuration.
        
        Parameters:
            config (Optional[ContextEngineeringConfig]): Pipeline configuration to use; if None, a default configuration is created (baseline with modules disabled).
        """
        self.config = config or ContextEngineeringConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize all available modules
        self.modules: Dict[str, ContextEngineeringModule] = {
            "naive_rag": NaiveRAGModule(),
            "rag_tool": RAGToolModule(),
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
        """
        Apply the current pipeline configuration to each registered module.
        
        For each module, enable it and pass its module-specific settings (via the config object's __dict__) when the corresponding config flag is true; otherwise disable the module. After applying all settings, logs the list of enabled modules.
        """
        # Naive RAG
        if self.config.naive_rag_enabled:
            self.modules["naive_rag"].enable()
            self.modules["naive_rag"].configure(self.config.naive_rag.__dict__)
        else:
            self.modules["naive_rag"].disable()

        # RAG-as-tool
        if self.config.rag_tool_enabled:
            self.modules["rag_tool"].enable()
            self.modules["rag_tool"].configure(self.config.rag_tool.__dict__)
        else:
            self.modules["rag_tool"].disable()
        
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
        Orchestrates enabled context-engineering modules for the given query and produces an aggregated PipelineContext.
        
        Modules are executed in the fixed order: memory, caching, naive_rag, rag_tool (registered for LLM use), hybrid_search, reranking, compression. Individual module failures are recorded in context.metadata and do not stop pipeline execution.
        
        Parameters:
            query (str): The user query to process.
            conversation_history (Optional[List[Dict[str, str]]]): Optional list of prior turns to inject into the pipeline.
        
        Returns:
            PipelineContext: The final context with accumulated context text and metadata populated by the modules.
        """
        start_time = time.time()
        
        # Initialize context
        context = PipelineContext(
            query=query,
            conversation_history=conversation_history or []
        )
        
        # Execute enabled modules in order
        # Note: rag_tool is registered but doesn't process automatically - it waits for LLM to call it
        module_order = ["memory", "caching", "naive_rag", "rag_tool", "hybrid_search", "reranking", "compression"]
        
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
