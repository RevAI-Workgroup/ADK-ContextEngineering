#!/usr/bin/env python3
"""
Test script to verify RAG-as-tool swapping functionality.
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_tool_swapping():
    """Test that tools are dynamically added/removed based on config."""

    print("=" * 60)
    print("Testing RAG-as-tool Hot-Swapping")
    print("=" * 60)

    # Test 1: Send message with RAG-as-tool DISABLED
    print("\n[TEST 1] Sending message with RAG-as-tool DISABLED...")
    config_disabled = {
        "naive_rag": {"enabled": False},
        "rag_tool": {"enabled": False},
        "compression": {"enabled": False},
        "reranking": {"enabled": False},
        "caching": {"enabled": False},
        "hybrid_search": {"enabled": False},
        "memory": {"enabled": False},
        "model": "qwen2.5:7b",
        "temperature": 0.7
    }

    response1 = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "message": "Hello, what tools do you have available?",
            "config": config_disabled,
            "include_thinking": False
        },
        timeout=30
    )

    if response1.status_code == 200:
        data1 = response1.json()
        print(f"✓ Response received")
        print(f"  Model: {data1.get('model')}")
        response_text = data1.get('response', '')
        print(f"  Response preview: {response_text[:100]}...")
        if data1.get('tool_calls'):
            print(f"  Tool calls: {len(data1['tool_calls'])}")
    else:
        print(f"✗ Error: {response1.status_code}")
        print(f"  {response1.text}")

    # Small delay
    time.sleep(1)

    # Test 2: Send message with RAG-as-tool ENABLED
    print("\n[TEST 2] Sending message with RAG-as-tool ENABLED...")
    config_enabled = {
        "naive_rag": {"enabled": False},
        "rag_tool": {"enabled": True, "top_k": 5, "similarity_threshold": 0.75},
        "compression": {"enabled": False},
        "reranking": {"enabled": False},
        "caching": {"enabled": False},
        "hybrid_search": {"enabled": False},
        "memory": {"enabled": False},
        "model": "qwen2.5:7b",
        "temperature": 0.7
    }

    response2 = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "message": "Search the knowledge base for information about Python",
            "config": config_enabled,
            "include_thinking": False
        },
        timeout=30
    )

    if response2.status_code == 200:
        data2 = response2.json()
        print(f"✓ Response received")
        print(f"  Model: {data2.get('model')}")
        response_text = data2.get('response', '')
        print(f"  Response preview: {response_text[:100]}...")
        if data2.get('tool_calls'):
            print(f"  Tool calls: {len(data2['tool_calls'])}")
            for tool in data2['tool_calls']:
                print(f"    - {tool.get('name', 'unknown')}")
        else:
            print(f"  No tool calls made")
    else:
        print(f"✗ Error: {response2.status_code}")
        print(f"  {response2.text}")
    # Test 3: Send message with RAG-as-tool DISABLED again
    print("\n[TEST 3] Sending message with RAG-as-tool DISABLED again...")

    response3 = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "message": "What is the capital of France?",
            "config": config_disabled,
            "include_thinking": False
        },
        timeout=30
    )

    if response3.status_code == 200:
        data3 = response3.json()
        print(f"✓ Response received")
        print(f"  Model: {data3.get('model')}")
        response_text = data3.get('response', '')
        print(f"  Response preview: {response_text[:100]}...")
        if data3.get('tool_calls'):
            print(f"  Tool calls: {len(data3['tool_calls'])}")
    else:
        print(f"✗ Error: {response3.status_code}")
        print(f"  {response3.text}")

    print("\n" + "=" * 60)
    print("Testing Complete")
    print("=" * 60)
    print("\nCheck the server logs for cache key usage and tool list details")

if __name__ == "__main__":
    try:
        # Check if server is running
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code != 200:
            print("Error: Server is not running or not healthy")
            exit(1)

        test_tool_swapping()
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to server at", BASE_URL)
        print("Please start the server first with:")
        print("  python3 -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000")
        exit(1)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
