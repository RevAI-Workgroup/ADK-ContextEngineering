"""
Text Chunking Strategies.

This module provides different strategies for chunking documents into smaller
pieces suitable for embedding and retrieval.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
import tiktoken

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """
    A text chunk with metadata.

    Attributes:
        text: Chunk text content
        metadata: Chunk metadata (source, chunk_index, etc.)
        chunk_id: Unique identifier for this chunk
    """
    text: str
    metadata: Dict[str, Any]
    chunk_id: Optional[str] = None

    def __post_init__(self):
        """Generate chunk_id if not provided."""
        if self.chunk_id is None:
            source = self.metadata.get("source", "unknown")
            index = self.metadata.get("chunk_index", 0)
            self.chunk_id = f"{source}_chunk_{index}"


class ChunkingStrategy:
    """Base class for chunking strategies."""

    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Chunk text into smaller pieces.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of Chunk objects
        """
        raise NotImplementedError


class FixedSizeChunking(ChunkingStrategy):
    """
    Fixed-size chunking with overlap.

    Chunks text into fixed-size pieces based on token count,
    with optional overlap between chunks for context preservation.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        encoding_name: str = "cl100k_base"  # GPT-4 encoding
    ):
        """
        Initialize fixed-size chunking strategy.

        Args:
            chunk_size: Target size of each chunk in tokens
            chunk_overlap: Number of tokens to overlap between chunks
            encoding_name: Tiktoken encoding to use
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            logger.warning(f"Failed to load encoding {encoding_name}, using default: {e}")
            self.encoding = tiktoken.get_encoding("cl100k_base")

        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Chunk text into fixed-size pieces with overlap.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of Chunk objects
        """
        if not text or not text.strip():
            return []

        if metadata is None:
            metadata = {}

        # Encode text to tokens
        tokens = self.encoding.encode(text)

        # Split into chunks
        chunks = []
        start = 0

        while start < len(tokens):
            # Get chunk tokens
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]

            # Decode back to text
            chunk_text = self.encoding.decode(chunk_tokens)

            # Create chunk metadata
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_index": len(chunks),
                "chunk_size": len(chunk_tokens),
                "start_token": start,
                "end_token": end
            })

            # Create chunk
            chunk = Chunk(
                text=chunk_text,
                metadata=chunk_metadata
            )
            chunks.append(chunk)

            # Move to next chunk with overlap
            start = end - self.chunk_overlap

            # Prevent infinite loop
            if start >= len(tokens):
                break

        logger.info(
            f"Chunked text into {len(chunks)} chunks "
            f"(chunk_size={self.chunk_size}, overlap={self.chunk_overlap})"
        )

        return chunks


class SentenceChunking(ChunkingStrategy):
    """
    Sentence-based chunking.

    Chunks text by sentences, combining sentences until reaching target size.
    If a single sentence exceeds chunk_size, it will be split into token-based
    sub-chunks respecting chunk_size and overlap semantics.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap_sentences: int = 1,
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize sentence-based chunking strategy.

        Args:
            chunk_size: Target size of each chunk in tokens
            chunk_overlap_sentences: Number of sentences to overlap
            encoding_name: Tiktoken encoding to use
        """
        self.chunk_size = chunk_size
        self.chunk_overlap_sentences = chunk_overlap_sentences

        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Chunk text by sentences.

        Sentences are combined until reaching chunk_size. If a single sentence
        exceeds chunk_size, it will be split into token-based sub-chunks with
        overlap semantics applied.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of Chunk objects
        """
        if not text or not text.strip():
            return []

        if metadata is None:
            metadata = {}

        # Split into sentences (simple splitting)
        sentences = self._split_sentences(text)

        if not sentences:
            return []

        # Combine sentences into chunks
        chunks = []
        current_chunk_sentences = []
        current_token_count = 0

        for sentence in sentences:
            sentence_tokens = len(self.encoding.encode(sentence))

            # Handle oversized sentences: split into token-based sub-chunks
            if sentence_tokens > self.chunk_size:
                # First, finalize current chunk if it has content
                if current_chunk_sentences:
                    chunk_text = " ".join(current_chunk_sentences)
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        "chunk_index": len(chunks),
                        "chunk_size": current_token_count,
                        "sentence_count": len(current_chunk_sentences)
                    })
                    chunks.append(Chunk(text=chunk_text, metadata=chunk_metadata))
                    current_chunk_sentences = []
                    current_token_count = 0

                # Split oversized sentence into token-based sub-chunks
                sentence_sub_chunks = self._split_oversized_sentence(sentence)
                
                for sub_chunk_text, sub_chunk_tokens in sentence_sub_chunks:
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        "chunk_index": len(chunks),
                        "chunk_size": sub_chunk_tokens,
                        "sentence_count": 1  # One sentence fragment
                    })
                    chunks.append(Chunk(text=sub_chunk_text, metadata=chunk_metadata))

                # Reset for next sentence (no overlap for oversized sentence fragments)
                current_chunk_sentences = []
                current_token_count = 0
                continue

            # Check if adding this sentence would exceed chunk size
            if current_token_count + sentence_tokens > self.chunk_size and current_chunk_sentences:
                # Create chunk from current sentences
                chunk_text = " ".join(current_chunk_sentences)
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunk_index": len(chunks),
                    "chunk_size": current_token_count,
                    "sentence_count": len(current_chunk_sentences)
                })

                chunks.append(Chunk(text=chunk_text, metadata=chunk_metadata))

                # Start new chunk with overlap
                if self.chunk_overlap_sentences > 0:
                    overlap_sentences = current_chunk_sentences[-self.chunk_overlap_sentences:]
                    current_chunk_sentences = overlap_sentences
                    current_token_count = sum(
                        len(self.encoding.encode(s)) for s in overlap_sentences
                    )
                else:
                    current_chunk_sentences = []
                    current_token_count = 0

            # Add sentence to current chunk
            current_chunk_sentences.append(sentence)
            current_token_count += sentence_tokens

        # Add final chunk
        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences)
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_index": len(chunks),
                "chunk_size": current_token_count,
                "sentence_count": len(current_chunk_sentences)
            })

            chunks.append(Chunk(text=chunk_text, metadata=chunk_metadata))

        logger.info(f"Chunked text into {len(chunks)} sentence-based chunks")

        return chunks

    def _split_oversized_sentence(self, sentence: str) -> List[Tuple[str, int]]:
        """
        Split an oversized sentence into token-based sub-chunks.

        Applies overlap semantics: calculates overlap tokens based on
        chunk_overlap_sentences parameter. If chunk_overlap_sentences is 0,
        no overlap is used. Otherwise, overlap is proportional to the number
        of overlapping sentences configured.

        Args:
            sentence: Sentence that exceeds chunk_size

        Returns:
            List of tuples (sub_chunk_text, token_count)
        """
        # Encode sentence to tokens
        tokens = self.encoding.encode(sentence)
        
        # Calculate overlap in tokens based on chunk_overlap_sentences
        # If no sentence overlap is configured, use no token overlap
        if self.chunk_overlap_sentences == 0:
            overlap_tokens = 0
        else:
            # Estimate average sentence tokens as a proportion of chunk_size
            # Typical sentences are ~10-20 tokens, so we use chunk_size // 10
            # as a reasonable estimate for average sentence size
            estimated_sentence_tokens = max(1, self.chunk_size // 10)
            
            # Calculate overlap: number of sentences * estimated tokens per sentence
            overlap_tokens = self.chunk_overlap_sentences * estimated_sentence_tokens
            
            # Cap overlap to reasonable limits to prevent issues
            overlap_tokens = min(
                overlap_tokens,
                int(self.chunk_size * 0.25),  # Max 25% of chunk size
                self.chunk_size - 1  # Ensure overlap < chunk_size
            )
        
        sub_chunks = []
        start = 0
        
        while start < len(tokens):
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]
            
            # Decode back to text
            chunk_text = self.encoding.decode(chunk_tokens)
            token_count = len(chunk_tokens)
            
            sub_chunks.append((chunk_text, token_count))
            
            # Move to next chunk with overlap
            if end >= len(tokens):
                break
            
            start = end - overlap_tokens
            # Prevent infinite loop if overlap is too large
            if start >= len(tokens):
                break
        
        return sub_chunks

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Simple sentence splitting based on common punctuation.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        import re

        # Split on sentence-ending punctuation followed by space or newline
        sentences = re.split(r'(?<=[.!?])\s+', text)

        # Filter out empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences


def chunk_document(
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
    strategy: str = "fixed",
    chunk_size: int = 512,
    chunk_overlap: int = 50
) -> List[Chunk]:
    """
    Chunk a document using the specified strategy.

    Args:
        text: Text to chunk
        metadata: Optional metadata to attach to chunks
        strategy: Chunking strategy ("fixed" or "sentence")
        chunk_size: Target chunk size in tokens
        chunk_overlap: Overlap size (tokens for fixed, sentences for sentence-based)

    Returns:
        List of Chunk objects
    """
    if strategy == "fixed":
        chunker = FixedSizeChunking(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    elif strategy == "sentence":
        chunker = SentenceChunking(
            chunk_size=chunk_size,
            chunk_overlap_sentences=chunk_overlap
        )
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")

    return chunker.chunk_text(text, metadata)


def get_chunking_stats(chunks: List[Chunk]) -> Dict[str, Any]:
    """
    Get statistics about chunks.

    Args:
        chunks: List of Chunk objects

    Returns:
        Dictionary with chunking statistics
    """
    if not chunks:
        return {
            "total_chunks": 0,
            "total_characters": 0,
            "avg_chunk_size": 0
        }

    total_chars = sum(len(chunk.text) for chunk in chunks)

    # Get token sizes if available
    token_sizes = [
        chunk.metadata.get("chunk_size", 0)
        for chunk in chunks
        if "chunk_size" in chunk.metadata
    ]

    stats = {
        "total_chunks": len(chunks),
        "total_characters": total_chars,
        "avg_chars_per_chunk": total_chars // len(chunks) if chunks else 0
    }

    if token_sizes:
        stats.update({
            "total_tokens": sum(token_sizes),
            "avg_tokens_per_chunk": sum(token_sizes) // len(token_sizes),
            "min_tokens": min(token_sizes),
            "max_tokens": max(token_sizes)
        })

    return stats
