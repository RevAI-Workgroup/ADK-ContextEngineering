"""
Embeddings Management Service.

This module provides embedding generation using sentence-transformers
for document and query vectorization.
"""

from typing import List, Optional
import logging
from sentence_transformers import SentenceTransformer
import numpy as np
from functools import lru_cache

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
        Initialize embedding service.

        Args:
            model_name: Name of the sentence-transformer model
            cache_size: Size of the embedding cache
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
        self._embedding_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return [0.0] * self.embedding_dim

        # Check cache
        if text in self._embedding_cache:
            self._cache_hits += 1
            return self._embedding_cache[text]

        # Generate embedding
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            embedding_list = embedding.tolist()

            # Update cache (with LRU eviction)
            self._cache_misses += 1
            if len(self._embedding_cache) >= self.cache_size:
                # Remove oldest entry (simple FIFO for now)
                self._embedding_cache.pop(next(iter(self._embedding_cache)))

            self._embedding_cache[text] = embedding_list

            return embedding_list

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}", exc_info=True)
            return [0.0] * self.embedding_dim

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for encoding

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Filter out cached embeddings
        uncached_texts = []
        uncached_indices = []
        results = [None] * len(texts)

        for i, text in enumerate(texts):
            if text in self._embedding_cache:
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

                    # Update cache
                    if len(self._embedding_cache) < self.cache_size:
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
        Get cache statistics.

        Returns:
            Dictionary with cache stats
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

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._embedding_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("Embedding cache cleared")

    def compute_similarity(
        self,
        text1: str,
        text2: str,
        metric: str = "cosine"
    ) -> float:
        """
        Compute similarity between two texts.

        Args:
            text1: First text
            text2: Second text
            metric: Similarity metric ("cosine" or "dot")

        Returns:
            Similarity score (0-1 for cosine, unbounded for dot)
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
        Get information about the embedding model.

        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.embedding_dim,
            "max_sequence_length": self.model.max_seq_length,
            "cache_stats": self.get_cache_stats()
        }


# Global embedding service instance (singleton pattern)
_global_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
) -> EmbeddingService:
    """
    Get global embedding service instance (singleton pattern).

    Args:
        model_name: Name of the embedding model

    Returns:
        Global EmbeddingService instance
    """
    global _global_embedding_service
    if _global_embedding_service is None:
        _global_embedding_service = EmbeddingService(model_name=model_name)
    return _global_embedding_service


def reset_embedding_service() -> None:
    """Reset the global embedding service (useful for testing)."""
    global _global_embedding_service
    _global_embedding_service = None
