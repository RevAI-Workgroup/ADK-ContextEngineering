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
    Search the knowledge base for relevant documents and information.

    IMPORTANT: Use this tool proactively whenever:
    - A user asks ANY question that isn't basic small talk
    - You need to provide accurate, factual information
    - The query could benefit from documentation, examples, or data
    - You're uncertain about specific details or facts
    - The user asks "what", "how", "why", "explain", or "tell me about" questions

    DO NOT assume the knowledge base is empty - always check it first.
    DO NOT say "I don't have information" without trying this tool first.
    Even if the query seems general, there might be relevant documents.

    Examples of when to use:
    - "What is X?" → Search for X
    - "How does Y work?" → Search for Y
    - "Tell me about Z" → Search for Z
    - "Explain A to me" → Search for A
    - Any technical question → Search for related terms

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
            similarity_threshold=0.2  # Lenient threshold to retrieve more potentially relevant results
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
