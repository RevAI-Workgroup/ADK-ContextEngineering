"""
Main evaluation orchestrator for context engineering experiments.

This module coordinates evaluation runs, manages benchmarks,
and generates comparative reports.
"""

from typing import List, Dict, Any, Callable, Optional
from pathlib import Path
import time
from datetime import datetime
import threading

from .metrics import MetricsCollector
from .benchmarks import BenchmarkDataset


class TimeoutError(Exception):
    """Raised when a system call exceeds the timeout."""
    pass


def _timeout_wrapper(func: Callable, args: tuple, kwargs: dict, result_container: list, exception_container: list):
    """
    Helper function to run a callable in a thread and capture result/exception.
    
    Args:
        func: The callable to execute
        args: Positional arguments for func
        kwargs: Keyword arguments for func
        result_container: List to store the result
        exception_container: List to store any exception
    """
    try:
        result = func(*args, **kwargs)
        result_container.append(result)
    except Exception as e:
        exception_container.append(e)


def call_with_timeout(func: Callable, args: tuple = (), kwargs: dict = None, timeout_seconds: int = 60):
    """
    Call a function with a timeout (cross-platform).
    
    Works on both Unix and Windows by using threading.
    
    Args:
        func: The callable to execute
        args: Positional arguments for func
        kwargs: Keyword arguments for func
        timeout_seconds: Timeout in seconds
        
    Returns:
        The return value of func
        
    Raises:
        TimeoutError: If func doesn't complete within timeout_seconds
        Exception: Any exception raised by func
    """
    if kwargs is None:
        kwargs = {}
    
    result_container = []
    exception_container = []
    
    # Create and start thread
    thread = threading.Thread(
        target=_timeout_wrapper,
        args=(func, args, kwargs, result_container, exception_container),
        daemon=True
    )
    thread.start()
    
    # Wait for thread to complete with timeout
    thread.join(timeout_seconds)
    
    # Check if thread is still alive (timeout occurred)
    if thread.is_alive():
        # Thread is still running - timeout occurred
        raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
    
    # Check if exception occurred
    if exception_container:
        raise exception_container[0]
    
    # Return result
    if result_container:
        return result_container[0]
    
    # Function returned None
    return None


class Evaluator:
    """
    Main evaluation orchestrator.
    
    Coordinates running evaluations, collecting metrics,
    and comparing different approaches.
    """
    
    def __init__(
        self,
        metrics: Optional[List[str]] = None,
        output_dir: str = "docs/phase_summaries",
        timeout_seconds: int = 60
    ):
        """
        Initialize evaluator.
        
        Args:
            metrics: List of metric names to track
            output_dir: Directory to save evaluation results
            timeout_seconds: Timeout for each system call (default 60s)
        """
        self.metrics = metrics or ['accuracy', 'latency', 'token_usage']
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = timeout_seconds
        
        self.metrics_collector = MetricsCollector()
    
    def evaluate(
        self,
        dataset: BenchmarkDataset,
        system: Callable[[str], str],
        phase: str = "baseline",
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Evaluate a system on a benchmark dataset.
        
        Args:
            dataset: BenchmarkDataset to evaluate on
            system: Callable that takes a query and returns a response
            phase: Name of the current phase (for tracking)
            description: Description of the system being evaluated
            
        Returns:
            Dictionary containing evaluation results and metrics
        """
        print(f"\n{'='*70}")
        print(f"Running Evaluation: {phase}")
        print(f"Dataset: {dataset.name} ({len(dataset)} test cases)")
        if description:
            print(f"Description: {description}")
        print(f"Timeout: {self.timeout_seconds}s per test case")
        print(f"{'='*70}\n")
        
        results = []
        failures = []
        
        for i, test_case in enumerate(dataset, 1):
            print(f"[{i}/{len(dataset)}] Processing: {test_case.id}")
            
            try:
                # Measure latency with timeout protection (cross-platform)
                start_time = time.time()
                
                # Call system with timeout protection
                response = call_with_timeout(
                    func=system,
                    args=(test_case.query,),
                    timeout_seconds=self.timeout_seconds
                )
                
                latency_ms = (time.time() - start_time) * 1000
                
                # Validate response type
                if not isinstance(response, str):
                    raise TypeError(
                        f"System must return str, got {type(response).__name__}. "
                        f"Response: {response}"
                    )
                
                # Evaluate response
                eval_result = self.metrics_collector.evaluate(
                    query=test_case.query,
                    response=response,
                    ground_truth=test_case.ground_truth,
                    context=test_case.context,
                    latency_ms=latency_ms
                )
                
                results.append(eval_result)
                
                # Print quick summary
                if test_case.ground_truth:
                    rouge1 = eval_result.metrics.get('rouge1_f1')
                    if rouge1:
                        print(f"  -> ROUGE-1: {rouge1.value:.3f}, Latency: {latency_ms:.0f}ms")
                else:
                    print(f"  -> Latency: {latency_ms:.0f}ms")
                
            except TimeoutError:
                error_msg = f"Timeout after {self.timeout_seconds}s"
                print(f"  [ERROR] {error_msg}")
                failures.append({
                    'test_case_id': test_case.id,
                    'query': test_case.query,
                    'error_type': 'TimeoutError',
                    'error_message': error_msg,
                    'timestamp': datetime.now().isoformat()
                })
                continue
                
            except TypeError as e:
                error_msg = f"Type validation failed: {e}"
                print(f"  [ERROR] {error_msg}")
                failures.append({
                    'test_case_id': test_case.id,
                    'query': test_case.query,
                    'error_type': 'TypeError',
                    'error_message': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                continue
                
            except Exception as e:
                error_msg = f"Unexpected error: {e}"
                print(f"  [ERROR] {error_msg}")
                failures.append({
                    'test_case_id': test_case.id,
                    'query': test_case.query,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                continue
        
        # Calculate aggregate metrics
        aggregates = self.metrics_collector.get_aggregate_metrics()
        
        # Prepare results with failure tracking
        evaluation_results = {
            'phase': phase,
            'description': description,
            'dataset': dataset.name,
            'total_test_cases': len(dataset),
            'successful_evaluations': len(results),
            'failed_evaluations': len(failures),
            'success_rate': len(results) / len(dataset) if len(dataset) > 0 else 0.0,
            'timeout_seconds': self.timeout_seconds,
            'timestamp': datetime.now().isoformat(),
            'aggregate_metrics': aggregates,
            'individual_results': [r.to_dict() for r in results],
            'failures': failures
        }
        
        # Print summary
        self._print_summary(aggregates, phase, len(results), len(failures), len(dataset))
        
        return evaluation_results
    
    def _print_summary(
        self, 
        aggregates: Dict[str, float], 
        phase: str,
        successful: int,
        failed: int,
        total: int
    ) -> None:
        """Print evaluation summary with consistent mean-only filtering."""
        print(f"\n{'='*70}")
        print(f"Evaluation Summary: {phase}")
        print("="*70 + "\n")
        
        # Print execution summary
        success_rate = (successful / total * 100) if total > 0 else 0
        print("Test Cases:")
        print(f"  Total: {total}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print()
        
        # Group metrics by type (show only mean values for clean summary)
        accuracy_metrics = {k: v for k, v in aggregates.items() if 'rouge' in k and '_mean' in k}
        efficiency_metrics = {k: v for k, v in aggregates.items() if ('latency' in k or 'tokens' in k) and '_mean' in k}
        quality_metrics = {k: v for k, v in aggregates.items() if ('relevance' in k or 'hallucination' in k) and '_mean' in k}
        
        if accuracy_metrics:
            print("Accuracy Metrics:")
            for metric, value in accuracy_metrics.items():
                print(f"  {metric}: {value:.4f}")
            print()
        
        if quality_metrics:
            print("Quality Metrics:")
            for metric, value in quality_metrics.items():
                print(f"  {metric}: {value:.4f}")
            print()
        
        if efficiency_metrics:
            print("Efficiency Metrics:")
            for metric, value in efficiency_metrics.items():
                print(f"  {metric}: {value:.2f}")
            print()
        
        print(f"{'='*70}\n")
    
    def save_results(self, results: Dict[str, Any], filename: str) -> None:
        """
        Save evaluation results to file.
        
        Saves the complete evaluation results including phase info, metrics,
        individual results, and failure tracking.
        
        Args:
            results: Evaluation results dictionary (from evaluate() method)
            filename: Output filename (e.g., "phase1_results.json")
        """
        import json
        
        output_path = self.output_dir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"Results saved to: {output_path}")
    
    def compare_with_baseline(
        self,
        current_results: Dict[str, Any],
        baseline_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare current results with baseline.
        
        Args:
            current_results: Current evaluation results
            baseline_file: Path to baseline results file
            
        Returns:
            Dictionary containing comparison metrics
        """
        if not baseline_file or not Path(baseline_file).exists():
            print("No baseline found for comparison.")
            return {}
        
        # Load baseline (would implement full loading logic)
        # For now, return placeholder
        return {
            'comparison': 'Not yet implemented',
            'baseline_file': baseline_file
        }

