"""
Run History Management System.

This module provides functionality to track and manage agent runs,
storing configurations, queries, responses, and metrics for comparison
and analysis.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path
import json
import uuid
import threading
from contextlib import contextmanager


def _parse_timestamp(timestamp: str) -> datetime:
    """
    Parse ISO timestamp into timezone-aware UTC datetime.
    
    Handles:
    - Timestamps with 'Z' suffix (converts to +00:00)
    - Timestamps with explicit timezone offset
    - Naive timestamps (assumes UTC)
    
    Args:
        timestamp: ISO format timestamp string
        
    Returns:
        Timezone-aware datetime in UTC for consistent comparison.
    """
    # Replace 'Z' suffix with '+00:00' for ISO parsing
    if timestamp.endswith('Z'):
        timestamp = timestamp[:-1] + '+00:00'
    
    dt = datetime.fromisoformat(timestamp)
    
    # If naive datetime (no timezone), treat as UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        # Convert any timezone-aware datetime to UTC for normalization
        dt = dt.astimezone(timezone.utc)
    
    return dt


@dataclass
class RunRecord:
    """
    Record of a single agent run with full context.

    Attributes:
        id: Unique identifier for the run (UUID)
        query: User's input query
        config: Context engineering configuration used
        response: Agent's response text
        metrics: Performance metrics collected during run
        timestamp: ISO format timestamp of run execution
        model: LLM model identifier used
        duration_ms: Total execution time in milliseconds
        enabled_techniques: List of enabled technique names
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    response: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    model: str = "qwen2.5:7b"
    duration_ms: float = 0.0
    enabled_techniques: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert run record to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert run record to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunRecord":
        """Create run record from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "RunRecord":
        """Create run record from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the run for display purposes.

        Returns:
            Dictionary with key run information
        """
        return {
            "id": self.id,
            "query_preview": self.query[:100] + "..."
            if len(self.query) > 100
            else self.query,
            "timestamp": self.timestamp,
            "model": self.model,
            "duration_ms": self.duration_ms,
            "enabled_techniques": self.enabled_techniques,
            "key_metrics": {
                k: v
                for k, v in self.metrics.items()
                if k in ["latency_ms", "token_count", "relevance_score", "accuracy"]
            },
        }


class RunHistoryManager:
    """
    Manager for storing and retrieving agent run history.

    Maintains a persistent history of the last N runs with thread-safe
    operations and atomic file writes.

    Attributes:
        history_file: Path to the JSON file storing run history
        max_runs: Maximum number of runs to keep in history (default: 8)
        _lock: Threading lock for thread-safe operations
    """

    def __init__(self, history_file: str = "data/run_history.json", max_runs: int = 8):
        """
        Initialize run history manager.

        Args:
            history_file: Path to history file
            max_runs: Maximum number of runs to keep
        """
        self.history_file = Path(history_file)
        self.max_runs = max_runs
        self._lock = threading.Lock()

        # Ensure data directory exists
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize file if it doesn't exist
        if not self.history_file.exists():
            self._write_history([])

    @contextmanager
    def _file_lock(self):
        """Context manager for thread-safe file operations."""
        self._lock.acquire()
        try:
            yield
        finally:
            self._lock.release()

    def _read_history(self) -> List[RunRecord]:
        """
        Read run history from file.

        Returns:
            List of RunRecord objects
        """
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [RunRecord.from_dict(record) for record in data]
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _write_history(self, runs: List[RunRecord]) -> None:
        """
        Write run history to file atomically.

        Args:
            runs: List of RunRecord objects to write
        """
        # Write to temporary file first
        temp_file = self.history_file.with_suffix(".json.tmp")

        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                data = [run.to_dict() for run in runs]
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_file.replace(self.history_file)
        except (OSError, IOError) as e:
            # Clean up temp file if write failed
            if temp_file.exists():
                temp_file.unlink()
            raise IOError(f"Failed to write run history: {e}") from e

    def add_run(self, run: RunRecord) -> None:
        """
        Add a new run to history.

        Maintains a rolling window of the last max_runs runs.

        Args:
            run: RunRecord to add
        """
        with self._file_lock():
            runs = self._read_history()

            # Add new run at the beginning (most recent first)
            runs.insert(0, run)

            # Keep only the last max_runs
            runs = runs[: self.max_runs]

            self._write_history(runs)

    def get_recent_runs(self, limit: Optional[int] = None) -> List[RunRecord]:
        """
        Get recent runs from history.

        Args:
            limit: Maximum number of runs to return (None for all)

        Returns:
            List of RunRecord objects, most recent first
        """
        with self._file_lock():
            runs = self._read_history()

            if limit is not None:
                runs = runs[:limit]

            return runs

    def get_run_by_id(self, run_id: str) -> Optional[RunRecord]:
        """
        Get a specific run by ID.

        Args:
            run_id: UUID of the run to retrieve

        Returns:
            RunRecord if found, None otherwise
        """
        with self._file_lock():
            runs = self._read_history()

            for run in runs:
                if run.id == run_id:
                    return run

            return None

    def get_runs_by_query(
        self, query_text: str, case_sensitive: bool = False
    ) -> List[RunRecord]:
        """
        Get runs that match a query text.

        Args:
            query_text: Text to search for in queries
            case_sensitive: Whether to perform case-sensitive search

        Returns:
            List of matching RunRecord objects
        """
        with self._file_lock():
            runs = self._read_history()

            if not case_sensitive:
                query_text = query_text.lower()
                return [run for run in runs if query_text in run.query.lower()]
            else:
                return [run for run in runs if query_text in run.query]

    def get_runs_by_technique(self, technique: str) -> List[RunRecord]:
        """
        Get runs that used a specific technique.

        Args:
            technique: Name of the technique (e.g., 'rag', 'compression')

        Returns:
            List of RunRecord objects that used the technique
        """
        with self._file_lock():
            runs = self._read_history()
            return [run for run in runs if technique in run.enabled_techniques]

    def get_runs_by_model(self, model: str) -> List[RunRecord]:
        """
        Get runs that used a specific model.

        Args:
            model: Model identifier

        Returns:
            List of RunRecord objects that used the model
        """
        with self._file_lock():
            runs = self._read_history()
            return [run for run in runs if run.model == model]

    def clear_history(self) -> None:
        """Clear all run history."""
        with self._file_lock():
            self._write_history([])

    def delete_run(self, run_id: str) -> bool:
        """
        Delete a specific run from history.

        Args:
            run_id: UUID of the run to delete

        Returns:
            True if run was deleted, False if not found
        """
        with self._file_lock():
            runs = self._read_history()

            # Find and remove the run
            initial_count = len(runs)
            runs = [run for run in runs if run.id != run_id]

            if len(runs) < initial_count:
                self._write_history(runs)
                return True

            return False

    def get_history_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the run history.

        Returns:
            Dictionary with history statistics
        """
        with self._file_lock():
            runs = self._read_history()

            if not runs:
                return {
                    "total_runs": 0,
                    "models_used": [],
                    "techniques_used": [],
                    "date_range": None,
                }

            # Collect statistics
            models = set(run.model for run in runs)
            all_techniques = set()
            for run in runs:
                all_techniques.update(run.enabled_techniques)

            timestamps = [_parse_timestamp(run.timestamp) for run in runs]
            min_time = min(timestamps)
            max_time = max(timestamps)

            # Calculate average metrics
            total_duration = sum(run.duration_ms for run in runs)
            avg_duration = total_duration / len(runs) if runs else 0

            return {
                "total_runs": len(runs),
                "models_used": list(models),
                "techniques_used": list(all_techniques),
                "date_range": {
                    "earliest": min_time.isoformat(),
                    "latest": max_time.isoformat(),
                },
                "average_duration_ms": avg_duration,
            }

    def export_to_json(self, output_file: Optional[str] = None) -> str:
        """
        Export run history to JSON file or string.

        Args:
            output_file: Optional path to output file

        Returns:
            JSON string of the history
        """
        with self._file_lock():
            runs = self._read_history()
            data = [run.to_dict() for run in runs]
            json_str = json.dumps(data, indent=2, ensure_ascii=False)

            if output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(json_str)

            return json_str

    def import_from_json(self, json_str: str, merge: bool = False) -> None:
        """
        Import run history from JSON string.

        Args:
            json_str: JSON string containing run history
            merge: If True, merge with existing history; if False, replace
        """
        with self._file_lock():
            new_data = json.loads(json_str)
            new_runs = [RunRecord.from_dict(record) for record in new_data]

            if merge:
                existing_runs = self._read_history()
                # Merge, keeping unique runs by ID
                run_dict = {run.id: run for run in existing_runs}
                for run in new_runs:
                    run_dict[run.id] = run

                # Sort by timestamp, most recent first
                # Parse timestamps to datetime objects for proper chronological ordering
                all_runs = list(run_dict.values())

                all_runs.sort(key=lambda run: _parse_timestamp(run.timestamp), reverse=True)
                # Keep only max_runs
                all_runs = all_runs[: self.max_runs]
                self._write_history(all_runs)
            else:
                # Replace completely
                new_runs = new_runs[: self.max_runs]
                self._write_history(new_runs)


# Global run history manager instance
_global_history_manager: Optional[RunHistoryManager] = None


def get_run_history_manager(
    history_file: str = "data/run_history.json", max_runs: int = 8
) -> RunHistoryManager:
    """
    Get global run history manager instance (singleton pattern).

    Args:
        history_file: Path to history file
        max_runs: Maximum number of runs to keep

    Returns:
        Global RunHistoryManager instance
    """
    global _global_history_manager
    if _global_history_manager is None:
        _global_history_manager = RunHistoryManager(
            history_file=history_file, max_runs=max_runs
        )
    return _global_history_manager


def reset_run_history_manager() -> None:
    """Reset the global run history manager (useful for testing)."""
    global _global_history_manager
    _global_history_manager = None
