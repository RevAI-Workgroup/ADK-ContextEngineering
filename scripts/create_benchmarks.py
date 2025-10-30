"""
Script to generate benchmark datasets for evaluation.

This script creates the initial benchmark datasets used
throughout the project phases.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.evaluation.benchmarks import create_baseline_dataset, create_rag_dataset


def main():
    """Generate and save benchmark datasets."""
    
    print("Creating Benchmark Datasets...")
    print("=" * 70)
    
    # Create data directory
    data_dir = project_root / "data" / "test_sets"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create baseline dataset
    print("\n1. Creating baseline dataset...")
    baseline_dataset = create_baseline_dataset()
    baseline_path = data_dir / "baseline_qa.json"
    baseline_dataset.save(str(baseline_path))
    print(f"   [OK] Created baseline dataset with {len(baseline_dataset)} test cases")
    print(f"   -> Saved to: {baseline_path}")
    
    # Print category breakdown
    categories = {}
    for tc in baseline_dataset:
        categories[tc.category] = categories.get(tc.category, 0) + 1
    
    print("\n   Category breakdown:")
    for category, count in categories.items():
        print(f"     - {category}: {count} cases")
    
    # Create RAG dataset
    print("\n2. Creating RAG dataset...")
    rag_dataset = create_rag_dataset()
    rag_path = data_dir / "rag_qa.json"
    rag_dataset.save(str(rag_path))
    print(f"   [OK] Created RAG dataset with {len(rag_dataset)} test cases")
    print(f"   -> Saved to: {rag_path}")
    
    print("\n" + "=" * 70)
    print("Benchmark datasets created successfully!")
    print(f"\nDatasets location: {data_dir}")


if __name__ == "__main__":
    main()

