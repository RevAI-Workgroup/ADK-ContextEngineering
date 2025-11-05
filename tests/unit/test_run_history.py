"""
Unit tests for run history management system.
"""

import pytest
import json
import tempfile
import time
from pathlib import Path
from datetime import datetime

from src.memory.run_history import (
    RunRecord,
    RunHistoryManager,
    get_run_history_manager,
    reset_run_history_manager,
)


class TestRunRecord:
    """Test RunRecord dataclass."""
    
    def test_default_creation(self):
        """Test creating run record with defaults."""
        record = RunRecord()
        
        assert record.id  # Should have a UUID
        assert record.query == ""
        assert record.config == {}
        assert record.response == ""
        assert record.metrics == {}
        assert record.timestamp  # Should have timestamp
        assert record.model == "qwen2.5:7b"
        assert record.duration_ms == 0.0
        assert record.enabled_techniques == []
    
    def test_custom_creation(self):
        """Test creating run record with custom values."""
        record = RunRecord(
            query="What is RAG?",
            response="RAG stands for Retrieval-Augmented Generation",
            model="qwen2.5:3b",
            duration_ms=1500.0,
            enabled_techniques=["rag", "compression"]
        )
        
        assert record.query == "What is RAG?"
        assert record.model == "qwen2.5:3b"
        assert record.duration_ms == 1500.0
        assert len(record.enabled_techniques) == 2
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        record = RunRecord(
            query="Test query",
            response="Test response"
        )
        
        data = record.to_dict()
        assert isinstance(data, dict)
        assert data['query'] == "Test query"
        assert data['response'] == "Test response"
        assert 'id' in data
        assert 'timestamp' in data
    
    def test_to_json(self):
        """Test conversion to JSON."""
        record = RunRecord(query="Test")
        json_str = record.to_json()
        
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data['query'] == "Test"
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            'id': 'test-id-123',
            'query': 'Test query',
            'config': {'rag': {'enabled': True}},
            'response': 'Test response',
            'metrics': {'latency_ms': 100},
            'timestamp': '2024-01-01T00:00:00',
            'model': 'qwen2.5:7b',
            'duration_ms': 150.0,
            'enabled_techniques': ['rag']
        }
        
        record = RunRecord.from_dict(data)
        assert record.id == 'test-id-123'
        assert record.query == 'Test query'
        assert record.response == 'Test response'
        assert record.enabled_techniques == ['rag']
    
    def test_from_json(self):
        """Test creation from JSON string."""
        json_str = json.dumps({
            'id': 'test-123',
            'query': 'Test',
            'config': {},
            'response': 'Response',
            'metrics': {},
            'timestamp': '2024-01-01T00:00:00',
            'model': 'qwen2.5:7b',
            'duration_ms': 100.0,
            'enabled_techniques': []
        })
        
        record = RunRecord.from_json(json_str)
        assert record.id == 'test-123'
        assert record.query == 'Test'
    
    def test_get_summary(self):
        """Test getting run summary."""
        record = RunRecord(
            query="What is context engineering?",
            duration_ms=1234.5,
            metrics={
                'latency_ms': 1200,
                'token_count': 500,
                'relevance_score': 0.85,
                'other_metric': 123
            },
            enabled_techniques=['rag', 'compression']
        )
        
        summary = record.get_summary()
        
        assert 'id' in summary
        assert 'query_preview' in summary
        assert 'timestamp' in summary
        assert summary['duration_ms'] == 1234.5
        assert summary['enabled_techniques'] == ['rag', 'compression']
        assert 'key_metrics' in summary
        assert summary['key_metrics']['token_count'] == 500
        assert 'other_metric' not in summary['key_metrics']
    
    def test_long_query_preview(self):
        """Test query preview truncation for long queries."""
        long_query = "A" * 200
        record = RunRecord(query=long_query)
        
        summary = record.get_summary()
        assert len(summary['query_preview']) == 103  # 100 + "..."
        assert summary['query_preview'].endswith("...")


class TestRunHistoryManager:
    """Test RunHistoryManager class."""
    
    @pytest.fixture
    def temp_history_file(self):
        """Create temporary history file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def manager(self, temp_history_file):
        """Create a run history manager with temporary file."""
        return RunHistoryManager(history_file=temp_history_file, max_runs=8)
    
    def test_initialization(self, temp_history_file):
        """Test manager initialization."""
        manager = RunHistoryManager(history_file=temp_history_file, max_runs=5)
        
        assert manager.history_file == Path(temp_history_file)
        assert manager.max_runs == 5
        assert manager.history_file.exists()
    
    def test_add_run(self, manager):
        """Test adding a run to history."""
        record = RunRecord(query="Test query 1", response="Test response 1")
        manager.add_run(record)
        
        runs = manager.get_recent_runs()
        assert len(runs) == 1
        assert runs[0].query == "Test query 1"
    
    def test_add_multiple_runs(self, manager):
        """Test adding multiple runs."""
        for i in range(5):
            record = RunRecord(query=f"Query {i}", response=f"Response {i}")
            manager.add_run(record)
            time.sleep(0.01)  # Small delay to ensure different timestamps
        
        runs = manager.get_recent_runs()
        assert len(runs) == 5
        # Most recent first
        assert runs[0].query == "Query 4"
        assert runs[-1].query == "Query 0"
    
    def test_max_runs_limit(self, temp_history_file):
        """Test that history respects max_runs limit."""
        manager = RunHistoryManager(history_file=temp_history_file, max_runs=3)
        
        for i in range(5):
            record = RunRecord(query=f"Query {i}")
            manager.add_run(record)
        
        runs = manager.get_recent_runs()
        assert len(runs) == 3
        # Should keep most recent 3
        assert runs[0].query == "Query 4"
        assert runs[1].query == "Query 3"
        assert runs[2].query == "Query 2"
    
    def test_get_recent_runs_with_limit(self, manager):
        """Test getting recent runs with limit."""
        for i in range(5):
            record = RunRecord(query=f"Query {i}")
            manager.add_run(record)
        
        runs = manager.get_recent_runs(limit=3)
        assert len(runs) == 3
        assert runs[0].query == "Query 4"
    
    def test_get_run_by_id(self, manager):
        """Test getting a specific run by ID."""
        record1 = RunRecord(query="Query 1")
        record2 = RunRecord(query="Query 2")
        
        manager.add_run(record1)
        manager.add_run(record2)
        
        retrieved = manager.get_run_by_id(record1.id)
        assert retrieved is not None
        assert retrieved.query == "Query 1"
        assert retrieved.id == record1.id
    
    def test_get_run_by_id_not_found(self, manager):
        """Test getting run with non-existent ID."""
        result = manager.get_run_by_id("nonexistent-id")
        assert result is None
    
    def test_get_runs_by_query(self, manager):
        """Test searching runs by query text."""
        manager.add_run(RunRecord(query="What is RAG?"))
        manager.add_run(RunRecord(query="How does compression work?"))
        manager.add_run(RunRecord(query="Explain RAG in detail"))
        
        rag_runs = manager.get_runs_by_query("RAG")
        assert len(rag_runs) == 2
        
        compression_runs = manager.get_runs_by_query("compression")
        assert len(compression_runs) == 1
    
    def test_get_runs_by_query_case_insensitive(self, manager):
        """Test case-insensitive query search."""
        manager.add_run(RunRecord(query="What is RAG?"))
        manager.add_run(RunRecord(query="What is rag?"))
        
        runs = manager.get_runs_by_query("rag", case_sensitive=False)
        assert len(runs) == 2
        
        runs_sensitive = manager.get_runs_by_query("rag", case_sensitive=True)
        assert len(runs_sensitive) == 1
    
    def test_get_runs_by_technique(self, manager):
        """Test getting runs by technique."""
        manager.add_run(RunRecord(
            query="Q1",
            enabled_techniques=["rag"]
        ))
        manager.add_run(RunRecord(
            query="Q2",
            enabled_techniques=["rag", "compression"]
        ))
        manager.add_run(RunRecord(
            query="Q3",
            enabled_techniques=["compression"]
        ))
        
        rag_runs = manager.get_runs_by_technique("rag")
        assert len(rag_runs) == 2
        
        compression_runs = manager.get_runs_by_technique("compression")
        assert len(compression_runs) == 2
    
    def test_get_runs_by_model(self, manager):
        """Test getting runs by model."""
        manager.add_run(RunRecord(query="Q1", model="qwen2.5:7b"))
        manager.add_run(RunRecord(query="Q2", model="qwen2.5:3b"))
        manager.add_run(RunRecord(query="Q3", model="qwen2.5:7b"))
        
        runs_7b = manager.get_runs_by_model("qwen2.5:7b")
        assert len(runs_7b) == 2
        
        runs_3b = manager.get_runs_by_model("qwen2.5:3b")
        assert len(runs_3b) == 1
    
    def test_clear_history(self, manager):
        """Test clearing all history."""
        for i in range(3):
            manager.add_run(RunRecord(query=f"Query {i}"))
        
        assert len(manager.get_recent_runs()) == 3
        
        manager.clear_history()
        assert len(manager.get_recent_runs()) == 0
    
    def test_delete_run(self, manager):
        """Test deleting a specific run."""
        record1 = RunRecord(query="Query 1")
        record2 = RunRecord(query="Query 2")
        
        manager.add_run(record1)
        manager.add_run(record2)
        
        assert len(manager.get_recent_runs()) == 2
        
        deleted = manager.delete_run(record1.id)
        assert deleted is True
        
        runs = manager.get_recent_runs()
        assert len(runs) == 1
        assert runs[0].id == record2.id
    
    def test_delete_run_not_found(self, manager):
        """Test deleting non-existent run."""
        deleted = manager.delete_run("nonexistent-id")
        assert deleted is False
    
    def test_get_history_stats_empty(self, manager):
        """Test getting stats for empty history."""
        stats = manager.get_history_stats()
        
        assert stats['total_runs'] == 0
        assert stats['models_used'] == []
        assert stats['techniques_used'] == []
        assert stats['date_range'] is None
    
    def test_get_history_stats(self, manager):
        """Test getting history statistics."""
        manager.add_run(RunRecord(
            query="Q1",
            model="qwen2.5:7b",
            duration_ms=100,
            enabled_techniques=["rag"]
        ))
        manager.add_run(RunRecord(
            query="Q2",
            model="qwen2.5:3b",
            duration_ms=200,
            enabled_techniques=["rag", "compression"]
        ))
        
        stats = manager.get_history_stats()
        
        assert stats['total_runs'] == 2
        assert len(stats['models_used']) == 2
        assert 'qwen2.5:7b' in stats['models_used']
        assert 'qwen2.5:3b' in stats['models_used']
        assert 'rag' in stats['techniques_used']
        assert 'compression' in stats['techniques_used']
        assert stats['average_duration_ms'] == 150.0
        assert 'date_range' in stats
    
    def test_export_to_json(self, manager, temp_history_file):
        """Test exporting history to JSON."""
        manager.add_run(RunRecord(query="Q1"))
        manager.add_run(RunRecord(query="Q2"))
        
        json_str = manager.export_to_json()
        
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert len(data) == 2
        assert data[0]['query'] == "Q2"  # Most recent first
    
    def test_export_to_file(self, manager):
        """Test exporting history to file."""
        manager.add_run(RunRecord(query="Q1"))
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name
        
        try:
            manager.export_to_json(output_file=output_file)
            
            assert Path(output_file).exists()
            with open(output_file, 'r') as f:
                data = json.load(f)
                assert len(data) == 1
                assert data[0]['query'] == "Q1"
        finally:
            Path(output_file).unlink(missing_ok=True)
    
    def test_import_from_json_replace(self, manager):
        """Test importing history (replace mode)."""
        # Add some existing runs
        manager.add_run(RunRecord(query="Existing"))
        
        # Import new runs (replace)
        new_data = [
            RunRecord(query="Imported 1").to_dict(),
            RunRecord(query="Imported 2").to_dict(),
        ]
        json_str = json.dumps(new_data)
        
        manager.import_from_json(json_str, merge=False)
        
        runs = manager.get_recent_runs()
        assert len(runs) == 2
        assert runs[0].query == "Imported 1"
        assert runs[1].query == "Imported 2"
    
    def test_import_from_json_merge(self, manager):
        """Test importing history (merge mode)."""
        existing = RunRecord(query="Existing")
        manager.add_run(existing)
        
        # Import with merge
        new_data = [
            RunRecord(query="Imported").to_dict(),
        ]
        json_str = json.dumps(new_data)
        
        manager.import_from_json(json_str, merge=True)
        
        runs = manager.get_recent_runs()
        assert len(runs) == 2
    
    def test_thread_safety(self, manager):
        """Test thread-safe operations (basic check)."""
        import threading
        
        def add_runs():
            for i in range(10):
                manager.add_run(RunRecord(query=f"Query {i}"))
        
        threads = [threading.Thread(target=add_runs) for _ in range(3)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have max_runs (8) in history
        runs = manager.get_recent_runs()
        assert len(runs) == 8


class TestGlobalManager:
    """Test global run history manager functions."""
    
    def test_get_run_history_manager_singleton(self):
        """Test that get_run_history_manager returns singleton."""
        reset_run_history_manager()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            manager1 = get_run_history_manager(history_file=temp_path)
            manager2 = get_run_history_manager(history_file=temp_path)
            
            assert manager1 is manager2
        finally:
            reset_run_history_manager()
            Path(temp_path).unlink(missing_ok=True)
    
    def test_reset_run_history_manager(self):
        """Test resetting global manager."""
        reset_run_history_manager()
        
        manager1 = get_run_history_manager()
        reset_run_history_manager()
        manager2 = get_run_history_manager()
        
        assert manager1 is not manager2

