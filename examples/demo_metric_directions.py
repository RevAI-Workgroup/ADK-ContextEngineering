"""
Demo: Metric Direction Handling in Paired Comparison
======================================================

This demonstrates the fix for handling "lower is better" metrics correctly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.paired_comparison import PairedComparisonTest


def demo_metric_directions():
    """Demonstrate proper handling of different metric directions."""
    
    print("="*80)
    print("DEMO: Metric Direction Handling")
    print("="*80)
    
    # Simulated baseline vs improved system
    def baseline_system(test_case):
        return {
            'accuracy': 0.70,           # Want higher
            'rouge1_f1': 0.55,          # Want higher
            'latency_ms': 500.0,        # Want lower
            'token_count': 1500,        # Want lower
            'hallucination_rate': 0.15  # Want lower
        }
    
    def improved_system(test_case):
        return {
            'accuracy': 0.85,           # Better (increased)
            'rouge1_f1': 0.70,          # Better (increased)
            'latency_ms': 300.0,        # Better (decreased)
            'token_count': 1000,        # Better (decreased)
            'hallucination_rate': 0.05  # Better (decreased)
        }
    
    # Create paired comparison test
    test = PairedComparisonTest(
        technique_a=baseline_system,
        technique_b=improved_system,
        technique_a_name="Baseline",
        technique_b_name="Optimized"
    )
    
    # Define metric extractors
    metric_extractors = {
        'accuracy': lambda r: r['accuracy'],
        'rouge1_f1': lambda r: r['rouge1_f1'],
        'latency_ms': lambda r: r['latency_ms'],
        'token_count': lambda r: r['token_count'],
        'hallucination_rate': lambda r: r['hallucination_rate']
    }
    
    # Define metric directions (THIS IS THE KEY FIX!)
    metric_directions = {
        'accuracy': 'higher',           # Higher accuracy is better
        'rouge1_f1': 'higher',          # Higher ROUGE is better
        'latency_ms': 'lower',          # Lower latency is better ✓
        'token_count': 'lower',         # Lower token use is better ✓
        'hallucination_rate': 'lower'   # Lower hallucination is better ✓
    }
    
    # Run test with metric directions
    print("\n>>> Running paired comparison with proper metric directions...\n")
    
    results = test.run_test(
        test_cases=[1, 2, 3, 4, 5],  # 5 test cases
        metric_extractors=metric_extractors,
        metric_directions=metric_directions,  # ← THE FIX!
        randomize=False
    )
    
    # Print results
    test.print_summary(results)
    
    # Explain the results
    print("\n" + "="*80)
    print("EXPLANATION")
    print("="*80)
    print("""
Before the fix:
  - All metrics were treated as "higher is better"
  - Lower latency (300ms vs 500ms) would show as -40% "improvement" [WRONG]
  - Lower hallucination (0.05 vs 0.15) would show as -66% "improvement" [WRONG]
  - This gave INVERTED conclusions!

After the fix:
  - Metrics can be marked as 'higher' or 'lower' is better
  - Lower latency (300ms vs 500ms) shows as +40% improvement [CORRECT]
  - Lower hallucination (0.05 vs 0.15) shows as +66% improvement [CORRECT]
  - All improvements are correctly signed!

Notice in the output above:
  - All 5 metrics show POSITIVE improvement for the Optimized system
  - The [^ higher is better] and [v lower is better] indicators
  - Raw differences show actual values (B-A)
  - Improvement percentages are correctly signed
    """)
    print("="*80)


if __name__ == "__main__":
    demo_metric_directions()

