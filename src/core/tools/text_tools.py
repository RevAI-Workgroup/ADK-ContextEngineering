"""
Text analysis tools for processing and analyzing text.

These tools provide various text statistics and analysis capabilities.
"""

import re
from typing import Any, Dict


def analyze_text(text: str) -> Dict[str, Any]:
    """
    Compute comprehensive statistics for the given text.
    
    Returns a dictionary with a "status" key and the following metrics when successful:
    - word_count: total number of whitespace-separated tokens
    - unique_word_count: count of distinct words (case-insensitive)
    - character_count: total characters including whitespace
    - character_count_no_spaces: characters excluding spaces, tabs, and newlines
    - sentence_count: number of sentence-ending punctuation sequences ('.', '!', '?'), at least 1 if text is present
    - paragraph_count: number of non-empty paragraphs separated by blank lines, at least 1 if text is present
    - line_count: number of non-empty lines
    - average_word_length: average length of words rounded to 2 decimals
    - vocabulary_richness: ratio of unique_word_count to word_count rounded to 2 decimals
    
    Returns:
        dict: A result dictionary. On success, contains "status": "success" and the metrics above.
              On failure or invalid input, contains "status": "error" and "error_message".
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
    Compute word count and a short text preview for the given text.
    
    If the input is empty or only whitespace, returns an error dictionary describing the problem.
    
    Returns:
        dict: On success, contains "status" = "success", "word_count" (int), and "text_preview" (str).
              On error, contains "status" = "error" and "error_message" (str).
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