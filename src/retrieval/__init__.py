"""
Retrieval module for RAG (Retrieval-Augmented Generation).

This module provides document loading, chunking, embedding, and vector search
capabilities for context engineering.
"""

from src.retrieval.vector_store import VectorStore, SearchResult, get_vector_store
from src.retrieval.embeddings import EmbeddingService, get_embedding_service
from src.retrieval.document_loader import (
    Document,
    DocumentLoader,
    TextDocumentLoader,
    MarkdownDocumentLoader,
    load_document,
    load_documents_from_directory
)
from src.retrieval.chunking import (
    Chunk,
    ChunkingStrategy,
    FixedSizeChunking,
    SentenceChunking,
    chunk_document
)

__all__ = [
    # Vector store
    "VectorStore",
    "SearchResult",
    "get_vector_store",

    # Embeddings
    "EmbeddingService",
    "get_embedding_service",

    # Document loading
    "Document",
    "DocumentLoader",
    "TextDocumentLoader",
    "MarkdownDocumentLoader",
    "load_document",
    "load_documents_from_directory",

    # Chunking
    "Chunk",
    "ChunkingStrategy",
    "FixedSizeChunking",
    "SentenceChunking",
    "chunk_document",
]
