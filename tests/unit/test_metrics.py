"""
Unit tests for metrics calculation.
"""

import pytest
from src.evaluation.metrics import MetricsCollector, MetricResult, EvaluationResult


class TestMetricsCollector:
    """Test suite for MetricsCollector."""
    
    @pytest.fixture
    def collector(self):
        """Create a MetricsCollector instance."""
        return MetricsCollector()
    
    def test_count_tokens(self, collector):
        """Test token counting."""
        text = "This is a test string for token counting."
        tokens = collector.count_tokens(text)
        assert isinstance(tokens, int)
        assert tokens > 0
    
    def test_rouge_scores(self, collector):
        """Test ROUGE score calculation."""
        prediction = "The cat sat on the mat."
        reference = "The cat is sitting on the mat."
        
        scores = collector.calculate_rouge_scores(prediction, reference)
        
        assert 'rouge1_f1' in scores
        assert 'rouge2_f1' in scores
        assert 'rougeL_f1' in scores
        
        # Scores should be between 0 and 1
        for score in scores.values():
            assert 0 <= score.value <= 1
            assert isinstance(score, MetricResult)
    
    def test_hallucination_detection_no_context(self, collector):
        """Test hallucination detection without context."""
        # Response with confident phrase and no context
        response = "I'm absolutely certain that the answer is 42."
        
        result = collector.detect_hallucination_heuristic(response, context="")
        
        assert isinstance(result, MetricResult)
        assert result.metric_name == 'hallucination_rate'
        assert 0 <= result.value <= 1
        # Should detect hallucination indicators
        assert result.value > 0
    
    def test_hallucination_detection_with_context(self, collector):
        """Test hallucination detection with sufficient context."""
        response = "I'm absolutely certain that the answer is 42."
        context = "According to the Deep Thought computer in The Hitchhiker's Guide, " \
                 "the answer to life, universe, and everything is 42."
        
        result = collector.detect_hallucination_heuristic(response, context=context)
        
        assert isinstance(result, MetricResult)
        # Should have lower hallucination score with context
        assert result.value < 1.0
    
    def test_hallucination_confident_without_context(self, collector):
        """Test detection of confident phrases without context."""
        response = "There's no doubt that this is correct."
        
        result = collector.detect_hallucination_heuristic(response, context="")
        
        # Should trigger check 1
        assert result.value > 0
        assert result.metadata['indicators_triggered'] >= 1
    
    def test_hallucination_numbers_without_context(self, collector):
        """Test detection of specific numbers without context."""
        response = "The price is $99.99 and the year is 2024."
        
        result = collector.detect_hallucination_heuristic(response, context="")
        
        # Should trigger check 2
        assert result.value > 0
        assert result.metadata['indicators_triggered'] >= 1
    
    def test_hallucination_long_unhedged_without_context(self, collector):
        """Test detection of long response without hedging and no context."""
        response = "This is a very long response that goes on and on without any " \
                  "hedging language whatsoever. It makes many claims and provides " \
                  "lots of information with complete certainty and absolute confidence."
        
        result = collector.detect_hallucination_heuristic(response, context="")
        
        # Should trigger check 3 (long response without hedging and no context)
        assert result.value > 0, f"Expected hallucination detected but got score={result.value}, metadata={result.metadata}"
        assert result.metadata['indicators_triggered'] >= 1
    
    def test_hallucination_scoring_consistency(self, collector):
        """Test that hallucination scoring is consistent and predictable."""
        # No indicators
        result1 = collector.detect_hallucination_heuristic(
            "I think this might be the answer.",
            context=""
        )
        
        # All indicators
        result2 = collector.detect_hallucination_heuristic(
            "I'm absolutely certain that the answer is $100 and 2024. " * 10,
            context=""
        )
        
        # Score should be 0 for no indicators
        assert result1.value == 0.0
        
        # Score should be 1.0 for all indicators
        assert result2.value == 1.0
        
        # Check metadata consistency
        assert result1.metadata['total_checks'] == result2.metadata['total_checks']
    
    def test_hallucination_context_length_threshold(self, collector):
        """Test that context length threshold is applied consistently."""
        response = "I'm absolutely certain."
        
        # Short context (< 50 chars)
        result_short = collector.detect_hallucination_heuristic(
            response, 
            context="Short"
        )
        
        # Long context (>= 50 chars)
        result_long = collector.detect_hallucination_heuristic(
            response,
            context="This is a sufficiently long context that exceeds fifty characters."
        )
        
        # Short context should have higher hallucination score
        assert result_short.value > result_long.value
        assert not result_short.metadata['has_sufficient_context']
        assert result_long.metadata['has_sufficient_context']
    
    def test_relevance_score(self, collector):
        """Test relevance score calculation."""
        query = "What is Python programming?"
        response = "Python is a high-level programming language."
        
        result = collector.calculate_relevance_score(query, response)
        
        assert isinstance(result, MetricResult)
        assert result.metric_name == 'relevance_score'
        assert 0 <= result.value <= 1
    
    def test_evaluate_complete(self, collector):
        """Test complete evaluation of query-response pair."""
        query = "What is 2+2?"
        response = "The answer is 4."
        ground_truth = "2+2 equals 4."
        
        result = collector.evaluate(
            query=query,
            response=response,
            ground_truth=ground_truth,
            latency_ms=100.0
        )
        
        assert isinstance(result, EvaluationResult)
        assert result.query == query
        assert result.response == response
        assert result.latency_ms == 100.0
        assert 'rouge1_f1' in result.metrics
        assert 'relevance_score' in result.metrics
        assert 'hallucination_rate' in result.metrics
    
    def test_aggregate_metrics(self, collector):
        """Test aggregate metrics calculation."""
        # Evaluate multiple queries
        for i in range(3):
            collector.evaluate(
                query=f"Query {i}",
                response=f"Response {i}",
                ground_truth=f"Truth {i}",
                latency_ms=float(i * 100)
            )
        
        aggregates = collector.get_aggregate_metrics()
        
        assert 'latency_ms_mean' in aggregates
        assert 'tokens_per_query_mean' in aggregates
        assert len(aggregates) > 0
    
    def test_case_insensitive_phrase_matching(self, collector):
        """Test that phrase matching is case-insensitive."""
        # Confident phrase in different cases
        responses = [
            "I'M ABSOLUTELY CERTAIN",
            "i'm absolutely certain",
            "I'm Absolutely Certain"
        ]
        
        for response in responses:
            result = collector.detect_hallucination_heuristic(response, context="")
            assert result.value > 0, f"Failed for: {response}"

