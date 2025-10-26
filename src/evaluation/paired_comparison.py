"""
Paired comparison testing framework for comparing context engineering techniques.

This module provides tools for running paired comparison experiments where
both techniques are evaluated on the same test cases to measure relative gains.
This is essential for measuring the impact of context engineering improvements
while controlling for test case difficulty.

IMPORTANT: This is NOT traditional A/B testing!
- Traditional A/B: Each test case → ONE variant (A or B) → Compare aggregates
- Paired Comparison: Each test case → BOTH variants (A and B) → Compare differences

Why Paired Comparison?
----------------------
For measuring context engineering gains (e.g., with/without RAG), we need:
1. Direct comparison on same inputs to measure improvement
2. Control for test case difficulty variance
3. More statistical power (paired t-test vs independent samples)
4. Clear attribution of gains to the technique, not test case selection

Example Use Case:
-----------------
baseline = SystemWithoutRAG()
treatment = SystemWithRAG()
test = PairedComparisonTest(baseline, treatment)

# Define metric extractors and directions
metrics = {
    'rouge1_f1': lambda r: r['rouge1_f1'],
    'latency_ms': lambda r: r['latency_ms'],
    'hallucination_rate': lambda r: r['hallucination_rate']
}
directions = {
    'rouge1_f1': 'higher',          # Higher accuracy is better
    'latency_ms': 'lower',          # Lower latency is better
    'hallucination_rate': 'lower'   # Lower hallucination is better
}

results = test.run_test(test_cases, metrics, metric_directions=directions)
test.print_summary(results)
# Shows: "RAG improved ROUGE by +15%, reduced latency by -20% on identical test set"
"""

from typing import List, Dict, Any, Callable, Literal
from dataclasses import dataclass, field
from datetime import datetime
import statistics
import random
import json
from pathlib import Path


@dataclass
class PairedComparisonResult:
    """Results from a paired comparison test."""
    
    technique_a_name: str
    technique_b_name: str
    metric_name: str
    
    technique_a_mean: float
    technique_b_mean: float
    technique_a_std: float
    technique_b_std: float
    
    sample_size_a: int
    sample_size_b: int
    
    difference: float  # B - A (raw difference)
    percent_improvement: float  # Signed improvement (positive = B better, negative = A better)
    
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)  # Should include 'direction': 'higher'|'lower'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'technique_a_name': self.technique_a_name,
            'technique_b_name': self.technique_b_name,
            'metric_name': self.metric_name,
            'technique_a': {
                'mean': self.technique_a_mean,
                'std': self.technique_a_std,
                'sample_size': self.sample_size_a
            },
            'technique_b': {
                'mean': self.technique_b_mean,
                'std': self.technique_b_std,
                'sample_size': self.sample_size_b
            },
            'comparison': {
                'difference': self.difference,
                'percent_improvement': self.percent_improvement
            },
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }


class PairedComparisonTest:
    """
    Framework for comparing two techniques using paired comparison.
    
    This class runs both techniques on EVERY test case (paired comparison),
    allowing direct measurement of improvements while controlling for test
    case difficulty. This is different from traditional A/B testing where
    each test case goes to only one variant.
    
    Use Case: Measuring context engineering gains
    - Baseline technique (e.g., no RAG) vs Treatment (e.g., with RAG)
    - Both run on same inputs to measure relative improvement
    - More statistically powerful than independent samples
    """
    
    def __init__(
        self,
        technique_a: Callable,
        technique_b: Callable,
        technique_a_name: str = "Baseline",
        technique_b_name: str = "Treatment"
    ):
        """
        Initialize paired comparison test.
        
        Args:
            technique_a: Baseline technique (typically without optimization)
            technique_b: Treatment technique (typically with optimization)
            technique_a_name: Name for baseline technique (e.g., "Without RAG")
            technique_b_name: Name for treatment technique (e.g., "With RAG")
        """
        self.technique_a = technique_a
        self.technique_b = technique_b
        self.technique_a_name = technique_a_name
        self.technique_b_name = technique_b_name
        
        self.results_a: List[Dict[str, Any]] = []
        self.results_b: List[Dict[str, Any]] = []
    
    def run_test(
        self,
        test_cases: List[Any],
        metric_extractors: Dict[str, Callable[[Any], float]],
        metric_directions: Dict[str, Literal['higher', 'lower']] = None,
        randomize: bool = True
    ) -> Dict[str, PairedComparisonResult]:
        """
        Run paired comparison test on provided test cases.
        
        IMPORTANT: Both techniques run on EVERY test case for direct comparison.
        This allows measuring improvement while controlling for test difficulty.
        
        Args:
            test_cases: List of test cases to run
            metric_extractors: Dict mapping metric names to functions that extract
                              metric values from results
            metric_directions: Dict mapping metric names to direction ('higher' or 'lower').
                             'higher' means higher values are better (e.g., accuracy, ROUGE).
                             'lower' means lower values are better (e.g., latency, hallucination).
                             Defaults to 'higher' for any unspecified metrics.
            randomize: Whether to randomize execution order (A then B, or B then A)
                      to control for order effects
            
        Returns:
            Dictionary of metric names to PairedComparisonResult objects
        """
        # Default to 'higher' for backward compatibility
        if metric_directions is None:
            metric_directions = {}
        for test_case in test_cases:
            # Randomize execution order to control for order effects
            # (e.g., caching, warmup) but BOTH techniques always run
            run_a_first = random.random() < 0.5 if randomize else True
            
            if run_a_first:
                # Run baseline first, then treatment
                result_a = self.technique_a(test_case)
                result_b = self.technique_b(test_case)
            else:
                # Run treatment first, then baseline
                result_b = self.technique_b(test_case)
                result_a = self.technique_a(test_case)
            
            # Store both results (paired comparison)
            self.results_a.append(result_a)
            self.results_b.append(result_b)
        
        # Calculate statistics for each metric
        ab_results = {}
        
        for metric_name, extractor in metric_extractors.items():
            values_a = [extractor(r) for r in self.results_a]
            values_b = [extractor(r) for r in self.results_b]
            
            mean_a = statistics.mean(values_a)
            mean_b = statistics.mean(values_b)
            std_a = statistics.stdev(values_a) if len(values_a) > 1 else 0.0
            std_b = statistics.stdev(values_b) if len(values_b) > 1 else 0.0
            
            # Raw difference (always B - A)
            difference = mean_b - mean_a
            
            # Get direction for this metric (default to 'higher' for backward compatibility)
            direction = metric_directions.get(metric_name, 'higher')
            
            # Calculate percent improvement based on direction
            # For 'higher' metrics: positive difference = improvement
            # For 'lower' metrics: negative difference = improvement (so flip sign)
            if mean_a != 0:
                raw_percent_change = (difference / abs(mean_a)) * 100
                if direction == 'lower':
                    # For "lower is better" metrics, flip the sign
                    percent_improvement = -raw_percent_change
                else:
                    percent_improvement = raw_percent_change
            else:
                percent_improvement = 0.0
            
            ab_results[metric_name] = PairedComparisonResult(
                technique_a_name=self.technique_a_name,
                technique_b_name=self.technique_b_name,
                metric_name=metric_name,
                technique_a_mean=mean_a,
                technique_b_mean=mean_b,
                technique_a_std=std_a,
                technique_b_std=std_b,
                sample_size_a=len(values_a),
                sample_size_b=len(values_b),
                difference=difference,
                percent_improvement=percent_improvement,
                metadata={'direction': direction}
            )
        
        return ab_results
    
    def save_results(self, output_path: str, ab_results: Dict[str, PairedComparisonResult]) -> None:
        """
        Save paired comparison test results to file.
        
        Args:
            output_path: Path to save results
            ab_results: Dictionary of PairedComparisonResult objects
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'comparison': f"{self.technique_a_name} vs {self.technique_b_name}",
            'total_samples': len(self.results_a),
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                name: result.to_dict()
                for name, result in ab_results.items()
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def print_summary(self, ab_results: Dict[str, PairedComparisonResult]) -> None:
        """
        Print a summary of paired comparison test results.
        
        Correctly interprets improvement based on metric direction stored in metadata.
        For 'higher' metrics (e.g., accuracy): positive improvement = B better
        For 'lower' metrics (e.g., latency): positive improvement = B better (already sign-flipped)
        
        Args:
            ab_results: Dictionary of PairedComparisonResult objects
        """
        print(f"\n{'='*70}")
        print(f"Paired Comparison Results: {self.technique_a_name} vs {self.technique_b_name}")
        print(f"{'='*70}\n")
        
        for metric_name, result in ab_results.items():
            direction = result.metadata.get('direction', 'higher')
            direction_str = "↑" if direction == 'higher' else "↓"
            
            print(f"Metric: {metric_name} [{direction_str} {direction} is better]")
            print(f"  {self.technique_a_name}: {result.technique_a_mean:.4f} (±{result.technique_a_std:.4f})")
            print(f"  {self.technique_b_name}: {result.technique_b_mean:.4f} (±{result.technique_b_std:.4f})")
            print(f"  Raw Difference (B-A): {result.difference:.4f}")
            print(f"  Improvement: {result.percent_improvement:+.2f}%")
            
            # Since percent_improvement is already correctly signed based on direction,
            # we can directly use it to determine which is better
            if result.percent_improvement > 0:
                print(f"  ✓ {self.technique_b_name} is better")
            elif result.percent_improvement < 0:
                print(f"  ✓ {self.technique_a_name} is better")
            else:
                print("  = No significant difference")
            print()
        
        print(f"{'='*70}\n")

