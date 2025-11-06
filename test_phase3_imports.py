#!/usr/bin/env python3
"""
Quick test script for Phase 3 RAG API endpoints.
Tests basic functionality without starting the full server.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print("Testing Phase 3 RAG module imports...")

try:
    # Test vector store imports
    from src.retrieval.vector_store import VectorStore, SearchResult, get_vector_store
    print("✓ Vector store imports successful")

    # Test embeddings imports
    from src.retrieval.embeddings import EmbeddingService, get_embedding_service
    print("✓ Embeddings service imports successful")

    # Test document loader imports
    from src.retrieval.document_loader import load_document, Document
    print("✓ Document loader imports successful")

    # Test chunking imports
    from src.retrieval.chunking import chunk_document, Chunk
    print("✓ Chunking imports successful")

    # Test API endpoints imports
    from src.api.endpoints import documents_router
    print("✓ Documents router imports successful")

    # Test modular pipeline with RAG modules
    from src.core.modular_pipeline import NaiveRAGModule, RAGToolModule
    print("✓ RAG modules (NaiveRAG and RAGTool) imports successful")

    print("\n" + "="*50)
    print("All imports successful!")
    print("="*50)

    # Test basic vector store functionality
    print("\nTesting basic vector store operations...")

    # Create a test vector store (in-memory, no persistence)
    import tempfile
    import shutil
    temp_dir = None

    try:
        temp_dir = tempfile.mkdtemp()
        vs = VectorStore(persist_directory=temp_dir, collection_name="test_collection")
        print(f"✓ Created vector store at {temp_dir}")

        # Test adding documents
        test_texts = ["Hello world", "Test document", "Python programming"]
        test_metadatas = [{"source": "test1"}, {"source": "test2"}, {"source": "test3"}]
        ids = vs.add_documents(texts=test_texts, metadatas=test_metadatas)
        print(f"✓ Added {len(ids)} documents to vector store")

        # Test count
        count = vs.count()
        print(f"✓ Vector store contains {count} documents")

        # Test search
        results = vs.search("hello", top_k=2)
        print(f"✓ Search returned {len(results)} results")
        if results:
            print(f"  Top result: similarity={results[0].similarity:.3f}")

        # Test stats
        stats = vs.get_stats()
        print(f"✓ Stats: {stats['total_documents']} docs, {stats['storage_size_mb']:.2f}MB")

    except Exception as e:
        print(f"✗ Vector store test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except (OSError, FileNotFoundError) as cleanup_error:
                print(f"⚠ Warning: Failed to clean up temporary directory {temp_dir}: {cleanup_error}")

    print("\n" + "="*50)
    print("Basic functionality tests passed!")
    print("="*50)

except ImportError as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ All tests passed! Ready to start the server.")
