"""
Vector Store Management using ChromaDB.

This module provides a wrapper around ChromaDB for managing document embeddings,
similarity search, and vector storage operations.
"""

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
        """
        Return a dictionary representation of the SearchResult.
        
        The dictionary includes the keys:
        - `id`: the result identifier,
        - `text`: the stored text content,
        - `metadata`: the associated metadata mapping,
        - `similarity`: the similarity score.
        
        Returns:
            dict: A mapping with keys `id`, `text`, `metadata`, and `similarity`.
        """
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
        Create and configure a persistent ChromaDB-backed vector store.
        
        Parameters:
            persist_directory (str): Filesystem path used for ChromaDB persistence.
            collection_name (str): Name of the ChromaDB collection to open or create.
            embedding_function (Optional[Any]): Embedding function to use for vectors. If omitted, defaults to the sentence-transformers model `all-MiniLM-L6-v2`.
            sample_limit (int): Default maximum number of documents to sample when computing stats.
            embedding_dimensions (Optional[int]): Explicit embedding dimensionality to use instead of auto-detecting it.
            allow_remote_embedding_detection (bool): If True, permit running remote embedding functions once to infer dimensionality; set to False to avoid potential API calls or costs.
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
        """
        Retrieve the embedding model name used by this VectorStore.
        
        Returns:
            embedding_model_name (str): The name of the embedding model.
        """
        if self._embedding_model_name is None:
            with self._metadata_lock:
                # Double-check pattern: another thread may have initialized while waiting
                if self._embedding_model_name is None:
                    self._embedding_model_name, self._embedding_dimensions = self._extract_embedding_metadata()
        return self._embedding_model_name

    @property
    def embedding_dimensions(self) -> int:
        """
        Retrieve the number of dimensions used by the embedding model.
        
        Returns:
            embedding_dimensions (int): The dimensionality of the embedding vectors.
        """
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
        Finds documents in the collection most similar to the provided query.
        
        Parameters:
            query (str): Query text to search for.
            top_k (int): Maximum number of results to consider.
            similarity_threshold (float): Minimum similarity score between 0 and 1; only results with similarity >= this threshold are returned.
            filter_metadata (Optional[Dict[str, Any]]): Optional metadata filter expressed as a dictionary to restrict matching documents.
        
        Returns:
            List[SearchResult]: Matching SearchResult objects ordered by relevance; each contains `id`, `text`, `metadata`, and `similarity` (0–1).
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
        Delete documents from the collection by their IDs.
        
        If `ids` is empty this method returns without performing any action.
        
        Parameters:
            ids (List[str]): Document IDs to remove from the collection.
        
        Raises:
            Exception: Propagates any exception raised by the underlying collection delete operation.
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
        Remove documents from the collection that match the provided metadata filter.
        
        Parameters:
            metadata_filter (Dict[str, Any]): A non-empty mapping of metadata field names to values used as a filter; documents with metadata matching these conditions will be deleted.
        
        Raises:
            ValueError: If `metadata_filter` is empty or falsy.
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
        Retrieve documents that match the given IDs.
        
        Parameters:
            ids (List[str]): Document IDs to retrieve.
        
        Returns:
            List[SearchResult]: A list of SearchResult instances for each found ID; each result has a similarity of 1.0 to indicate an exact match. If no IDs are provided or retrieval fails, returns an empty list.
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
        Return documents from the collection up to an optional limit.
        
        Parameters:
            limit (Optional[int]): Maximum number of documents to return. If None, return all documents.
        
        Returns:
            List[SearchResult]: Retrieved documents as SearchResult objects. Each result's `similarity` is set to `1.0`.
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
        Get the number of documents in the collection.
        
        Returns:
            int: Number of documents in the collection; returns 0 if an error occurs while retrieving the count.
        """
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Count failed: {e}", exc_info=True)
            return 0

    def clear(self) -> None:
        """
        Remove all documents by deleting and recreating the collection.
        
        Deletes the ChromaDB collection for this instance and recreates it using the same
        embedding function and HNSW metadata setting (`"hnsw:space": "cosine"`). Any
        exceptions raised by the underlying client are propagated.
        """
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
        Determine whether the configured embedding function appears to be local.
        
        Detection order:
        - If the embedding function has an `is_local` attribute, its boolean value is used.
        - Otherwise, instances of `SentenceTransformerEmbeddingFunction` are treated as local.
        - If neither condition applies, the function is considered remote.
        
        Returns:
            True if the embedding function appears local, False otherwise.
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
        Determine the embedding model name and vector dimensionality for the current embedding function.
        
        This inspects the configured embedding function and returns a best-effort pair of (model_name, dimensions). It prefers an explicitly provided dimensions value, then attempts to extract metadata from a SentenceTransformerEmbeddingFunction (attributes on the wrapper or its underlying model). If dimensions remain unknown and auto-detection is permitted (local embedding function or allow_remote_embedding_detection=True), it may call the embedding function on a short test input to infer the vector length. If detection fails, dimensions will be 0 and model_name may be "unknown" or a best-effort identifier derived from the function/class.
        
        Returns:
            Tuple[str, int]: (model_name, dimensions) where `model_name` is a human-readable identifier for the embedding model and `dimensions` is the embedding vector length (0 if unknown).
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
        Return statistics and metadata about the vector store.
        
        Parameters:
            limit (Optional[int]): Maximum number of documents to sample for source statistics; if omitted uses the instance's sample_limit.
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - total_documents (int): Total number of documents in the collection.
                - unique_sources (int): Count of distinct `source` values found in the sampled documents.
                - sources (List[str]): List of distinct `source` values discovered.
                - collection_name (str): Name of the Chroma collection.
                - persist_directory (str): Filesystem path used for persistence.
                - storage_size_mb (float): Estimated storage size of the persist directory in megabytes.
                - embedding_model (str): Name or identifier of the embedding model.
                - embedding_dimensions (int): Dimensionality of the embedding vectors.
                - sample_limit_used (int): The sample limit actually used for collecting statistics.
            On failure returns a dictionary with `total_documents` set to 0 and an `error` string describing the failure.
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
        Estimate the total size of the persistence directory in megabytes.
        
        Returns:
            storage_size_mb (float): Total size of files under the configured persist directory in megabytes; returns 0.0 if estimation fails.
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
    Return the global VectorStore singleton, creating and tracking a new instance if none exists.
    
    Parameters:
        embedding_dimensions (Optional[int]): Explicit embedding vector dimensionality; when provided, auto-detection is skipped.
        allow_remote_embedding_detection (bool): If True, allow attempting embedding-dimension detection for remote/unknown embedding functions.
    
    Returns:
        VectorStore: The global VectorStore instance managed as a singleton.
    
    Raises:
        ValueError: If a global instance already exists and the requested `persist_directory` or `collection_name` differ from the tracked values. Call `reset_vector_store()` or instantiate `VectorStore` directly to use different parameters.
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
    """
    Clear the module's cached global VectorStore instance and its stored parameters.
    
    This resets the internal singleton state so subsequent calls to get_vector_store()
    will create a new VectorStore.
    """
    global _global_vector_store, _global_vector_store_params
    _global_vector_store = None
    _global_vector_store_params = None