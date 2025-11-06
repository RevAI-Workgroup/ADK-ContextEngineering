#!/usr/bin/env python3
"""
Test script to verify that raw tool call XML is filtered from responses.
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_tool_call_filtering():
    """Test that raw <tool>...</tool> XML is filtered from responses."""

    print("=" * 60)
    print("Testing Tool Call Filtering")
    print("=" * 60)

    # Send a message that will trigger the RAG tool
    print("\n[TEST] Sending message that should trigger RAG tool...")
    config = {
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

    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "message": "Can you tell me who is Riri in the knowledge base?",
            "config": config,
            "include_thinking": False
        },
        timeout=60
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Response received")
        print(f"  Model: {data.get('model')}")

        response_text = data.get('response', '')
        print(f"\n  Response text ({len(response_text)} chars):")
        print(f"  {response_text}")

        # Check if raw tool calls appear in response
        if '<tool>' in response_text or '</tool>' in response_text:
            print("\n  ✗ FAIL: Raw tool call XML found in response!")
            print("  The filtering is not working correctly.")
        else:
            print("\n  ✓ PASS: No raw tool call XML in response")
            print("  The filtering is working correctly!")

        # Show tool calls if any
        if data.get('tool_calls'):
            print(f"\n  Tool calls detected: {len(data['tool_calls'])}")
            for tool in data['tool_calls']:
                print(f"    - {tool.get('name', 'unknown')}")
                if 'result' in tool:
                    result_preview = str(tool['result'])[:100]
                    print(f"      Result preview: {result_preview}...")
        else:
            print(f"\n  No tool calls detected in metadata")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  {response.text}")

    print("\n" + "=" * 60)
    print("Testing Complete")
    print("=" * 60)

if __name__ == "__main__":
    try:
        # Check if server is running
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code != 200:
            print("Error: Server is not running or not healthy")
            exit(1)

        test_tool_call_filtering()
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to server at", BASE_URL)
        print("Please start the server first with:")
        print("  python3 -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000")
        exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
