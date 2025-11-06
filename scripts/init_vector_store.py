#!/usr/bin/env python3
"""
Initialize Vector Store with Test Documents

This script initializes the ChromaDB vector store and ingests
the test documents from data/knowledge_base/
"""

import sys
import os
from pathlib import Path

# Add project root to path (dynamically determine it)
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

def initialize_vector_store():
    """
    Initialize the project's ChromaDB vector store and ingest test documents from data/knowledge_base.
    
    Initializes the ChromaDB vector store (via src.retrieval.vector_store.get_vector_store), and if the store is empty:
    loads .txt and .md files from data/knowledge_base, chunks each document using a fixed strategy (chunk_size=512, chunk_overlap=50),
    adds all chunks to the vector store, and prints verification statistics and quick API usage hints.
    
    Exits the process with status 1 on ImportError (missing dependencies) or on other unexpected errors.
    """
    print("="*60)
    print("Initializing Vector Store for Phase 3 RAG")
    print("="*60)

    try:
        # Import after path is set
        from src.retrieval.vector_store import get_vector_store
        from src.retrieval.document_loader import load_documents_from_directory
        from src.retrieval.chunking import chunk_document

        print("\n1. Initializing ChromaDB...")
        vector_store = get_vector_store()

        # Check if already populated
        count = vector_store.count()
        if count > 0:
            print(f"   ✓ Vector store already contains {count} documents")
            print("   Skipping initialization (clear store to re-initialize)")
            return

        print("   ✓ ChromaDB initialized successfully")

        # Load test documents
        kb_dir = "data/knowledge_base"
        if not os.path.exists(kb_dir):
            print(f"   ⚠ Knowledge base directory not found: {kb_dir}")
            print("   Skipping document ingestion")
            return

        print(f"\n2. Loading documents from {kb_dir}...")
        documents = load_documents_from_directory(
            directory=kb_dir,
            recursive=True,
            file_extensions=[".txt", ".md"]
        )

        if not documents:
            print("   ⚠ No documents found to ingest")
            return

        print(f"   ✓ Loaded {len(documents)} documents")

        # Chunk documents
        print("\n3. Chunking documents...")
        all_chunks = []
        for doc in documents:
            chunks = chunk_document(
                text=doc.content,
                metadata=doc.metadata,
                strategy="fixed",
                chunk_size=512,
                chunk_overlap=50
            )
            all_chunks.extend(chunks)
            print(f"   - {doc.metadata.get('filename')}: {len(chunks)} chunks")

        print(f"   ✓ Created {len(all_chunks)} total chunks")

        # Add to vector store
        print("\n4. Adding chunks to vector store...")
        chunk_texts = [chunk.text for chunk in all_chunks]
        chunk_metadatas = [chunk.metadata for chunk in all_chunks]

        ids = vector_store.add_documents(
            texts=chunk_texts,
            metadatas=chunk_metadatas
        )

        print(f"   ✓ Added {len(ids)} chunks to vector store")

        # Verify
        print("\n5. Verifying vector store...")
        stats = vector_store.get_stats()
        print(f"   ✓ Total documents: {stats['total_documents']}")
        print(f"   ✓ Unique sources: {stats['unique_sources']}")
        print(f"   ✓ Storage size: {stats['storage_size_mb']:.2f} MB")

        print("\n" + "="*60)
        print("✅ Vector Store Initialization Complete!")
        print("="*60)
        print("\nYou can now:")
        print("  - Test search: curl 'http://localhost:8000/api/vector-store/search?query=Python'")
        print("  - View stats: curl http://localhost:8000/api/vector-store/stats")
        print("  - Enable RAG in the chat UI and ask questions!")
        print()

    except ImportError as e:
        print(f"\n✗ Import Error: {e}")
        print("\nMissing dependencies? Run:")
        print("  pip install chromadb sentence-transformers tiktoken")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    initialize_vector_store()