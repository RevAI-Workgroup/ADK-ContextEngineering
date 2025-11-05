"""
Vector Store Management using ChromaDB.

This module provides a wrapper around ChromaDB for managing document embeddings,
similarity search, and vector storage operations.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from pathlib import Path
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
        embedding_function: Optional[Any] = None
    ):
        """
        Initialize vector store.

        Args:
            persist_directory: Directory for ChromaDB persistence
            collection_name: Name of the collection to use
            embedding_function: Optional embedding function (defaults to sentence-transformers)
        """
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name

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

        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Loaded existing collection: {collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
            logger.info(f"Created new collection: {collection_name}")

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
            metadata_filter: Metadata filter for deletion
        """
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

    def get_stats(self) -> Dict[str, Any]:
        """
        Get vector store statistics.

        Returns:
            Dictionary with store statistics
        """
        try:
            count = self.count()

            # Get sample documents to analyze
            sample_docs = self.get_all_documents(limit=100)

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
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "embedding_dimensions": 384
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


def get_vector_store(
    persist_directory: str = "./data/chroma",
    collection_name: str = "documents"
) -> VectorStore:
    """
    Get global vector store instance (singleton pattern).

    Args:
        persist_directory: Directory for ChromaDB persistence
        collection_name: Name of the collection

    Returns:
        Global VectorStore instance
    """
    global _global_vector_store
    if _global_vector_store is None:
        _global_vector_store = VectorStore(
            persist_directory=persist_directory,
            collection_name=collection_name
        )
    return _global_vector_store


def reset_vector_store() -> None:
    """Reset the global vector store (useful for testing)."""
    global _global_vector_store
    _global_vector_store = None
