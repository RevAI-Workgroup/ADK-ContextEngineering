#!/usr/bin/env python3
"""
Manual test script for ADK agent.

This script allows quick testing of the agent without running full evaluation.
Use this to verify that the agent and tools are working correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.adk_agent import ContextEngineeringAgent
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_agent():
    """Test the ADK agent with various queries."""

    print("="*70)
    print("ADK Agent Manual Test")
    print("="*70)
    print()

    try:
        # Initialize agent
        print("Initializing agent...")
        agent = ContextEngineeringAgent()
        print(f"✓ Agent initialized: {agent}")
        print()

        # Display model info
        model_info = agent.get_model_info()
        print("Model Information:")
        for key, value in model_info.items():
            print(f"  {key}: {value}")
        print()

        # Display available tools
        print("Available Tools:")
        for tool in agent.get_tool_info():
            print(f"  - {tool['name']}: {tool['description']}")
        print()

        # Test queries
        test_cases = [
            {
                "name": "Calculator Tool",
                "query": "What is 15 multiplied by 7?",
                "expected_tool": "calculate"
            },
            {
                "name": "Text Analysis Tool",
                "query": "Analyze this text: The quick brown fox jumps over the lazy dog.",
                "expected_tool": "analyze_text"
            },
            {
                "name": "Time Tool",
                "query": "What's the current time in Asia/Tokyo?",
                "expected_tool": "get_current_time"
            },
            {
                "name": "General Query (no tool)",
                "query": "What is Python?",
                "expected_tool": None
            }
        ]

        for i, test in enumerate(test_cases, 1):
            print(f"\n{'='*70}")
            print(f"Test {i}/{len(test_cases)}: {test['name']}")
            print(f"{'='*70}")
            print(f"\nQuery: {test['query']}")
            print("\nProcessing...\n")

            try:
                response = agent.query(test['query'])
                print(f"Response:\n{response}")

                if test['expected_tool']:
                    print(f"\n✓ Expected tool: {test['expected_tool']}")

            except Exception as e:
                print(f"\n✗ Error: {e}")
                logger.error(f"Test {i} failed", exc_info=True)

        print(f"\n{'='*70}")
        print("All tests completed!")
        print(f"{'='*70}\n")

    except Exception as e:
        print(f"\n✗ Agent initialization failed: {e}")
        logger.error("Failed to initialize agent", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(test_agent())
