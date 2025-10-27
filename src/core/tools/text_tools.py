"""
Text analysis tools for processing and analyzing text.

These tools provide various text statistics and analysis capabilities.
"""

import re
from typing import Any, Dict


def analyze_text(text: str) -> Dict[str, Any]:
    """
    Analyze text and return comprehensive statistics.

    Provides word count, character count, sentence count, paragraph count,
    average word length, and unique word count.

    Args:
        text: Text to analyze

    Returns:
        dict: Comprehensive text statistics with status

    Examples:
        >>> analyze_text("Hello world. This is a test.")
        {
            "status": "success",
            "word_count": 6,
            "character_count": 28,
            "sentence_count": 2,
            ...
        }
    """
    try:
        # Basic validation
        if not text or not text.strip():
            return {
                "status": "error",
                "error_message": "Text cannot be empty",
            }

        # Word analysis
        words = text.split()
        word_count = len(words)
        unique_words = len(set(w.lower() for w in words))

        # Character count (excluding whitespace)
        char_count = len(text)
        char_count_no_spaces = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))

        # Sentence count (basic - counts . ! ?)
        sentence_count = len(re.findall(r'[.!?]+', text))
        if sentence_count == 0 and text:
            sentence_count = 1  # At least one sentence if there's text

        # Paragraph count
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)
        if paragraph_count == 0 and text:
            paragraph_count = 1

        # Average word length
        avg_word_length = sum(len(w) for w in words) / word_count if word_count > 0 else 0

        # Line count
        line_count = len([line for line in text.split('\n') if line.strip()])

        return {
            "status": "success",
            "word_count": word_count,
            "unique_word_count": unique_words,
            "character_count": char_count,
            "character_count_no_spaces": char_count_no_spaces,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "line_count": line_count,
            "average_word_length": round(avg_word_length, 2),
            "vocabulary_richness": round(unique_words / word_count, 2) if word_count > 0 else 0,
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Text analysis failed: {str(e)}",
        }


def count_words(text: str) -> Dict[str, Any]:
    """
    Count the number of words in the given text.

    This is a simpler version of analyze_text that only returns word count.
    Useful when you just need a quick word count without full analysis.

    Args:
        text: Text to count words in

    Returns:
        dict: Word count with status

    Examples:
        >>> count_words("Hello world")
        {"status": "success", "word_count": 2, "text_preview": "Hello world"}
    """
    try:
        if not text or not text.strip():
            return {
                "status": "error",
                "error_message": "Text cannot be empty",
            }

        words = text.split()
        word_count = len(words)

        # Create preview (first 50 characters)
        preview = text[:50] + "..." if len(text) > 50 else text

        return {
            "status": "success",
            "word_count": word_count,
            "text_preview": preview,
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Word count failed: {str(e)}",
        }
