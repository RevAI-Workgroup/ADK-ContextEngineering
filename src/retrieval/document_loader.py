"""
Document Loading and Processing.

This module provides document loaders for different file formats (TXT, MD).
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import logging
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """
    Loaded document with metadata.

    Attributes:
        content: Full text content of the document
        metadata: Document metadata (source, type, created_at, etc.)
        doc_id: Unique document identifier
    """
    content: str
    metadata: Dict[str, Any]
    doc_id: Optional[str] = None

    def __post_init__(self):
        """Generate doc_id if not provided."""
        if self.doc_id is None:
            # Generate ID from content hash
            content_hash = hashlib.md5(self.content.encode()).hexdigest()
            self.doc_id = f"doc_{content_hash[:16]}"


class DocumentLoader:
    """
    Base class for document loaders.
    """

    def load(self, file_path: str) -> Document:
        """
        Load a document from file.

        Args:
            file_path: Path to the document file

        Returns:
            Loaded Document object
        """
        raise NotImplementedError


class TextDocumentLoader(DocumentLoader):
    """
    Loader for plain text (.txt) files.
    """

    def load(self, file_path: str) -> Document:
        """
        Load a text document.

        Args:
            file_path: Path to the .txt file

        Returns:
            Loaded Document object
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # Read file content
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract metadata
            metadata = {
                "source": str(path.absolute()),
                "filename": path.name,
                "file_type": "txt",
                "file_size_bytes": path.stat().st_size,
                "changed_at": datetime.fromtimestamp(path.stat().st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat()
            }

            logger.info(f"Loaded text document: {path.name} ({len(content)} chars)")

            return Document(content=content, metadata=metadata)

        except UnicodeDecodeError:
            logger.error(f"Failed to decode file as UTF-8: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to load text document: {e}", exc_info=True)
            raise


class MarkdownDocumentLoader(DocumentLoader):
    """
    Loader for Markdown (.md) files.
    """

    def load(self, file_path: str) -> Document:
        """
        Load a Markdown document.

        Args:
            file_path: Path to the .md file

        Returns:
            Loaded Document object
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # Read file content
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract title from first H1 heading if present
            title = None
            lines = content.split("\n")
            for line in lines:
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            # Extract metadata
            metadata = {
                "source": str(path.absolute()),
                "filename": path.name,
                "file_type": "md",
                "file_size_bytes": path.stat().st_size,
                "created_at": datetime.fromtimestamp(path.stat().st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat()
            }

            if title:
                metadata["title"] = title

            logger.info(f"Loaded markdown document: {path.name} ({len(content)} chars)")

            return Document(content=content, metadata=metadata)

        except UnicodeDecodeError:
            logger.error(f"Failed to decode file as UTF-8: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to load markdown document: {e}", exc_info=True)
            raise


def load_document(file_path: str) -> Document:
    """
    Load a document based on file extension.

    Args:
        file_path: Path to the document file

    Returns:
        Loaded Document object

    Raises:
        ValueError: If file type is not supported
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".txt":
        loader = TextDocumentLoader()
    elif extension == ".md":
        loader = MarkdownDocumentLoader()
    else:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            f"Supported types: .txt, .md"
        )

    return loader.load(file_path)


def load_documents_from_directory(
    directory: str,
    recursive: bool = True,
    file_extensions: Optional[List[str]] = None
) -> List[Document]:
    """
    Load all documents from a directory.

    Args:
        directory: Path to the directory
        recursive: Whether to search recursively
        file_extensions: List of file extensions to include (default: [".txt", ".md"])

    Returns:
        List of loaded Document objects
    """
    if file_extensions is None:
        file_extensions = [".txt", ".md"]

    path = Path(directory)

    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    documents = []

    # Get all files
    if recursive:
        files = [f for f in path.rglob("*") if f.is_file()]
    else:
        files = [f for f in path.iterdir() if f.is_file()]

    # Filter by extensions
    files = [f for f in files if f.suffix.lower() in file_extensions]

    logger.info(f"Found {len(files)} documents in {directory}")

    # Load each file
    for file_path in files:
        try:
            doc = load_document(str(file_path))
            documents.append(doc)
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
            # Continue with other files

    logger.info(f"Successfully loaded {len(documents)} documents")

    return documents


def get_document_stats(documents: List[Document]) -> Dict[str, Any]:
    """
    Get statistics about a list of documents.

    Args:
        documents: List of Document objects

    Returns:
        Dictionary with document statistics
    """
    if not documents:
        return {
            "total_documents": 0,
            "total_characters": 0,
            "total_size_bytes": 0,
            "file_types": {}
        }

    total_chars = sum(len(doc.content) for doc in documents)
    total_size = sum(doc.metadata.get("file_size_bytes", 0) for doc in documents)

    # Count file types
    file_types = {}
    for doc in documents:
        file_type = doc.metadata.get("file_type", "unknown")
        file_types[file_type] = file_types.get(file_type, 0) + 1

    return {
        "total_documents": len(documents),
        "total_characters": total_chars,
        "total_size_bytes": total_size,
        "avg_chars_per_doc": total_chars // len(documents) if documents else 0,
        "file_types": file_types
    }
