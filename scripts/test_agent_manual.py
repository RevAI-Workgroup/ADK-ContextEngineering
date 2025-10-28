#!/usr/bin/env python3
"""
Manual test script for ADK agent.

This script verifies the agent configuration and displays info.
For interactive testing, use: adk run context_engineering_agent

This validates that the agent is properly configured and ready to use.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from context_engineering_agent import root_agent


def test_agent():
    """Verify the ADK agent configuration."""

    print("="*70)
    print("ADK Agent Configuration Test")
    print("="*70)
    print()

    try:
        # Display agent info
        print("✓ Agent loaded successfully!")
        print()

        print("Agent Information:")
        print(f"  Name: {root_agent.name}")
        print(f"  Model: {root_agent.model.model}")
        print(f"  Tools: {len(root_agent.tools)}")
        print()

        # Display available tools
        print("Available Tools:")
        for tool in root_agent.tools:
            tool_name = tool.__name__ if callable(tool) else str(tool)
            doc = tool.__doc__ if hasattr(tool, '__doc__') and tool.__doc__ else "No description"
            first_line = doc.strip().split('\n')[0] if doc else "No description"
            print(f"  - {tool_name}: {first_line}")
        print()

        print("="*70)
        print("Configuration Valid!")
        print("="*70)
        print()
        print("To test the agent interactively, run:")
        print("  adk run context_engineering_agent")
        print()
        print("Example queries:")
        print('  echo "What is 15 multiplied by 7?" | adk run context_engineering_agent')
        print('  echo "Analyze this text: Hello world" | adk run context_engineering_agent')
        print('  echo "What time is it in Asia/Tokyo?" | adk run context_engineering_agent')
        print()

        return 0

    except Exception as e:
        print(f"\n✗ Agent load failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(test_agent())
