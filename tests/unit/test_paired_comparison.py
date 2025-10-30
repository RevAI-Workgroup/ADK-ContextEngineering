"""
Tests for paired comparison framework with metric direction handling.
"""

import pytest
from src.evaluation.paired_comparison import PairedComparisonTest, PairedComparisonResult


class TestMetricDirections:
    """Test metric direction handling (higher vs lower is better)."""
    
    def test_higher_is_better_metric(self):
        """Test that 'higher' metrics correctly identify improvements."""
        # Setup: Technique B has higher accuracy (better)
        def technique_a(x):
            return {'accuracy': 0.70}
        
        def technique_b(x):
            return {'accuracy': 0.85}
        
        test = PairedComparisonTest(technique_a, technique_b, "Baseline", "Improved")
        
        results = test.run_test(
            test_cases=[1, 2, 3],
            metric_extractors={'accuracy': lambda r: r['accuracy']},
            metric_directions={'accuracy': 'higher'},
            randomize=False
        )
        
        result = results['accuracy']
        
        # Verify: B has higher mean
        assert result.technique_b_mean > result.technique_a_mean
        
        # Verify: difference is positive (B - A)
        assert result.difference > 0
        
        # Verify: percent_improvement is positive (B is better)
        assert result.percent_improvement > 0
        
        # Verify: direction stored in metadata
        assert result.metadata['direction'] == 'higher'
    
    def test_lower_is_better_metric(self):
        """Test that 'lower' metrics correctly identify improvements."""
        # Setup: Technique B has lower latency (better)
        def technique_a(x):
            return {'latency_ms': 500.0}
        
        def technique_b(x):
            return {'latency_ms': 300.0}
        
        test = PairedComparisonTest(technique_a, technique_b, "Baseline", "Optimized")
        
        results = test.run_test(
            test_cases=[1, 2, 3],
            metric_extractors={'latency_ms': lambda r: r['latency_ms']},
            metric_directions={'latency_ms': 'lower'},
            randomize=False
        )
        
        result = results['latency_ms']
        
        # Verify: B has lower mean (better for latency)
        assert result.technique_b_mean < result.technique_a_mean
        
        # Verify: raw difference is negative (B - A)
        assert result.difference < 0
        
        # Verify: percent_improvement is positive (B is better, sign flipped)
        assert result.percent_improvement > 0
        
        # Verify: direction stored in metadata
        assert result.metadata['direction'] == 'lower'
    
    def test_lower_is_better_when_b_worse(self):
        """Test that 'lower' metrics correctly identify when B is worse."""
        # Setup: Technique B has higher latency (worse)
        def technique_a(x):
            return {'latency_ms': 300.0}
        
        def technique_b(x):
            return {'latency_ms': 500.0}
        
        test = PairedComparisonTest(technique_a, technique_b, "Baseline", "Slower")
        
        results = test.run_test(
            test_cases=[1, 2, 3],
            metric_extractors={'latency_ms': lambda r: r['latency_ms']},
            metric_directions={'latency_ms': 'lower'},
            randomize=False
        )
        
        result = results['latency_ms']
        
        # Verify: B has higher mean (worse for latency)
        assert result.technique_b_mean > result.technique_a_mean
        
        # Verify: raw difference is positive (B - A)
        assert result.difference > 0
        
        # Verify: percent_improvement is negative (B is worse, sign flipped)
        assert result.percent_improvement < 0
        
        # Verify: direction stored in metadata
        assert result.metadata['direction'] == 'lower'
    
    def test_mixed_metric_directions(self):
        """Test handling multiple metrics with different directions."""
        def technique_a(x):
            return {
                'accuracy': 0.70,
                'latency_ms': 500.0,
                'hallucination_rate': 0.15
            }
        
        def technique_b(x):
            return {
                'accuracy': 0.85,      # Better (higher)
                'latency_ms': 300.0,   # Better (lower)
                'hallucination_rate': 0.20  # Worse (higher when lower is better)
            }
        
        test = PairedComparisonTest(technique_a, technique_b, "Baseline", "Treatment")
        
        results = test.run_test(
            test_cases=[1, 2, 3],
            metric_extractors={
                'accuracy': lambda r: r['accuracy'],
                'latency_ms': lambda r: r['latency_ms'],
                'hallucination_rate': lambda r: r['hallucination_rate']
            },
            metric_directions={
                'accuracy': 'higher',
                'latency_ms': 'lower',
                'hallucination_rate': 'lower'
            },
            randomize=False
        )
        
        # Accuracy: B better (higher value, higher is better)
        assert results['accuracy'].percent_improvement > 0
        assert results['accuracy'].metadata['direction'] == 'higher'
        
        # Latency: B better (lower value, lower is better)
        assert results['latency_ms'].percent_improvement > 0
        assert results['latency_ms'].metadata['direction'] == 'lower'
        
        # Hallucination: B worse (higher value, lower is better)
        assert results['hallucination_rate'].percent_improvement < 0
        assert results['hallucination_rate'].metadata['direction'] == 'lower'
    
    def test_default_direction_is_higher(self):
        """Test that unspecified metrics default to 'higher' for backward compatibility."""
        def technique_a(x):
            return {'score': 0.70}
        
        def technique_b(x):
            return {'score': 0.85}
        
        test = PairedComparisonTest(technique_a, technique_b)
        
        # Don't specify metric_directions - should default to 'higher'
        results = test.run_test(
            test_cases=[1, 2, 3],
            metric_extractors={'score': lambda r: r['score']},
            randomize=False
        )
        
        result = results['score']
        
        # Should treat as 'higher' by default
        assert result.metadata['direction'] == 'higher'
        assert result.percent_improvement > 0  # B is better
    
    def test_percent_improvement_calculation(self):
        """Test that percent improvement is calculated correctly for both directions."""
        # Higher is better: accuracy 0.5 -> 0.6 = +20% improvement
        def technique_a_high(x):
            return {'accuracy': 0.5}
        
        def technique_b_high(x):
            return {'accuracy': 0.6}
        
        test_high = PairedComparisonTest(technique_a_high, technique_b_high)
        results_high = test_high.run_test(
            test_cases=[1],
            metric_extractors={'accuracy': lambda r: r['accuracy']},
            metric_directions={'accuracy': 'higher'},
            randomize=False
        )
        
        # Improvement should be (0.6 - 0.5) / 0.5 * 100 = +20%
        assert abs(results_high['accuracy'].percent_improvement - 20.0) < 0.01
        
        # Lower is better: latency 500 -> 400 = +20% improvement (sign flipped)
        def technique_a_low(x):
            return {'latency': 500.0}
        
        def technique_b_low(x):
            return {'latency': 400.0}
        
        test_low = PairedComparisonTest(technique_a_low, technique_b_low)
        results_low = test_low.run_test(
            test_cases=[1],
            metric_extractors={'latency': lambda r: r['latency']},
            metric_directions={'latency': 'lower'},
            randomize=False
        )
        
        # Raw change is (400 - 500) / 500 = -20%, but flipped for 'lower' = +20%
        assert abs(results_low['latency'].percent_improvement - 20.0) < 0.01


class TestBackwardCompatibility:
    """Ensure changes maintain backward compatibility."""
    
    def test_run_test_without_metric_directions(self):
        """Test that run_test works without metric_directions parameter."""
        def technique_a(x):
            return {'score': 0.7}
        
        def technique_b(x):
            return {'score': 0.8}
        
        test = PairedComparisonTest(technique_a, technique_b)
        
        # Old API: no metric_directions parameter
        results = test.run_test(
            test_cases=[1, 2, 3],
            metric_extractors={'score': lambda r: r['score']},
            randomize=False
        )
        
        # Should work and default to 'higher'
        assert results['score'].metadata['direction'] == 'higher'
        assert results['score'].percent_improvement > 0

