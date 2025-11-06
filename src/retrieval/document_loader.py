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
        """
        Set a deterministic `doc_id` based on the document content when no `doc_id` was provided.
        
        If `doc_id` is None, computes the MD5 hash of `content`, takes the first 16 hex characters, and sets `doc_id` to `doc_<16_hex_chars>`.
        """
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
        Load a Document object from the given file path.
        
        Parameters:
            file_path (str): Path to the source file to load.
        
        Returns:
            Document: A Document populated with the file's content and metadata.
        
        Raises:
            NotImplementedError: Implementations must override this method in subclasses.
        """
        raise NotImplementedError


class TextDocumentLoader(DocumentLoader):
    """
    Loader for plain text (.txt) files.
    """

    def load(self, file_path: str) -> Document:
        """
        Load a text document from disk.
        
        Parameters:
            file_path (str): Path to the `.txt` file to load.
        
        Returns:
            Document: Document containing the file's text content and metadata (source, filename, file_type, file_size_bytes, changed_at, modified_at).
        
        Raises:
            FileNotFoundError: If the given file does not exist.
            UnicodeDecodeError: If the file cannot be decoded as UTF-8.
            Exception: Propagates other unexpected errors encountered while reading the file.
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
        Load a Markdown (.md) file and return a Document containing its content and file metadata.
        
        Parameters:
            file_path (str): Path to the Markdown file.
        
        Returns:
            Document: Document with `content` set to the file text and `metadata` containing:
                - source: absolute path
                - filename: file name
                - file_type: "md"
                - file_size_bytes: file size in bytes
                - created_at: creation time in ISO format
                - modified_at: modification time in ISO format
                - title: (optional) first H1 heading from the file
        
        Raises:
            FileNotFoundError: If the file does not exist.
            UnicodeDecodeError: If the file cannot be decoded as UTF-8.
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
    Selects the appropriate loader by file extension and returns the loaded Document.
    
    Parameters:
        file_path (str): Path to the document file to load.
    
    Returns:
        Document: The loaded document with content and metadata.
    
    Raises:
        ValueError: If the file extension is not supported (supported: .txt, .md).
        FileNotFoundError: If the specified file does not exist.
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
    Collects and loads documents from a directory, optionally traversing subdirectories and filtering by file extension.
    
    Parameters:
    	directory (str): Path to the directory to search.
    	recursive (bool): If True, search subdirectories recursively; if False, search only the top-level directory.
    	file_extensions (Optional[List[str]]): List of file extensions to include (each with a leading dot), defaults to [".txt", ".md"].
    
    Returns:
    	List[Document]: Successfully loaded Document objects.
    
    Raises:
    	FileNotFoundError: If the directory does not exist.
    	ValueError: If the provided path is not a directory.
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
    Compute aggregate statistics for a list of Document objects.
    
    Returns:
        dict: A dictionary with the following keys:
            - total_documents (int): Number of documents.
            - total_characters (int): Sum of characters across all document contents.
            - total_size_bytes (int): Sum of `file_size_bytes` from each document's metadata (uses 0 if missing).
            - avg_chars_per_doc (int): Average characters per document using integer division (0 if no documents).
            - file_types (dict): Mapping from `file_type` (from metadata, or `"unknown"`) to count of documents.
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