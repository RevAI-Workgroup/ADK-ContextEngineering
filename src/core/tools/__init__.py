"""
Tools package for ADK agent.

This package contains all the tools that can be used by the ADK agent.
Each tool is implemented as a simple Python function with proper docstrings
that ADK uses to understand the tool's purpose and parameters.
"""

from .calculator import calculate
from .text_tools import analyze_text, count_words
from .time_tools import get_current_time

__all__ = [
    'calculate',
    'analyze_text',
    'count_words',
    'get_current_time',
]
