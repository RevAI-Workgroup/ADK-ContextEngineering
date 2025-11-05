"""
RAG Search Tool for ADK Agent.

This tool allows the LLM to search the knowledge base when it needs
external information to answer a query.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def search_knowledge_base(query: str, top_k: int = 5) -> str:
    """
    Search the knowledge base for relevant information.

    This tool searches through the vector store to find documents
    relevant to the given query. Use this when you need factual
    information that might be in the knowledge base.

    Args:
        query: The search query describing what information you need
        top_k: Number of documents to retrieve (default: 5)

    Returns:
        String containing the retrieved documents and their sources
    """
    try:
        from src.retrieval.vector_store import get_vector_store

        logger.info(f"RAG tool called with query: {query[:50]}...")

        # Get vector store
        vector_store = get_vector_store()

        # Check if vector store has documents
        doc_count = vector_store.count()
        if doc_count == 0:
            return "The knowledge base is empty. No documents have been uploaded yet."

        # Perform search
        results = vector_store.search(
            query=query,
            top_k=top_k,
            similarity_threshold=0.2  # Use same threshold as naive RAG
        )

        if not results:
            return f"No relevant documents found in the knowledge base for query: '{query}'"

        # Format results for the LLM
        formatted_results = []
        formatted_results.append(f"Found {len(results)} relevant documents:\n")

        for i, result in enumerate(results, 1):
            source = result.metadata.get("source", "unknown")
            similarity = result.similarity

            formatted_results.append(f"\n--- Document {i} ---")
            formatted_results.append(f"Source: {source}")
            formatted_results.append(f"Relevance: {similarity:.2%}")
            formatted_results.append(f"Content:\n{result.text}\n")

        response = "\n".join(formatted_results)
        logger.info(f"RAG tool returned {len(results)} documents")

        return response

    except Exception as e:
        error_msg = f"Error searching knowledge base: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg
