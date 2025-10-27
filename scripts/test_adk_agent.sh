#!/bin/bash

# Test script for ADK agent with tool calling verification
# Each test sends a query and checks if the agent responds correctly

set -euo pipefail  # Exit on error, undefined variables, and pipeline failures

echo "========================================================================"
echo "ADK Agent Test Script - Phase 1"
echo "========================================================================"
echo ""

# Prerequisite checks
echo "Checking prerequisites..."

# Check for adk binary
if ! command -v adk &> /dev/null; then
    echo "ERROR: 'adk' command not found in PATH" >&2
    echo "Please install the ADK toolkit or ensure it's in your PATH" >&2
    exit 127
fi
echo "✓ adk binary found: $(command -v adk)"

# Check for context_engineering_agent
if ! adk run --list 2>&1 | grep -F -q "context_engineering_agent"; then
    echo "ERROR: 'context_engineering_agent' not found in available agents" >&2
    echo "Available agents:" >&2
    adk run --list >&2
    exit 1
fi
echo "✓ context_engineering_agent found"
echo ""

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to run a test with validation
# Usage: run_test <test_name> <query> <expected_pattern> [tool_name]
run_test() {
    local test_name="$1"
    local query="$2"
    local expected_pattern="$3"
    local tool_name="$4"

    echo "Test: $test_name"
    echo "Query: $query"
    echo ""

    # Create temporary file to capture output
    local output_file
    output_file=$(mktemp)

    # Run the agent and capture stdout/stderr
    # Temporarily disable pipefail to capture the exit code without exiting
    set +e
    echo "$query" | adk run context_engineering_agent > "$output_file" 2>&1
    local exit_code=$?
    set -e

    # Display the output
    cat "$output_file"
    echo ""

    # Check exit code
    if [ $exit_code -ne 0 ]; then
        echo "❌ FAIL: Agent command exited with code $exit_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        rm -f "$output_file"
        return 1
    fi

    # Check for expected pattern
    if grep -F -q -- "$expected_pattern" "$output_file"; then
        echo "✅ PASS: Found expected pattern: '$expected_pattern'"

        # If tool name provided, verify tool was invoked
        if [ -n "$tool_name" ]; then
            if grep -F -q -- "$tool_name" "$output_file"; then
                echo "✅ PASS: Tool '$tool_name' was invoked"
            else
                echo "❌ FAIL: Tool '$tool_name' was NOT invoked"
                TESTS_FAILED=$((TESTS_FAILED + 1))
                rm -f "$output_file"
                return 1
            fi
        fi

        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "❌ FAIL: Expected pattern '$expected_pattern' not found in output"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        rm -f "$output_file"
        return 1
    fi

    # Cleanup
    rm -f "$output_file"
    echo "------------------------------------------------------------------------"
    echo ""
    return 0
}

# Test 1: Calculator Tool
run_test \
    "Calculator Tool" \
    "What is 15 multiplied by 7?" \
    "105" \
    "Calculator"

# Test 2: Text Analysis Tool
run_test \
    "Text Analysis Tool" \
    "Analyze this text: The quick brown fox jumps over the lazy dog" \
    "word_count" \
    "Text Analysis"

# Test 3: Time Tool
run_test \
    "Time Tool" \
    "What's the current time in Asia/Tokyo?" \
    "Asia/Tokyo" \
    "Time"

# Test 4: General Query (no tool)
run_test \
    "General Query (no tool required)" \
    "What is Python?" \
    "Python" \
    ""

# Summary
echo "========================================================================"
echo "Test Results Summary"
echo "========================================================================"
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -gt 0 ]; then
    echo "❌ Some tests failed!"
    exit 1
else
    echo "✅ All tests passed!"
    exit 0
fi
