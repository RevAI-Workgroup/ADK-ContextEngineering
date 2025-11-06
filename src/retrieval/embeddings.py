"""
Embeddings Management Service.

This module provides embedding generation using sentence-transformers
for document and query vectorization.
"""

from typing import List, Optional, Dict
import logging
import threading
from collections import OrderedDict
from sentence_transformers import SentenceTransformer
import numpy as np
from src.core.config import get_config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings using sentence-transformers.

    Uses all-MiniLM-L6-v2 by default (384 dimensions, ~80MB).
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        cache_size: int = 1000
    ):
        """
        Create an EmbeddingService by loading the specified SentenceTransformer model and initializing an LRU embedding cache.
        
        Parameters:
            model_name (str): Sentence-transformers model identifier to load (default "sentence-transformers/all-MiniLM-L6-v2").
            cache_size (int): Maximum number of embeddings to retain in the LRU cache.
        
        Raises:
            Exception: If the SentenceTransformer model fails to load.
        """
        self.model_name = model_name
        self.cache_size = cache_size

        logger.info(f"Loading embedding model: {model_name}")
        try:
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(
                f"Embedding model loaded successfully. "
                f"Dimensions: {self.embedding_dim}"
            )
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}", exc_info=True)
            raise

        # Cache for embeddings (LRU cache)
        self._embedding_cache = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0

    def embed_text(self, text: str) -> List[float]:
        """
        Generates an embedding vector for the given text.
        
        Returns a zero vector when the input is empty or whitespace. Uses the service's LRU cache and updates cache hit/miss counters; on a successful cache hit returns the cached vector. On encoding failure returns a zero vector.
        
        Args:
            text (str): The input text to embed.
        
        Returns:
            List[float]: The embedding vector (length equals the service's embedding dimension); `0.0` values indicate an empty input or an encoding failure.
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return [0.0] * self.embedding_dim

        # Check cache
        if text in self._embedding_cache:
            # Move to end (most recently used)
            self._embedding_cache.move_to_end(text)
            self._cache_hits += 1
            return self._embedding_cache[text]

        # Generate embedding
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            embedding_list = embedding.tolist()

            # Update cache (with LRU eviction)
            self._cache_misses += 1
            if len(self._embedding_cache) >= self.cache_size:
                # Remove least-recently-used entry (first item)
                self._embedding_cache.popitem(last=False)

            # Insert new entry at end (most recently used)
            self._embedding_cache[text] = embedding_list

            return embedding_list

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}", exc_info=True)
            return [0.0] * self.embedding_dim

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for a list of texts, reusing cached embeddings and encoding uncached texts in batches.
        
        Cached embeddings are returned in-place and their LRU position is updated; uncached texts are encoded in batches of size `batch_size` and added to the cache. If batch encoding fails, embeddings for the failed items are replaced with zero vectors of the service's embedding dimension.
        
        Parameters:
            texts (List[str]): Input texts to embed; order is preserved in the result.
            batch_size (int): Maximum number of texts to encode per model call.
        
        Returns:
            List[List[float]]: Embedding vectors aligned with the input `texts`; each entry is a list of floats.
        """
        if not texts:
            return []

        # Filter out cached embeddings
        uncached_texts = []
        uncached_indices = []
        results = [None] * len(texts)

        for i, text in enumerate(texts):
            if text in self._embedding_cache:
                # Move to end (most recently used)
                self._embedding_cache.move_to_end(text)
                results[i] = self._embedding_cache[text]
                self._cache_hits += 1
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Generate embeddings for uncached texts
        if uncached_texts:
            try:
                embeddings = self.model.encode(
                    uncached_texts,
                    batch_size=batch_size,
                    convert_to_numpy=True,
                    show_progress_bar=len(uncached_texts) > 100
                )

                # Store in cache and results
                for i, (text, embedding) in enumerate(zip(uncached_texts, embeddings)):
                    embedding_list = embedding.tolist()
                    results[uncached_indices[i]] = embedding_list

                    # Update cache (with LRU eviction)
                    if len(self._embedding_cache) >= self.cache_size:
                        # Remove least-recently-used entry (first item)
                        self._embedding_cache.popitem(last=False)
                    
                    # Insert new entry at end (most recently used)
                    self._embedding_cache[text] = embedding_list

                self._cache_misses += len(uncached_texts)

            except Exception as e:
                logger.error(f"Batch embedding failed: {e}", exc_info=True)
                # Fill with zero vectors for failed embeddings
                zero_vector = [0.0] * self.embedding_dim
                for i in uncached_indices:
                    results[i] = zero_vector

        return results

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.

        Returns:
            Embedding dimension
        """
        return self.embedding_dim

    def get_cache_stats(self) -> dict:
        """
        Return statistics about the embedding cache.
        
        Returns:
            dict: Mapping with the following keys:
                - cache_size (int): Current number of entries in the embedding cache.
                - max_cache_size (int): Configured maximum cache capacity.
                - cache_hits (int): Number of cache hits served.
                - cache_misses (int): Number of cache misses.
                - hit_rate (float): Ratio of hits to total requests (value between 0 and 1).
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (
            self._cache_hits / total_requests if total_requests > 0 else 0
        )

        return {
            "cache_size": len(self._embedding_cache),
            "max_cache_size": self.cache_size,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate
        }

    def compute_similarity(
        self,
        text1: str,
        text2: str,
        metric: str = "cosine"
    ) -> float:
        """
        Compute a similarity score between two texts using either cosine similarity or dot product.
        
        Parameters:
            metric (str): Similarity metric to use; either "cosine" (normalized cosine similarity, range -1 to 1)
                or "dot" (raw dot product, unbounded). Defaults to "cosine".
        
        Returns:
            float: Similarity score (for "cosine", -1.0 to 1.0; for "dot", an unbounded float).
        
        Raises:
            ValueError: If `metric` is not "cosine" or "dot".
        """
        emb1 = np.array(self.embed_text(text1))
        emb2 = np.array(self.embed_text(text2))

        if metric == "cosine":
            # Cosine similarity
            dot_product = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return float(dot_product / (norm1 * norm2))
        elif metric == "dot":
            # Dot product
            return float(np.dot(emb1, emb2))
        else:
            raise ValueError(f"Unknown metric: {metric}")

    def get_model_info(self) -> dict:
        """
        Return metadata and runtime statistics for the embedding model.
        
        Returns:
            info (dict): Dictionary with the following keys:
                - model_name (str): The model identifier used for embeddings.
                - embedding_dimension (int): Size of the output embedding vectors.
                - max_sequence_length (int): Maximum token/sequence length the model accepts.
                - cache_stats (dict): Cache statistics containing `cache_size`, `max_cache_size`, `cache_hits`, `cache_misses`, and `hit_rate`.
        """
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.embedding_dim,
            "max_sequence_length": self.model.max_seq_length,
            "cache_stats": self.get_cache_stats()
        }

    def cleanup(self) -> None:
        """
        Release internal resources used by the embedding service.
        
        Clears the in-memory embedding cache and clears the model reference to allow garbage collection. Exceptions raised during cleanup are caught and logged; this method does not propagate errors.
        """
        try:
            # Clear embedding cache
            self._embedding_cache.clear()
            # Note: SentenceTransformer models don't have explicit cleanup,
            # but clearing references helps with garbage collection
            self.model = None
            logger.info(f"Cleaned up EmbeddingService for model: {self.model_name}")
        except Exception as e:
            logger.warning(f"Error during EmbeddingService cleanup: {e}", exc_info=True)


# Multi-instance singleton pattern: one instance per model name
# This prevents stale references when different models are requested
# Thread-safe with bounded LRU cache for model instances
_embedding_services: OrderedDict[str, "EmbeddingService"] = OrderedDict()
_services_lock = threading.Lock()

# Default max models cache size (can be overridden via config)
_DEFAULT_MAX_MODELS = 5


def get_embedding_service(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
) -> EmbeddingService:
    """
    Return the EmbeddingService singleton for the given model name.
    
    Maintains a per-model singleton registry with an LRU-bounded capacity; when capacity is reached,
    the least-recently-used service is evicted and its cleanup method is invoked.
    
    Parameters:
        model_name (str): Name or identifier of the embedding model to retrieve.
    
    Returns:
        EmbeddingService: The cached or newly created EmbeddingService instance for the specified model.
    """
    global _embedding_services, _services_lock
    
    with _services_lock:
        # Check if instance exists and move to end (most recently used)
        if model_name in _embedding_services:
            _embedding_services.move_to_end(model_name)
            return _embedding_services[model_name]
        
        # Get max models from config or use default
        try:
            config = get_config()
            max_models = config.get("retrieval.embeddings.max_models", _DEFAULT_MAX_MODELS)
        except Exception as e:
            logger.warning(f"Failed to load config, using default max_models: {e}")
            max_models = _DEFAULT_MAX_MODELS
        
        # Evict least-recently-used if at capacity
        if len(_embedding_services) >= max_models:
            # Remove oldest entry (first item in OrderedDict)
            evicted_name, evicted_service = _embedding_services.popitem(last=False)
            logger.info(
                f"Evicting least-recently-used EmbeddingService for model: {evicted_name} "
                f"(cache at capacity: {max_models})"
            )
            try:
                evicted_service.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up evicted service: {e}", exc_info=True)
        
        # Create and cache new instance for this model
        logger.info(f"Creating new EmbeddingService instance for model: {model_name}")
        service = EmbeddingService(model_name=model_name)
        _embedding_services[model_name] = service
        # Move to end to mark as most recently used
        _embedding_services.move_to_end(model_name)
        
        return service


def reset_embedding_service(model_name: Optional[str] = None) -> None:
    """
    Reset cached EmbeddingService instances, optionally for a single model.
    
    Performs cleanup on the affected instance(s) and removes them from the module-level cache in a thread-safe manner.
    
    Parameters:
        model_name (Optional[str]): If provided, reset only the service for this model name; if None, reset all services.
    """
    global _embedding_services, _services_lock
    
    with _services_lock:
        if model_name is None:
            # Reset all instances with cleanup
            for service in _embedding_services.values():
                try:
                    service.cleanup()
                except Exception as e:
                    logger.warning(f"Error cleaning up service during reset: {e}", exc_info=True)
            _embedding_services.clear()
            logger.info("Reset all EmbeddingService instances")
        elif model_name in _embedding_services:
            # Reset specific instance with cleanup
            service = _embedding_services.pop(model_name)
            try:
                service.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up service during reset: {e}", exc_info=True)
            logger.info(f"Reset EmbeddingService instance for model: {model_name}")
        else:
            logger.warning(f"No EmbeddingService instance found for model: {model_name}")


def get_all_embedding_services() -> Dict[str, "EmbeddingService"]:
    """
    Get all active embedding service instances.
    
    Thread-safe operation that returns a snapshot of current instances.
    
    Returns:
        Dictionary mapping model names to their EmbeddingService instances
    """
    global _embedding_services, _services_lock
    
    with _services_lock:
        return dict(_embedding_services)