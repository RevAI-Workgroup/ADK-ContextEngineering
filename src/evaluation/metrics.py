"""
Metrics calculation module for evaluating LLM responses.

This module provides various metrics for measuring effectiveness,
efficiency, and quality of LLM responses.
"""

from typing import List, Dict, Any, Optional
import re
from dataclasses import dataclass, field
from rouge_score import rouge_scorer
import tiktoken
import json
from pathlib import Path
from datetime import datetime


@dataclass
class MetricResult:
    """Container for metric calculation results."""
    
    metric_name: str
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class EvaluationResult:
    """Container for complete evaluation results."""
    
    query: str
    response: str
    ground_truth: Optional[str] = None
    metrics: Dict[str, MetricResult] = field(default_factory=dict)
    latency_ms: float = 0.0
    token_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'query': self.query,
            'response': self.response,
            'ground_truth': self.ground_truth,
            'metrics': {
                name: {
                    'value': metric.value,
                    'metadata': metric.metadata
                }
                for name, metric in self.metrics.items()
            },
            'latency_ms': self.latency_ms,
            'token_count': self.token_count,
            'timestamp': self.timestamp
        }


class MetricsCollector:
    """
    Collects and calculates various metrics for LLM evaluation.
    
    Metrics include:
    - Answer accuracy (ROUGE scores)
    - Relevance scoring
    - Hallucination detection
    - Token usage
    - Latency
    """
    
    def __init__(self, encoding_name: str = "cl100k_base"):
        """
        Initialize metrics collector.
        
        Args:
            encoding_name: Tokenizer encoding to use for token counting
        """
        self.rouge_scorer = rouge_scorer.RougeScorer(
            ['rouge1', 'rouge2', 'rougeL'],
            use_stemmer=True
        )
        self.encoding = tiktoken.get_encoding(encoding_name)
        self.results: List[EvaluationResult] = []
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))
    
    def calculate_rouge_scores(
        self,
        prediction: str,
        reference: str
    ) -> Dict[str, MetricResult]:
        """
        Calculate ROUGE scores for answer accuracy.
        
        Args:
            prediction: Model's generated response
            reference: Ground truth reference answer
            
        Returns:
            Dictionary of ROUGE metric results
        """
        scores = self.rouge_scorer.score(reference, prediction)
        
        return {
            'rouge1_f1': MetricResult(
                metric_name='rouge1_f1',
                value=scores['rouge1'].fmeasure,
                metadata={
                    'precision': scores['rouge1'].precision,
                    'recall': scores['rouge1'].recall
                }
            ),
            'rouge2_f1': MetricResult(
                metric_name='rouge2_f1',
                value=scores['rouge2'].fmeasure,
                metadata={
                    'precision': scores['rouge2'].precision,
                    'recall': scores['rouge2'].recall
                }
            ),
            'rougeL_f1': MetricResult(
                metric_name='rougeL_f1',
                value=scores['rougeL'].fmeasure,
                metadata={
                    'precision': scores['rougeL'].precision,
                    'recall': scores['rougeL'].recall
                }
            )
        }
    
    def detect_hallucination_heuristic(self, response: str, context: str = "") -> MetricResult:
        """
        Heuristic-based hallucination detection.
        
        This is a simple baseline implementation. Phase 0 uses basic patterns.
        Future phases can incorporate more sophisticated detection.
        
        Scoring: Each check contributes 0 or 1 point. Final score is normalized by total checks.
        
        Args:
            response: Model's response
            context: Context provided to the model (empty string if no context)
            
        Returns:
            MetricResult with hallucination score (0-1, higher = more likely hallucination)
        """
        hallucination_indicators = 0
        total_checks = 3  # Fixed number of checks for consistent scoring
        
        # Minimum context length threshold for "sufficient context"
        MIN_CONTEXT_LENGTH = 50
        has_sufficient_context = len(context) >= MIN_CONTEXT_LENGTH
        
        # Check 1: Overly confident phrases without sufficient context
        # High confidence claims need supporting context
        confident_phrases = [
            "I'm absolutely certain",
            "There's no doubt",
            "It's definitely",
            "I can guarantee",
            "without question",
            "undoubtedly"
        ]
        if any(phrase.lower() in response.lower() for phrase in confident_phrases):
            if not has_sufficient_context:
                hallucination_indicators += 1
        
        # Check 2: Specific numbers/dates/statistics without sufficient context
        # Concrete data points should be backed by source material
        has_specific_data = bool(re.search(r'\b\d{4}\b|\b\d+%\b|\$\d+|(\d+\.\d+)', response))
        if has_specific_data and not has_sufficient_context:
            hallucination_indicators += 1
        
        # Check 3: Lack of hedging in long responses without context
        # Long responses without hedge words may indicate over-confidence
        hedge_phrases = ["I think", "might be", "possibly", "I'm not sure", "probably", "may", "could be"]
        has_hedging = any(phrase.lower() in response.lower() for phrase in hedge_phrases)
        is_long_response = len(response) > 100
        
        if is_long_response and not has_hedging and not has_sufficient_context:
            hallucination_indicators += 1
        
        # Calculate normalized score
        hallucination_score = hallucination_indicators / total_checks
        
        return MetricResult(
            metric_name='hallucination_rate',
            value=hallucination_score,
            metadata={
                'method': 'heuristic_baseline',
                'indicators_triggered': hallucination_indicators,
                'total_checks': total_checks,
                'has_sufficient_context': has_sufficient_context,
                'context_length': len(context)
            }
        )
    
    def calculate_relevance_score(
        self,
        query: str,
        response: str,
        retrieved_docs: Optional[List[str]] = None
    ) -> MetricResult:
        """
        Calculate relevance score using simple keyword overlap.
        
        This is a baseline implementation. More sophisticated methods
        will be implemented in later phases (e.g., cross-encoder scoring).
        
        Args:
            query: User's query
            response: Model's response
            retrieved_docs: Documents retrieved for context (if any)
            
        Returns:
            MetricResult with relevance score (0-1)
        """
        # Extract keywords from query
        query_words = set(re.findall(r'\b\w+\b', query.lower()))
        response_words = set(re.findall(r'\b\w+\b', response.lower()))
        
        # Calculate Jaccard similarity
        if not query_words:
            relevance = 0.0
        else:
            intersection = query_words.intersection(response_words)
            union = query_words.union(response_words)
            relevance = len(intersection) / len(union) if union else 0.0
        
        return MetricResult(
            metric_name='relevance_score',
            value=relevance,
            metadata={
                'method': 'jaccard_similarity',
                'query_terms': len(query_words),
                'matching_terms': len(query_words.intersection(response_words))
            }
        )
    
    def evaluate(
        self,
        query: str,
        response: str,
        ground_truth: Optional[str] = None,
        context: str = "",
        latency_ms: float = 0.0,
        retrieved_docs: Optional[List[str]] = None
    ) -> EvaluationResult:
        """
        Perform complete evaluation of a query-response pair.
        
        Args:
            query: User's query
            response: Model's response
            ground_truth: Reference answer (if available)
            context: Context provided to model
            latency_ms: Response latency in milliseconds
            retrieved_docs: Retrieved documents for RAG evaluation
            
        Returns:
            Complete EvaluationResult
        """
        result = EvaluationResult(
            query=query,
            response=response,
            ground_truth=ground_truth,
            latency_ms=latency_ms,
            token_count=self.count_tokens(query + response)
        )
        
        # Calculate accuracy metrics if ground truth is available
        if ground_truth:
            rouge_metrics = self.calculate_rouge_scores(response, ground_truth)
            result.metrics.update(rouge_metrics)
        
        # Calculate relevance score
        relevance = self.calculate_relevance_score(query, response, retrieved_docs)
        result.metrics['relevance_score'] = relevance
        
        # Detect hallucinations
        hallucination = self.detect_hallucination_heuristic(response, context)
        result.metrics['hallucination_rate'] = hallucination
        
        # Store result
        self.results.append(result)
        
        return result
    
    def get_aggregate_metrics(self) -> Dict[str, float]:
        """
        Calculate aggregate metrics across all evaluated queries.
        
        Returns:
            Dictionary of averaged metrics
        """
        if not self.results:
            return {}
        
        aggregates = {}
        metric_names = set()
        
        # Collect all metric names
        for result in self.results:
            metric_names.update(result.metrics.keys())
        
        # Calculate averages
        for metric_name in metric_names:
            values = [
                result.metrics[metric_name].value
                for result in self.results
                if metric_name in result.metrics
            ]
            if values:
                aggregates[f"{metric_name}_mean"] = sum(values) / len(values)
                aggregates[f"{metric_name}_min"] = min(values)
                aggregates[f"{metric_name}_max"] = max(values)
        
        # Average latency and tokens
        aggregates['latency_ms_mean'] = sum(r.latency_ms for r in self.results) / len(self.results)
        aggregates['tokens_per_query_mean'] = sum(r.token_count for r in self.results) / len(self.results)
        
        return aggregates
    
    def save_results(self, output_path: str) -> None:
        """
        Save evaluation results to JSON file.
        
        Args:
            output_path: Path to save results
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'summary': self.get_aggregate_metrics(),
            'total_evaluations': len(self.results),
            'results': [result.to_dict() for result in self.results]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def log(self, data: Dict[str, Any]) -> None:
        """
        Log custom metrics data.
        
        Args:
            data: Dictionary containing metric data to log
        """
        # This can be extended to log to various backends
        print(f"[METRICS] {json.dumps(data)}")
    
    def collect_response_metrics(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect metrics from an agent response for API endpoints.
        
        Args:
            response_data: Response data from agent
            
        Returns:
            Dictionary of metrics
        """
        metrics = response_data.get("metrics", {}).copy()
        
        # Add token counts if available
        response = response_data.get("response", "")
        if response:
            metrics["token_count"] = self.count_tokens(response)
        
        return metrics
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all collected metrics from all phases.
        
        Returns:
            Dictionary containing metrics from all phases
        """
        metrics = {}
        
        # Load Phase 0 metrics if available
        phase0_path = Path("docs/phase_summaries/phase0_baseline_results.json")
        if phase0_path.exists():
            try:
                with open(phase0_path, 'r', encoding='utf-8') as f:
                    metrics["phase0"] = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load phase0 metrics: {e}")
        
        # Add current evaluation results
        if self.results:
            metrics["current"] = {
                "summary": self.get_aggregate_metrics(),
                "count": len(self.results)
            }
        
        return metrics
    
    def get_phase_metrics(self, phase_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metrics for a specific phase.
        
        Args:
            phase_id: Phase identifier (e.g., "phase0", "phase1")
            
        Returns:
            Dictionary containing phase metrics or None if not found
        """
        # Validate phase_id to prevent path traversal
        if not re.match(r'^[a-zA-Z0-9_]+$', phase_id) and phase_id != "current":
            return None
        
        # Try to load from phase summary files
        phase_path = Path(f"docs/phase_summaries/{phase_id}_baseline_results.json")
        if not phase_path.exists():
            phase_path = Path(f"docs/phase_summaries/{phase_id}_results.json")
        
        if phase_path.exists():
            try:
                with open(phase_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load metrics for {phase_id}: {e}")
                return None
        
        # Return current results if requesting current phase
        if phase_id == "current" and self.results:
            return {
                "summary": self.get_aggregate_metrics(),
                "count": len(self.results),
                "results": [r.to_dict() for r in self.results]
            }
        
        return None
    
    def get_metrics_comparison(self) -> Dict[str, Any]:
        """
        Generate a comparison of metrics across phases.
        
        Returns:
            Dictionary with comparison data showing improvements/degradations
        """
        comparison = {
            "phases": [],
            "metrics": {},
            "improvements": {}
        }
        
        # Collect all available phase metrics
        phase_files = Path("docs/phase_summaries").glob("phase*_results.json")
        
        for phase_file in sorted(phase_files):
            phase_id = phase_file.stem.replace("_baseline_results", "").replace("_results", "")
            
            try:
                with open(phase_file, 'r', encoding='utf-8') as f:
                    phase_data = json.load(f)
                    comparison["phases"].append({
                        "id": phase_id,
                        "metrics": phase_data.get("summary", {})
                    })
            except Exception as e:
                print(f"Error loading {phase_file}: {e}")
        
        # Add current metrics if available
        if self.results:
            comparison["phases"].append({
                "id": "current",
                "metrics": self.get_aggregate_metrics()
            })
        
        # Calculate improvements
        if len(comparison["phases"]) > 1:
            baseline = comparison["phases"][0]["metrics"]
            latest = comparison["phases"][-1]["metrics"]
            # Metrics where lower is better
            lower_is_better = {'hallucination_rate', 'latency_ms_mean'}
            
            for metric_name in baseline:
                if metric_name in latest:
                    baseline_val = baseline[metric_name]
                    latest_val = latest[metric_name]
                    
                    # Type safety check
                    if isinstance(baseline_val, (int, float)) and isinstance(latest_val, (int, float)) and baseline_val != 0:
                        change_pct = ((latest_val - baseline_val) / baseline_val) * 100
                        
                        # Invert for metrics where lower is better
                        if any(m in metric_name for m in lower_is_better):
                            improvement_pct = -change_pct
                        else:
                            improvement_pct = change_pct
                        
                        comparison["improvements"][metric_name] = {
                            "baseline": baseline_val,
                            "latest": latest_val,
                            "improvement_pct": improvement_pct
                        }
        
        return comparison
