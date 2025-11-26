"""
Unit tests for RAG search tool threshold functionality.

Tests the search_knowledge_base function with various scenarios including
empty knowledge base, no results, and successful retrieval with different
threshold values.
"""

import pytest
import re
from unittest.mock import Mock, patch
from src.core.tools.rag_search import search_knowledge_base
from src.retrieval.vector_store import SearchResult


class TestRAGSearchThreshold:
    """Test suite for RAG search tool threshold behavior."""

    @pytest.fixture
    def mock_vector_store(self):
        """Create a mock vector store for testing."""
        mock_store = Mock()
        return mock_store

    @pytest.fixture
    def sample_search_results(self):
        """Create sample search results for testing."""
        return [
            SearchResult(
                id="doc1",
                text="Riri is a character in the story.",
                metadata={"source": "RiriFifiLoulou.md"},
                similarity=0.85
            ),
            SearchResult(
                id="doc2",
                text="Riri appears alongside Fifi and Loulou.",
                metadata={"source": "RiriFifiLoulou.md"},
                similarity=0.72
            ),
            SearchResult(
                id="doc3",
                text="Riri's adventures are documented here.",
                metadata={"source": "RiriFifiLoulou.md"},
                similarity=0.65
            ),
        ]

    @patch('src.retrieval.vector_store.get_vector_store')
    def test_search_with_empty_knowledge_base(self, mock_get_vector_store, mock_vector_store):
        """Test search when knowledge base is empty."""
        mock_vector_store.count.return_value = 0
        mock_get_vector_store.return_value = mock_vector_store

        result = search_knowledge_base("Riri", top_k=5)

        assert "knowledge base is empty" in result.lower()
        assert "no documents have been uploaded yet" in result.lower()
        mock_vector_store.count.assert_called_once()
        mock_vector_store.search.assert_not_called()

    @patch('src.retrieval.vector_store.get_vector_store')
    def test_search_with_no_results(self, mock_get_vector_store, mock_vector_store):
        """Test search when no relevant documents are found."""
        mock_vector_store.count.return_value = 10
        mock_vector_store.search.return_value = []
        mock_get_vector_store.return_value = mock_vector_store

        result = search_knowledge_base("nonexistent query", top_k=5)

        assert "No relevant documents found" in result
        assert "nonexistent query" in result
        mock_vector_store.count.assert_called_once()
        mock_vector_store.search.assert_called_once_with(
            query="nonexistent query",
            top_k=5,
            similarity_threshold=0.2
        )

    @patch('src.retrieval.vector_store.get_vector_store')
    def test_search_successful_retrieval(self, mock_get_vector_store, mock_vector_store, sample_search_results):
        """Test successful document retrieval."""
        mock_vector_store.count.return_value = 10
        mock_vector_store.search.return_value = sample_search_results
        mock_get_vector_store.return_value = mock_vector_store

        result = search_knowledge_base("Riri", top_k=5)

        assert "Found 3 relevant documents" in result
        assert "--- Document 1 ---" in result
        assert "--- Document 2 ---" in result
        assert "--- Document 3 ---" in result
        assert "RiriFifiLoulou.md" in result
        assert "Riri is a character" in result
        assert "85.00%" in result or "85%" in result  # Check relevance percentage
        mock_vector_store.search.assert_called_once_with(
            query="Riri",
            top_k=5,
            similarity_threshold=0.2
        )

    @pytest.mark.parametrize("top_k,expected_doc_count", [
        (1, 1),
        (3, 3),
        (5, 3),  # Only 3 results available
        (10, 3),  # Only 3 results available
    ])
    @patch('src.retrieval.vector_store.get_vector_store')
    def test_search_with_different_top_k(
        self,
        mock_get_vector_store,
        mock_vector_store,
        sample_search_results,
        top_k,
        expected_doc_count
    ):
        """Test search with different top_k values."""
        # Limit results based on top_k
        limited_results = sample_search_results[:expected_doc_count]
        mock_vector_store.count.return_value = 10
        mock_vector_store.search.return_value = limited_results
        mock_get_vector_store.return_value = mock_vector_store

        result = search_knowledge_base("Riri", top_k=top_k)

        assert f"Found {expected_doc_count} relevant documents" in result
        # Count document markers
        doc_count = len(re.findall(r"--- Document \d+ ---", result))
        assert doc_count == expected_doc_count
        mock_vector_store.search.assert_called_once_with(
            query="Riri",
            top_k=top_k,
            similarity_threshold=0.2
        )

    @patch('src.retrieval.vector_store.get_vector_store')
    def test_search_error_handling(self, mock_get_vector_store, mock_vector_store):
        """Test error handling when vector store operations fail."""
        mock_vector_store.count.side_effect = Exception("Database connection error")
        mock_get_vector_store.return_value = mock_vector_store

        result = search_knowledge_base("Riri", top_k=5)

        assert "Error searching knowledge base" in result
        assert "Database connection error" in result

    @patch('src.retrieval.vector_store.get_vector_store')
    def test_search_result_formatting(self, mock_get_vector_store, mock_vector_store, sample_search_results):
        """Test that search results are properly formatted."""
        mock_vector_store.count.return_value = 10
        mock_vector_store.search.return_value = sample_search_results
        mock_get_vector_store.return_value = mock_vector_store

        result = search_knowledge_base("Riri", top_k=5)

        # Check formatting elements
        assert "Found" in result
        assert "relevant documents" in result
        # Each document should have source, relevance, and content
        assert "Source:" in result
        assert "Relevance:" in result
        assert "Content:" in result
        # Check that all document texts are included
        for search_result in sample_search_results:
            assert search_result.text in result
            assert search_result.metadata["source"] in result
