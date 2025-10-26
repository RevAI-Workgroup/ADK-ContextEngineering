"""
Script to run evaluation on a system.

This script provides the baseline evaluation functionality
for Phase 0 and can be extended for later phases.
"""

import sys
import argparse
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.evaluation.evaluator import Evaluator
from src.evaluation.benchmarks import BenchmarkDataset


def simple_echo_system(query: str) -> str:
    """
    Simple echo system for baseline testing.
    
    This is a placeholder system that simply echoes back
    a generic response. Used for Phase 0 baseline.
    
    Args:
        query: Input query
        
    Returns:
        Generic response string
    """
    return f"This is a simple response to: {query}"


def main():
    """Run evaluation."""
    
    parser = argparse.ArgumentParser(description="Run evaluation on a system")
    parser.add_argument(
        "--dataset",
        type=str,
        default="data/test_sets/baseline_qa.json",
        help="Path to benchmark dataset"
    )
    parser.add_argument(
        "--phase",
        type=str,
        default="phase0_baseline",
        help="Phase name for tracking"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output filename (default: auto-generated)"
    )
    
    args = parser.parse_args()
    
    # Load dataset
    print(f"\nLoading dataset from: {args.dataset}")
    try:
        dataset = BenchmarkDataset.load(args.dataset)
        print(f"[OK] Loaded {len(dataset)} test cases")
    except FileNotFoundError:
        print(f"[ERROR] Dataset not found: {args.dataset}")
        print("\nPlease run: python scripts/create_benchmarks.py")
        return 1
    
    # Initialize evaluator
    evaluator = Evaluator()
    
    # Run evaluation
    results = evaluator.evaluate(
        dataset=dataset,
        system=simple_echo_system,
        phase=args.phase,
        description="Baseline evaluation with simple echo system"
    )
    
    # Save results
    output_filename = args.output or f"{args.phase}_results.json"
    evaluator.save_results(results, output_filename)
    
    print("\n[OK] Evaluation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

