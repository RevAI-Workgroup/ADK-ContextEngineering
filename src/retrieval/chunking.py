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
        """
        Ensure the chunk has a stable identifier by generating one from metadata when absent.
        
        If `chunk_id` is `None`, sets `chunk_id` to "{source}_chunk_{chunk_index}" using
        metadata["source"] (default "unknown") and metadata["chunk_index"] (default 0).
        """
        if self.chunk_id is None:
            source = self.metadata.get("source", "unknown")
            index = self.metadata.get("chunk_index", 0)
            self.chunk_id = f"{source}_chunk_{index}"


class ChunkingStrategy:
    """Base class for chunking strategies."""

    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Produce a list of Chunk objects from the provided text according to the strategy's rules.
        
        Parameters:
            text (str): The input text to be split into chunks.
            metadata (Optional[Dict[str, Any]]): Optional metadata to attach to each produced Chunk; if provided, implementations should merge or copy this metadata into each chunk's metadata.
        
        Returns:
            List[Chunk]: A list of Chunk instances representing the input text partitioned by the strategy.
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
        Configure the fixed-size chunking strategy with tokenization parameters.
        
        Parameters:
            chunk_size (int): Target number of tokens per chunk.
            chunk_overlap (int): Number of tokens to overlap between consecutive chunks; must be less than `chunk_size`.
            encoding_name (str): Name of the tiktoken encoding to use for tokenization.
        
        Raises:
            ValueError: If `chunk_overlap` is greater than or equal to `chunk_size`.
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
        Produce fixed-size token chunks from the given text using the instance encoding, applying the configured token overlap.
        
        Parameters:
            text (str): The input text to chunk. Blank or empty text returns an empty list.
            metadata (Optional[Dict[str, Any]]): Optional metadata dictionary to attach to each chunk; the dictionary is copied and extended per chunk.
        
        Returns:
            List[Chunk]: A list of Chunk objects. Each chunk's metadata is extended with:
                - `chunk_index` (int): zero-based index of the chunk,
                - `chunk_size` (int): number of tokens in the chunk,
                - `start_token` (int): start token index (inclusive),
                - `end_token` (int): end token index (exclusive).
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
        Configure a sentence-based chunking strategy.
        
        Parameters:
            chunk_size (int): Target number of tokens per chunk.
            chunk_overlap_sentences (int): Number of whole sentences to repeat between consecutive chunks to create overlap.
            encoding_name (str): Name of the tiktoken encoding to use for tokenization.
        
        Behavior:
            Attempts to load the specified tiktoken encoding; if loading fails, falls back to the default "cl100k_base" encoding.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap_sentences = chunk_overlap_sentences

        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Split input text into sentence-based chunks, combining sentences until a target token size is reached.
        
        Sentences are accumulated into chunks up to self.chunk_size (measured in tokens). If a single sentence exceeds self.chunk_size it is split into token-level sub-chunks (with token-overlap behavior determined by the strategy). Each returned Chunk includes metadata keys such as `chunk_index`, `chunk_size` (token count), and `sentence_count`.
        
        Parameters:
            text (str): Text to chunk.
            metadata (Optional[Dict[str, Any]]): Optional metadata to attach to each chunk; copied and extended with chunk-specific fields.
        
        Returns:
            List[Chunk]: A list of sentence-based Chunk objects covering the input text.
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
        Split an oversized sentence into token-length sub-chunks, applying token-level overlap derived from the configured sentence-overlap setting.
        
        If chunk_overlap_sentences is 0 no overlap is applied. Otherwise the method estimates average tokens per sentence as max(1, chunk_size // 10), multiplies that by chunk_overlap_sentences to get overlap tokens, and caps the overlap to at most 25% of chunk_size and to be strictly less than chunk_size.
        
        Parameters:
            sentence (str): Sentence whose token count exceeds the configured chunk_size.
        
        Returns:
            List[Tuple[str, int]]: A list of (sub_chunk_text, token_count) tuples for each generated sub-chunk, where token_count is the number of tokens in that sub-chunk.
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
        Split input text into sentences using a simple punctuation-based heuristic.
        
        Parameters:
            text (str): The text to split into sentences.
        
        Returns:
            List[str]: Sentences obtained by splitting on sentence-ending punctuation (., !, ?) followed by whitespace; each sentence is stripped and empty entries are omitted.
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
    Chunk a document into smaller Chunk objects using the chosen strategy.
    
    Parameters:
        strategy (str): 'fixed' to produce fixed-size token chunks, or 'sentence' to produce sentence-aware chunks.
        chunk_overlap (int): If `strategy` is 'fixed', number of tokens to overlap between consecutive chunks. If 'sentence', number of sentences to overlap between consecutive chunks.
    
    Returns:
        List[Chunk]: Chunks produced from the input text with attached metadata.
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
    Compute basic statistics for a list of Chunk objects.
    
    Parameters:
        chunks (List[Chunk]): Chunks to analyze.
    
    Returns:
        Dict[str, Any]: Statistics including:
            - total_chunks (int): Number of chunks (0 if input is empty).
            - total_characters (int): Sum of len(chunk.text) across chunks.
            - avg_chars_per_chunk (int): Integer average characters per chunk (0 if no chunks).
            - total_tokens (int, optional): Sum of `chunk_size` values from chunk.metadata when present.
            - avg_tokens_per_chunk (int, optional): Integer average of token sizes (computed over chunks that have `chunk_size`).
            - min_tokens (int, optional): Minimum token count among chunks that have `chunk_size`.
            - max_tokens (int, optional): Maximum token count among chunks that have `chunk_size`.
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