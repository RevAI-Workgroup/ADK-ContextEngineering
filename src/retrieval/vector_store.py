"""
Vector Store Management using ChromaDB.

This module provides a wrapper around ChromaDB for managing document embeddings,
similarity search, and vector storage operations.
"""

import os
# Disable ChromaDB telemetry before importing chromadb
# This must be set before the chromadb import to prevent telemetry errors
os.environ.setdefault("CHROMA_TELEMETRY_ENABLED", "false")

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from pathlib import Path
import threading
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import uuid

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """
    Result from a vector similarity search.

    Attributes:
        id: Unique identifier of the document chunk
        text: Text content of the chunk
        metadata: Associated metadata (source, page, etc.)
        similarity: Similarity score (0-1, higher is better)
    """
    id: str
    text: str
    metadata: Dict[str, Any]
    similarity: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "metadata": self.metadata,
            "similarity": self.similarity
        }


class VectorStore:
    """
    Vector store wrapper for ChromaDB.

    Manages document embeddings, similarity search, and persistence.
    """

    def __init__(
        self,
        persist_directory: str = "./data/chroma",
        collection_name: str = "documents",
        embedding_function: Optional[Any] = None,
        sample_limit: int = 100,
        embedding_dimensions: Optional[int] = None,
        allow_remote_embedding_detection: bool = False
    ):
        """
        Initialize vector store.

        Args:
            persist_directory: Directory for ChromaDB persistence
            collection_name: Name of the collection to use
            embedding_function: Optional embedding function (defaults to sentence-transformers)
            sample_limit: Default limit for sampling documents in get_stats (default: 100)
            embedding_dimensions: Explicit embedding dimensions (avoids auto-detection)
            allow_remote_embedding_detection: Allow auto-detection for remote embedding functions
                (default: False to prevent expensive API calls)
        """
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.sample_limit = sample_limit
        self._explicit_embedding_dimensions = embedding_dimensions
        self.allow_remote_embedding_detection = allow_remote_embedding_detection

        # Create persist directory if it doesn't exist
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Use provided embedding function or default
        if embedding_function is None:
            # Default: sentence-transformers all-MiniLM-L6-v2 (384 dims)
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
        else:
            self.embedding_function = embedding_function

        # Initialize or get collection
        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Loaded existing collection: {collection_name}")
        except Exception:
            logger.info(f"Collection '{collection_name}' not found, creating new one")
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
            logger.info(f"Created new collection: {collection_name}")

        # Cache embedding metadata (lazy-loaded when first accessed)
        self._embedding_model_name: Optional[str] = None
        self._embedding_dimensions: Optional[int] = None
        self._metadata_lock = threading.Lock()

    @property
    def embedding_model_name(self) -> str:
        """Get the embedding model name (lazy-loaded)."""
        if self._embedding_model_name is None:
            with self._metadata_lock:
                # Double-check pattern: another thread may have initialized while waiting
                if self._embedding_model_name is None:
                    self._embedding_model_name, self._embedding_dimensions = self._extract_embedding_metadata()
        return self._embedding_model_name

    @property
    def embedding_dimensions(self) -> int:
        """Get the embedding dimensions (lazy-loaded)."""
        if self._embedding_dimensions is None:
            with self._metadata_lock:
                # Double-check pattern: another thread may have initialized while waiting
                if self._embedding_dimensions is None:
                    self._embedding_model_name, self._embedding_dimensions = self._extract_embedding_metadata()
        return self._embedding_dimensions

    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents to the vector store.

        Args:
            texts: List of text chunks to add
            metadatas: Optional list of metadata dictionaries
            ids: Optional list of IDs (will generate UUIDs if not provided)

        Returns:
            List of document IDs
        """
        if not texts:
            logger.warning("No texts provided to add_documents")
            return []

        # Validate that ids length matches texts length if ids is provided
        if ids is not None and len(ids) != len(texts):
            raise ValueError(
                f"Length mismatch: ids has {len(ids)} elements but texts has {len(texts)} elements. "
                f"They must have the same length."
            )

        # Validate that metadatas length matches texts length if metadatas is provided
        if metadatas is not None and len(metadatas) != len(texts):
            raise ValueError(
                f"Length mismatch: metadatas has {len(metadatas)} elements but texts has {len(texts)} elements. "
                f"They must have the same length."
            )

        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]

        # Generate default metadata if not provided
        if metadatas is None:
            metadatas = [{} for _ in texts]

        # Ensure metadata values are serializable
        metadatas = [self._sanitize_metadata(m) for m in metadatas]

        try:
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(texts)} documents to vector store")
            return ids
        except Exception as e:
            logger.error(f"Failed to add documents: {e}", exc_info=True)
            raise

    def search(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for similar documents.

        Args:
            query: Query text
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            filter_metadata: Optional metadata filter

        Returns:
            List of SearchResult objects
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=filter_metadata
            )

            # Parse results
            search_results = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    # ChromaDB returns distance, convert to similarity
                    # For cosine distance: similarity = 1 - distance
                    distance = results["distances"][0][i] if results["distances"] else 0
                    similarity = 1 - distance

                    # Filter by threshold
                    if similarity >= similarity_threshold:
                        search_results.append(SearchResult(
                            id=doc_id,
                            text=results["documents"][0][i],
                            metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                            similarity=similarity
                        ))

            logger.info(
                f"Search returned {len(search_results)} results "
                f"(threshold: {similarity_threshold})"
            )
            return search_results

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return []

    def delete_by_ids(self, ids: List[str]) -> None:
        """
        Delete documents by IDs.

        Args:
            ids: List of document IDs to delete
        """
        if not ids:
            return

        try:
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents")
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}", exc_info=True)
            raise

    def delete_by_metadata(self, metadata_filter: Dict[str, Any]) -> None:
        """
        Delete documents by metadata filter.

        Args:
            metadata_filter: Metadata filter for deletion. Must not be empty or falsy.

        Raises:
            ValueError: If metadata_filter is empty or falsy.
        """
        if not metadata_filter:
            raise ValueError("metadata_filter must not be empty or falsy")
        
        try:
            self.collection.delete(where=metadata_filter)
            logger.info(f"Deleted documents matching filter: {metadata_filter}")
        except Exception as e:
            logger.error(f"Failed to delete by metadata: {e}", exc_info=True)
            raise

    def get_by_ids(self, ids: List[str]) -> List[SearchResult]:
        """
        Get documents by IDs.

        Args:
            ids: List of document IDs

        Returns:
            List of SearchResult objects
        """
        if not ids:
            return []

        try:
            results = self.collection.get(ids=ids)

            search_results = []
            for i, doc_id in enumerate(results["ids"]):
                search_results.append(SearchResult(
                    id=doc_id,
                    text=results["documents"][i],
                    metadata=results["metadatas"][i] if results["metadatas"] else {},
                    similarity=1.0  # Perfect match for direct retrieval
                ))

            return search_results

        except Exception as e:
            logger.error(f"Get by IDs failed: {e}", exc_info=True)
            return []

    def get_all_documents(self, limit: Optional[int] = None) -> List[SearchResult]:
        """
        Get all documents in the collection.

        Args:
            limit: Optional limit on number of documents to return

        Returns:
            List of SearchResult objects
        """
        try:
            # Get collection count
            count = self.collection.count()

            if count == 0:
                return []

            # Limit results if specified
            n_results = min(limit, count) if limit else count

            # Get all documents
            results = self.collection.get(
                limit=n_results
            )

            search_results = []
            for i, doc_id in enumerate(results["ids"]):
                search_results.append(SearchResult(
                    id=doc_id,
                    text=results["documents"][i],
                    metadata=results["metadatas"][i] if results["metadatas"] else {},
                    similarity=1.0
                ))

            return search_results

        except Exception as e:
            logger.error(f"Get all documents failed: {e}", exc_info=True)
            return []

    def count(self) -> int:
        """
        Get number of documents in collection.

        Returns:
            Document count
        """
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Count failed: {e}", exc_info=True)
            return 0

    def clear(self) -> None:
        """Clear all documents from the collection."""
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Cleared vector store")
        except Exception as e:
            logger.error(f"Clear failed: {e}", exc_info=True)
            raise

    def _is_local_embedding_function(self) -> bool:
        """
        Check if the embedding function is local (safe to call without API costs).

        Returns:
            True if the embedding function is local, False otherwise
        """
        # Check for explicit is_local attribute
        if hasattr(self.embedding_function, 'is_local'):
            return getattr(self.embedding_function, 'is_local', False)
        
        # SentenceTransformerEmbeddingFunction is always local
        if isinstance(self.embedding_function, embedding_functions.SentenceTransformerEmbeddingFunction):
            return True
        
        # Default: assume remote if not explicitly marked as local
        return False

    def _extract_embedding_metadata(self) -> Tuple[str, int]:
        """
        Extract embedding model name and dimensions from the embedding function.

        Returns:
            Tuple of (model_name, dimensions)
        """
        model_name = "unknown"
        dimensions = 0

        # First, check for explicitly provided dimensions
        if self._explicit_embedding_dimensions is not None:
            dimensions = self._explicit_embedding_dimensions
            logger.info(f"Using explicitly provided embedding dimensions: {dimensions}")

        try:
            # Check if it's a SentenceTransformerEmbeddingFunction
            if isinstance(self.embedding_function, embedding_functions.SentenceTransformerEmbeddingFunction):
                # Try various ways to get the model name
                # ChromaDB may store it as model_name, _model_name, or in the model itself
                if hasattr(self.embedding_function, 'model_name'):
                    model_name = self.embedding_function.model_name
                elif hasattr(self.embedding_function, '_model_name'):
                    model_name = self.embedding_function._model_name
                
                # Try to access the underlying SentenceTransformer model
                if hasattr(self.embedding_function, 'model'):
                    model = self.embedding_function.model
                    # Get dimensions from the model if available (only if not explicitly provided)
                    if dimensions == 0 and hasattr(model, 'get_sentence_embedding_dimension'):
                        dimensions = model.get_sentence_embedding_dimension()
                    # Try to get model name from the model
                    if model_name == "unknown" and hasattr(model, 'model_name'):
                        model_name = model.model_name
                    elif model_name == "unknown" and hasattr(model, '_model_name'):
                        model_name = model._model_name
                    elif model_name == "unknown" and hasattr(model, 'get_sentence_embedding_dimension'):
                        # Last resort: try to infer from model path/name
                        if hasattr(model, '__class__'):
                            model_name = f"sentence-transformers/{model.__class__.__name__}"

            # If dimensions not yet determined, attempt auto-detection only if safe
            if dimensions == 0:
                is_local = self._is_local_embedding_function()
                can_auto_detect = is_local or self.allow_remote_embedding_detection
                
                if can_auto_detect:
                    try:
                        test_embedding = self.embedding_function(["test"])
                        if test_embedding and len(test_embedding) > 0:
                            dimensions = len(test_embedding[0])
                            logger.info(f"Auto-detected embedding dimensions: {dimensions}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to auto-detect embedding dimensions: {e}. "
                            f"Please provide embedding_dimensions explicitly."
                        )
                else:
                    logger.warning(
                        f"Embedding dimensions not provided and auto-detection is disabled "
                        f"(embedding function appears to be remote). "
                        f"Please provide embedding_dimensions parameter or set "
                        f"allow_remote_embedding_detection=True to enable auto-detection. "
                        f"Current dimensions: {dimensions}"
                    )

            # If model_name is still unknown, try to infer from the function
            if model_name == "unknown":
                # Check for common attributes
                if hasattr(self.embedding_function, '__name__'):
                    model_name = self.embedding_function.__name__
                elif hasattr(self.embedding_function, '__class__'):
                    class_name = self.embedding_function.__class__.__name__
                    if class_name == "SentenceTransformerEmbeddingFunction":
                        # Default fallback for SentenceTransformer
                        model_name = "sentence-transformers/all-MiniLM-L6-v2"
                    else:
                        model_name = f"custom_{class_name.lower()}"
                else:
                    model_name = "custom_embedding_function"

            logger.info(
                f"Embedding metadata: model={model_name}, dimensions={dimensions}"
            )

        except Exception as e:
            logger.warning(
                f"Failed to extract embedding metadata: {e}. "
                f"Using defaults: model=unknown, dimensions={dimensions}"
            )
            # Only attempt fallback auto-detection if explicitly allowed
            if dimensions == 0 and self.allow_remote_embedding_detection:
                try:
                    test_embedding = self.embedding_function(["test"])
                    if test_embedding and len(test_embedding) > 0:
                        dimensions = len(test_embedding[0])
                        model_name = "custom_embedding_function"
                        logger.info(f"Fallback auto-detection succeeded: dimensions={dimensions}")
                except Exception as fallback_error:
                    logger.warning(
                        f"Fallback auto-detection also failed: {fallback_error}. "
                        f"Please provide embedding_dimensions explicitly."
                    )

        return model_name, dimensions

    def get_stats(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Get vector store statistics.

        Args:
            limit: Optional limit for sampling documents (defaults to self.sample_limit)

        Returns:
            Dictionary with store statistics
        """
        try:
            count = self.count()

            # Use provided limit or instance default
            sample_limit = limit if limit is not None else self.sample_limit

            # Get sample documents to analyze
            sample_docs = self.get_all_documents(limit=sample_limit)

            # Extract unique sources
            sources = set()
            for doc in sample_docs:
                if "source" in doc.metadata:
                    sources.add(doc.metadata["source"])

            # Calculate storage size (approximate)
            storage_size_mb = self._estimate_storage_size()

            return {
                "total_documents": count,
                "unique_sources": len(sources),
                "sources": list(sources),
                "collection_name": self.collection_name,
                "persist_directory": str(self.persist_directory),
                "storage_size_mb": storage_size_mb,
                "embedding_model": self.embedding_model_name,
                "embedding_dimensions": self.embedding_dimensions,
                "sample_limit_used": sample_limit
            }
        except Exception as e:
            logger.error(f"Get stats failed: {e}", exc_info=True)
            return {
                "total_documents": 0,
                "error": str(e)
            }

    def _estimate_storage_size(self) -> float:
        """
        Estimate storage size in MB.

        Returns:
            Estimated size in megabytes
        """
        try:
            total_size = 0
            for file_path in self.persist_directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size / (1024 * 1024)  # Convert to MB
        except Exception as e:
            logger.error(f"Storage size estimation failed: {e}")
            return 0.0

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize metadata to ensure ChromaDB compatibility.

        ChromaDB requires metadata values to be str, int, float, or bool.

        Args:
            metadata: Raw metadata dictionary

        Returns:
            Sanitized metadata dictionary
        """
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, (list, tuple)):
                # Convert lists to comma-separated strings
                sanitized[key] = ",".join(str(v) for v in value)
            else:
                # Convert other types to string
                sanitized[key] = str(value)
        return sanitized


# Global vector store instance (singleton pattern)
_global_vector_store: Optional[VectorStore] = None
_global_vector_store_params: Optional[Dict[str, str]] = None


def get_vector_store(
    persist_directory: str = "./data/chroma",
    collection_name: str = "documents",
    embedding_function: Optional[Any] = None,
    embedding_dimensions: Optional[int] = None,
    allow_remote_embedding_detection: bool = False
) -> VectorStore:
    """
    Get global vector store instance (singleton pattern).

    Args:
        persist_directory: Directory for ChromaDB persistence
        collection_name: Name of the collection
        embedding_function: Optional embedding function
        embedding_dimensions: Explicit embedding dimensions (avoids auto-detection)
        allow_remote_embedding_detection: Allow auto-detection for remote embedding functions

    Returns:
        Global VectorStore instance

    Raises:
        ValueError: If called with different parameters than the existing instance
    """
    global _global_vector_store, _global_vector_store_params

    # Normalize paths to ensure consistent comparison
    persist_directory_normalized = str(Path(persist_directory).resolve())

    # Parameters for this call
    requested_params = {
        "persist_directory": persist_directory_normalized,
        "collection_name": collection_name
    }

    # If no instance exists, create one
    if _global_vector_store is None:
        _global_vector_store = VectorStore(
            persist_directory=persist_directory,
            collection_name=collection_name,
            embedding_function=embedding_function,
            embedding_dimensions=embedding_dimensions,
            allow_remote_embedding_detection=allow_remote_embedding_detection
        )
        _global_vector_store_params = requested_params
        logger.info(
            f"Created global vector store instance: "
            f"persist_directory={persist_directory_normalized}, "
            f"collection_name={collection_name}"
        )
        return _global_vector_store

    # Validate that requested parameters match existing instance parameters
    if _global_vector_store_params is None:
        # This shouldn't happen, but handle gracefully
        logger.warning(
            "Global vector store exists but parameters are not tracked. "
            "Recreating instance with new parameters."
        )
        _global_vector_store = VectorStore(
            persist_directory=persist_directory,
            collection_name=collection_name,
            embedding_function=embedding_function,
            embedding_dimensions=embedding_dimensions,
            allow_remote_embedding_detection=allow_remote_embedding_detection
        )
        _global_vector_store_params = requested_params
        return _global_vector_store

    # Check for parameter mismatches
    existing_params = _global_vector_store_params
    mismatches = []

    if existing_params["persist_directory"] != requested_params["persist_directory"]:
        mismatches.append(
            f"persist_directory: existing='{existing_params['persist_directory']}', "
            f"requested='{requested_params['persist_directory']}'"
        )

    if existing_params["collection_name"] != requested_params["collection_name"]:
        mismatches.append(
            f"collection_name: existing='{existing_params['collection_name']}', "
            f"requested='{requested_params['collection_name']}'"
        )

    if mismatches:
        error_msg = (
            f"Vector store singleton was already initialized with different parameters. "
            f"Parameter mismatches: {', '.join(mismatches)}. "
            f"To use different parameters, call reset_vector_store() first, or use "
            f"VectorStore() directly to create a new instance."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Parameters match, return existing instance
    return _global_vector_store


def reset_vector_store() -> None:
    """Reset the global vector store (useful for testing)."""
    global _global_vector_store, _global_vector_store_params
    _global_vector_store = None
    _global_vector_store_params = None
