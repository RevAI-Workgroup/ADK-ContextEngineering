"""
Test script for Phase 2 API endpoints.

Tests the new configuration and run history endpoints without
starting the full server.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.context_config import (
    ContextEngineeringConfig,
    ConfigPreset,
    get_default_config,
    get_preset_configs,
    get_preset_names
)
from src.core.modular_pipeline import ContextPipeline
from src.memory.run_history import RunHistoryManager, RunRecord


def test_configuration_system():
    """Test the configuration system."""
    print("=" * 60)
    print("Testing Configuration System")
    print("=" * 60)
    
    # Test default config
    print("\n1. Testing default configuration...")
    default_config = get_default_config()
    print(f"   Default config created: {len(default_config.get_enabled_techniques())} techniques enabled")
    assert len(default_config.get_enabled_techniques()) == 0, "Default should have no techniques enabled"
    print("   ✓ Default config has all techniques disabled")
    
    # Test presets
    print("\n2. Testing configuration presets...")
    preset_names = get_preset_names()
    print(f"   Available presets: {', '.join(preset_names)}")
    assert len(preset_names) == 4, "Should have 4 presets"
    
    for preset_name in preset_names:
        preset = ConfigPreset(preset_name)
        config = ContextEngineeringConfig.from_preset(preset)
        techniques = config.get_enabled_techniques()
        print(f"   {preset_name}: {len(techniques)} techniques - {', '.join(techniques) if techniques else 'none'}")
    print("   ✓ All presets loaded successfully")
    
    # Test validation
    print("\n3. Testing configuration validation...")
    valid_config = ContextEngineeringConfig()
    valid_config.rag.enabled = True
    errors = valid_config.validate()
    assert len(errors) == 0, f"Valid config should have no errors, got: {errors}"
    print("   ✓ Valid configuration passes validation")
    
    # Test invalid config
    invalid_config = ContextEngineeringConfig()
    invalid_config.rag.enabled = True
    invalid_config.rag.chunk_size = -100  # Invalid
    errors = invalid_config.validate()
    assert len(errors) > 0, "Invalid config should have errors"
    print(f"   ✓ Invalid configuration caught {len(errors)} error(s)")
    
    # Test serialization
    print("\n4. Testing configuration serialization...")
    config = ContextEngineeringConfig.from_preset(ConfigPreset.BASIC_RAG)
    config_dict = config.to_dict()
    config_restored = ContextEngineeringConfig.from_dict(config_dict)
    
    # Verify RAG configuration fields
    assert config_restored.rag.enabled == config.rag.enabled, "RAG enabled mismatch"
    assert config_restored.rag.chunk_size == config.rag.chunk_size, "RAG chunk_size mismatch"
    assert config_restored.rag.chunk_overlap == config.rag.chunk_overlap, "RAG chunk_overlap mismatch"
    assert config_restored.rag.top_k == config.rag.top_k, "RAG top_k mismatch"
    assert config_restored.rag.similarity_threshold == config.rag.similarity_threshold, "RAG similarity_threshold mismatch"
    assert config_restored.rag.embedding_model == config.rag.embedding_model, "RAG embedding_model mismatch"
    
    # Verify other top-level config fields
    assert config_restored.model == config.model, "Model mismatch"
    assert config_restored.max_context_tokens == config.max_context_tokens, "Max context tokens mismatch"
    
    print(f"   ✓ RAG config verified: enabled={config.rag.enabled}, chunk_size={config.rag.chunk_size}, top_k={config.rag.top_k}")
    print("   ✓ Configuration serialization/deserialization works")
    
    print("\n✅ Configuration system tests passed!")


def test_modular_pipeline():
    """Test the modular pipeline."""
    print("\n" + "=" * 60)
    print("Testing Modular Pipeline")
    print("=" * 60)
    
    # Test pipeline creation
    print("\n1. Testing pipeline creation...")
    config = ContextEngineeringConfig()
    pipeline = ContextPipeline(config)
    print(f"   Pipeline created with {len(pipeline.modules)} modules")
    assert len(pipeline.modules) == 6, "Should have 6 modules"
    print("   ✓ Pipeline initialized with all modules")
    
    # Test with no modules enabled
    print("\n2. Testing pipeline with no modules enabled...")
    result = pipeline.process("What is Python?")
    assert result.query == "What is Python?"
    metrics = pipeline.get_aggregated_metrics()
    print(f"   Processed query, execution time: {metrics['total_execution_time_ms']:.2f}ms")
    print(f"   Enabled modules: {len(metrics['enabled_modules'])}")
    assert len(metrics['enabled_modules']) == 0
    print("   ✓ Pipeline works with no modules")
    
    # Test with modules enabled
    print("\n3. Testing pipeline with modules enabled...")
    config.rag.enabled = True
    config.compression.enabled = True
    pipeline.update_config(config)
    
    result = pipeline.process("What is context engineering?")
    metrics = pipeline.get_aggregated_metrics()
    print(f"   Processed query, execution time: {metrics['total_execution_time_ms']:.2f}ms")
    print(f"   Enabled modules: {', '.join(metrics['enabled_modules'])}")
    assert "rag" in metrics['enabled_modules']
    assert "compression" in metrics['enabled_modules']
    print("   ✓ Pipeline works with modules enabled")
    
    # Test full stack
    print("\n4. Testing pipeline with full stack...")
    full_config = ContextEngineeringConfig.from_preset(ConfigPreset.FULL_STACK)
    pipeline.update_config(full_config)
    
    result = pipeline.process("Test query")
    metrics = pipeline.get_aggregated_metrics()
    print(f"   Enabled modules ({len(metrics['enabled_modules'])}): {', '.join(metrics['enabled_modules'])}")
    assert len(metrics['enabled_modules']) == 6
    print("   ✓ Full stack pipeline works")
    
    print("\n✅ Modular pipeline tests passed!")


def test_run_history():
    """Test the run history system."""
    print("\n" + "=" * 60)
    print("Testing Run History System")
    print("=" * 60)
    
    # Use a test file
    import tempfile
    import os
    
    test_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    test_file.close()
    test_file_path = test_file.name
    
    try:
        # Test history manager creation
        print("\n1. Testing history manager creation...")
        manager = RunHistoryManager(history_file=test_file_path, max_runs=5)
        print(f"   History manager created with max_runs=5")
        print("   ✓ History manager initialized")
        
        # Test adding runs
        print("\n2. Testing adding runs...")
        for i in range(3):
            run = RunRecord(
                query=f"Test query {i}",
                response=f"Test response {i}",
                model="qwen2.5:7b",
                duration_ms=100 + i * 10,
                enabled_techniques=["rag"] if i % 2 == 0 else ["compression"]
            )
            manager.add_run(run)
        
        recent_runs = manager.get_recent_runs()
        print(f"   Added 3 runs, retrieved {len(recent_runs)} runs")
        assert len(recent_runs) == 3
        print("   ✓ Run history storage works")
        
        # Test filtering
        print("\n3. Testing run filtering...")
        rag_runs = manager.get_runs_by_technique("rag")
        print(f"   Runs with RAG: {len(rag_runs)}")
        assert len(rag_runs) == 2  # Runs 0 and 2
        
        query_runs = manager.get_runs_by_query("query 1")
        print(f"   Runs matching 'query 1': {len(query_runs)}")
        assert len(query_runs) == 1
        print("   ✓ Run filtering works")
        
        # Test statistics
        print("\n4. Testing run statistics...")
        stats = manager.get_history_stats()
        print(f"   Total runs: {stats['total_runs']}")
        print(f"   Models used: {', '.join(stats['models_used'])}")
        print(f"   Techniques used: {', '.join(stats['techniques_used'])}")
        print(f"   Average duration: {stats['average_duration_ms']:.2f}ms")
        assert stats['total_runs'] == 3
        print("   ✓ Run statistics work")
        
        # Test clearing history
        print("\n5. Testing clearing history...")
        manager.clear_history()
        recent_runs = manager.get_recent_runs()
        print(f"   After clear: {len(recent_runs)} runs")
        assert len(recent_runs) == 0
        print("   ✓ History clearing works")
        
        print("\n✅ Run history tests passed!")
    
    finally:
        # Clean up test file
        if os.path.exists(test_file_path):
            os.unlink(test_file_path)


def test_integration():
    """Test integration of all Phase 2 components."""
    print("\n" + "=" * 60)
    print("Testing Phase 2 Integration")
    print("=" * 60)
    
    print("\n1. Testing end-to-end flow...")
    
    # Create a configuration
    config = ContextEngineeringConfig.from_preset(ConfigPreset.BASIC_RAG)
    print(f"   Created config with preset: basic_rag")
    
    # Create pipeline
    pipeline = ContextPipeline(config)
    print(f"   Created pipeline")
    
    # Process a query
    query = "What are the benefits of RAG?"
    result = pipeline.process(query)
    print(f"   Processed query: '{query}'")
    
    # Get metrics
    metrics = pipeline.get_aggregated_metrics()
    print(f"   Pipeline metrics: {metrics['total_execution_time_ms']:.2f}ms")
    print(f"   Enabled techniques: {', '.join(metrics['enabled_modules'])}")
    
    # This simulates what would happen in the API endpoint
    print("\n2. Testing API endpoint flow simulation...")
    
    # Simulate receiving config from frontend
    config_dict = config.to_dict()
    print(f"   Frontend sends config: {list(config_dict.keys())}")
    
    # Backend reconstructs config
    backend_config = ContextEngineeringConfig.from_dict(config_dict)
    print(f"   Backend reconstructs config")
    
    # Backend creates pipeline
    backend_pipeline = ContextPipeline(backend_config)
    print(f"   Backend creates pipeline")
    
    # Backend processes query
    backend_result = backend_pipeline.process(query)
    backend_metrics = backend_pipeline.get_aggregated_metrics()
    print(f"   Backend processes query: {backend_metrics['total_execution_time_ms']:.2f}ms")
    
    # Backend would create run record (not saving to file in this test)
    run_record = RunRecord(
        query=query,
        config=config_dict,
        response="Simulated response",
        metrics=backend_metrics,
        model="qwen2.5:7b",
        duration_ms=backend_metrics['total_execution_time_ms'],
        enabled_techniques=config.get_enabled_techniques()
    )
    print(f"   Created run record with ID: {run_record.id[:8]}...")
    
    print("\n✅ Integration tests passed!")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PHASE 2 API TESTS")
    print("=" * 60)
    
    try:
        test_configuration_system()
        test_modular_pipeline()
        test_run_history()
        test_integration()
        
        print("\n" + "=" * 60)
        print("✅ ALL PHASE 2 TESTS PASSED!")
        print("=" * 60)
        print("\nPhase 2 Backend Implementation Complete:")
        print("  ✓ Modular Pipeline Architecture")
        print("  ✓ Configuration System with Presets")
        print("  ✓ Run History Management")
        print("  ✓ Stub Modules (RAG, Compression, Reranking, etc.)")
        print("  ✓ API Integration Ready")
        print("\nNext Steps:")
        print("  • Start backend server: ./start_backend.sh")
        print("  • Test API endpoints via Swagger: http://localhost:8000/docs")
        print("  • Begin Frontend implementation (Phase 2 frontend tasks)")
        print("  • Implement RAG module in Phase 3")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

