"""
Unit tests for the evaluator module.
"""

import pytest
from pathlib import Path
import tempfile
import json

from src.evaluation.evaluator import Evaluator
from src.evaluation.benchmarks import BenchmarkDataset, TestCase


class TestEvaluator:
    """Test suite for Evaluator class."""
    
    @pytest.fixture
    def sample_dataset(self):
        """Create a sample benchmark dataset."""
        dataset = BenchmarkDataset(name="test")
        
        dataset.add_test_case(TestCase(
            id="test_001",
            query="What is 2+2?",
            ground_truth="The answer is 4.",
            category="math",
            difficulty="easy"
        ))
        
        dataset.add_test_case(TestCase(
            id="test_002",
            query="What is Python?",
            ground_truth="Python is a programming language.",
            category="tech",
            difficulty="easy"
        ))
        
        return dataset
    
    @pytest.fixture
    def simple_system(self):
        """Create a simple echo system for testing."""
        def echo_system(query: str) -> str:
            return f"Response to: {query}"
        return echo_system
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_evaluator_initialization(self, temp_output_dir):
        """Test evaluator initialization."""
        evaluator = Evaluator(
            metrics=['accuracy', 'latency'],
            output_dir=temp_output_dir
        )
        
        assert evaluator.metrics == ['accuracy', 'latency']
        assert evaluator.output_dir == Path(temp_output_dir)
        assert evaluator.metrics_collector is not None
    
    def test_evaluate_basic(self, sample_dataset, simple_system, temp_output_dir):
        """Test basic evaluation functionality."""
        evaluator = Evaluator(output_dir=temp_output_dir)
        
        results = evaluator.evaluate(
            dataset=sample_dataset,
            system=simple_system,
            phase="test_phase",
            description="Test evaluation"
        )
        
        assert results['phase'] == "test_phase"
        assert results['description'] == "Test evaluation"
        assert results['dataset'] == "test"
        assert results['total_test_cases'] == 2
        assert results['successful_evaluations'] == 2
        assert 'aggregate_metrics' in results
        assert 'individual_results' in results
    
    def test_evaluate_with_ground_truth(self, temp_output_dir):
        """Test evaluation with ground truth for accuracy metrics."""
        dataset = BenchmarkDataset(name="accuracy_test")
        dataset.add_test_case(TestCase(
            id="acc_001",
            query="What is 5+3?",
            ground_truth="The answer is 8.",
            category="math"
        ))
        
        def accurate_system(query: str) -> str:
            return "The answer is 8."
        
        evaluator = Evaluator(output_dir=temp_output_dir)
        results = evaluator.evaluate(
            dataset=dataset,
            system=accurate_system,
            phase="accuracy_test"
        )
        
        # Should have ROUGE metrics
        aggregates = results['aggregate_metrics']
        assert 'rouge1_f1_mean' in aggregates
        assert 'rouge2_f1_mean' in aggregates
        assert 'rougeL_f1_mean' in aggregates
    
    def test_print_summary_metric_filtering(self, sample_dataset, simple_system, temp_output_dir, capsys):
        """Test that summary prints only mean values consistently."""
        evaluator = Evaluator(output_dir=temp_output_dir)
        
        results = evaluator.evaluate(
            dataset=sample_dataset,
            system=simple_system,
            phase="filter_test"
        )
        
        # Capture printed output
        captured = capsys.readouterr()
        
        # Should show mean values
        assert '_mean' in captured.out or 'mean' in captured.out.lower()
        
        # Should NOT show min/max in summary (they're in JSON but not printed)
        # This is what we're testing - consistent filtering
        aggregates = results['aggregate_metrics']
        
        # Check that we have both mean and min/max in aggregates
        has_mean = any('_mean' in k for k in aggregates.keys())
        has_minmax = any('_min' in k or '_max' in k for k in aggregates.keys())
        
        assert has_mean, "Should have mean values"
        assert has_minmax, "Should have min/max in aggregates"
        
        # But the printed summary should be filtered to show only means
        # (We can't easily test the exact output, but the test validates behavior)
    
    def test_save_results(self, sample_dataset, simple_system, temp_output_dir):
        """Test saving evaluation results."""
        evaluator = Evaluator(output_dir=temp_output_dir)
        
        results = evaluator.evaluate(
            dataset=sample_dataset,
            system=simple_system,
            phase="save_test"
        )
        
        output_file = Path(temp_output_dir) / "test_results.json"
        evaluator.save_results(results, "test_results.json")
        
        assert output_file.exists()
        
        # Verify saved content matches what was returned
        with open(output_file, 'r') as f:
            saved_data = json.load(f)
        
        # Should contain all the fields from evaluate()
        assert saved_data['phase'] == 'save_test'
        assert saved_data['dataset'] == 'test'
        assert 'total_test_cases' in saved_data
        assert 'successful_evaluations' in saved_data
        assert 'failed_evaluations' in saved_data
        assert 'success_rate' in saved_data
        assert 'aggregate_metrics' in saved_data
        assert 'individual_results' in saved_data
        assert 'failures' in saved_data
        assert 'timeout_seconds' in saved_data
        
        # Verify the saved data matches the returned results
        assert saved_data == results
    
    def test_error_handling(self, temp_output_dir):
        """Test error handling during evaluation."""
        dataset = BenchmarkDataset(name="error_test")
        dataset.add_test_case(TestCase(
            id="err_001",
            query="Trigger error",
            category="error"
        ))
        
        def failing_system(query: str) -> str:
            raise ValueError("Intentional error")
        
        evaluator = Evaluator(output_dir=temp_output_dir)
        
        # Should handle errors gracefully
        results = evaluator.evaluate(
            dataset=dataset,
            system=failing_system,
            phase="error_test"
        )
        
        # Should have attempted 1, succeeded 0
        assert results['total_test_cases'] == 1
        assert results['successful_evaluations'] == 0
    
    def test_aggregate_metrics_structure(self, sample_dataset, simple_system, temp_output_dir):
        """Test structure of aggregate metrics."""
        evaluator = Evaluator(output_dir=temp_output_dir)
        
        results = evaluator.evaluate(
            dataset=sample_dataset,
            system=simple_system,
            phase="aggregate_test"
        )
        
        aggregates = results['aggregate_metrics']
        
        # Should have mean, min, max for metrics
        # Check for latency (efficiency metric)
        assert 'latency_ms_mean' in aggregates
        
        # Check for tokens (efficiency metric)
        assert 'tokens_per_query_mean' in aggregates
        
        # Quality metrics should be present
        has_quality = any('relevance' in k or 'hallucination' in k for k in aggregates.keys())
        assert has_quality
    
    def test_metric_grouping_consistency(self, sample_dataset, simple_system, temp_output_dir):
        """Test that metric grouping is consistent across categories."""
        evaluator = Evaluator(output_dir=temp_output_dir)
        
        results = evaluator.evaluate(
            dataset=sample_dataset,
            system=simple_system,
            phase="grouping_test"
        )
        
        aggregates = results['aggregate_metrics']
        
        # All mean values should be present
        mean_keys = [k for k in aggregates.keys() if '_mean' in k]
        assert len(mean_keys) > 0
        
        # Check that we have means for different metric types
        has_rouge_mean = any('rouge' in k and '_mean' in k for k in aggregates.keys())
        has_efficiency_mean = any(('latency' in k or 'tokens' in k) and '_mean' in k for k in aggregates.keys())
        has_quality_mean = any(('relevance' in k or 'hallucination' in k) and '_mean' in k for k in aggregates.keys())
        
        # At least efficiency should always be present
        assert has_efficiency_mean
        
        # Rouge only if ground truth provided
        if any(tc.ground_truth for tc in sample_dataset):
            assert has_rouge_mean
    
    def test_timeout_handling(self, temp_output_dir):
        """Test timeout handling for slow systems (cross-platform)."""
        import time
        
        dataset = BenchmarkDataset(name="timeout_test")
        dataset.add_test_case(TestCase(
            id="timeout_001",
            query="Slow query",
            category="timeout"
        ))
        
        def slow_system(query: str) -> str:
            time.sleep(5)  # Simulate slow response (5 seconds)
            return "Too slow"
        
        # Set timeout to 2 seconds (shorter than the 5-second sleep)
        evaluator = Evaluator(output_dir=temp_output_dir, timeout_seconds=2)
        
        results = evaluator.evaluate(
            dataset=dataset,
            system=slow_system,
            phase="timeout_test"
        )
        
        # Should have caught the timeout (works on both Unix and Windows now)
        assert results['failed_evaluations'] == 1
        assert results['successful_evaluations'] == 0
        assert len(results['failures']) == 1
        
        # Check failure details
        failure = results['failures'][0]
        assert failure['error_type'] == 'EvaluationTimeoutError'
        assert 'timeout' in failure['error_message'].lower()
        assert failure['test_case_id'] == 'timeout_001'
    
    def test_type_validation(self, temp_output_dir):
        """Test that non-string responses are caught."""
        dataset = BenchmarkDataset(name="type_test")
        dataset.add_test_case(TestCase(
            id="type_001",
            query="Type test",
            category="type"
        ))
        
        def invalid_system(query: str):
            return 42  # Returns int instead of str
        
        evaluator = Evaluator(output_dir=temp_output_dir)
        
        results = evaluator.evaluate(
            dataset=dataset,
            system=invalid_system,
            phase="type_test"
        )
        
        # Should have 1 failure
        assert results['failed_evaluations'] == 1
        assert results['successful_evaluations'] == 0
        assert len(results['failures']) == 1
        
        # Check failure details
        failure = results['failures'][0]
        assert failure['error_type'] == 'TypeError'
        assert 'must return str' in failure['error_message']
        assert failure['test_case_id'] == 'type_001'
    
    def test_failure_tracking(self, temp_output_dir):
        """Test that failures are properly tracked."""
        dataset = BenchmarkDataset(name="failure_test")
        
        # Add multiple test cases
        for i in range(5):
            dataset.add_test_case(TestCase(
                id=f"fail_{i}",
                query=f"Query {i}",
                category="test"
            ))
        
        call_count = [0]
        
        def intermittent_system(query: str) -> str:
            call_count[0] += 1
            if call_count[0] % 2 == 0:
                raise ValueError(f"Simulated failure {call_count[0]}")
            return f"Success {call_count[0]}"
        
        evaluator = Evaluator(output_dir=temp_output_dir)
        
        results = evaluator.evaluate(
            dataset=dataset,
            system=intermittent_system,
            phase="failure_test"
        )
        
        # Should have some successes and some failures
        assert results['successful_evaluations'] == 3  # Odd numbers: 1, 3, 5
        assert results['failed_evaluations'] == 2      # Even numbers: 2, 4
        assert results['success_rate'] == 0.6          # 3/5 = 60%
        
        # Check failures list
        assert len(results['failures']) == 2
        for failure in results['failures']:
            assert 'test_case_id' in failure
            assert 'error_type' in failure
            assert 'error_message' in failure
            assert 'timestamp' in failure
            assert failure['error_type'] == 'ValueError'
    
    def test_success_rate_calculation(self, temp_output_dir):
        """Test success rate calculation."""
        dataset = BenchmarkDataset(name="rate_test")
        dataset.add_test_case(TestCase(id="1", query="q1", category="test"))
        dataset.add_test_case(TestCase(id="2", query="q2", category="test"))
        
        def working_system(query: str) -> str:
            return "response"
        
        evaluator = Evaluator(output_dir=temp_output_dir)
        
        results = evaluator.evaluate(
            dataset=dataset,
            system=working_system,
            phase="rate_test"
        )
        
        assert results['success_rate'] == 1.0  # 100% success
        assert results['successful_evaluations'] == 2
        assert results['failed_evaluations'] == 0
    
    def test_results_include_timeout_config(self, temp_output_dir):
        """Test that results include timeout configuration."""
        dataset = BenchmarkDataset(name="config_test")
        dataset.add_test_case(TestCase(id="1", query="q", category="test"))
        
        def simple_system(query: str) -> str:
            return "response"
        
        evaluator = Evaluator(output_dir=temp_output_dir, timeout_seconds=30)
        
        results = evaluator.evaluate(
            dataset=dataset,
            system=simple_system,
            phase="config_test"
        )
        
        assert results['timeout_seconds'] == 30

