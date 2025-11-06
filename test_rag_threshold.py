#!/usr/bin/env python3
"""
Direct test of RAG search tool threshold.
"""
from src.core.tools.rag_search import search_knowledge_base

print("=" * 60)
print("Testing RAG Search Tool Threshold")
print("=" * 60)

# Test search for "Riri"
print("\n[TEST] Searching for 'Riri' in knowledge base...")
result = search_knowledge_base("Riri", top_k=5)

print(f"\nResult:\n{result}")

# Check if it found documents
if "No relevant documents found" in result:
    print("\n✗ FAIL: No documents found (threshold might be too high)")
elif "knowledge base is empty" in result:
    print("\n✗ FAIL: Knowledge base is empty")
else:
    print("\n✓ PASS: Found documents!")
    # Count how many documents
    import re
    doc_count = len(re.findall(r"--- Document \d+ ---", result))
    print(f"  Documents returned: {doc_count}")

print("\n" + "=" * 60)
