#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF Hash Utility

Generates SHA256 hashes for PDF files to uniquely identify document content.
Used by ExtractionRegistry to detect if a document has been extracted before.

Key Features:
    - SHA256 hashing for reliable content identification
    - Handles large files efficiently with chunked reading
    - Returns hash with 'sha256:' prefix for registry compatibility

Author: V11 Development Team
Created: 2025-10-03
"""

import sys
import os
from pathlib import Path
import hashlib

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')
    if not hasattr(sys.stderr, '_wrapped_utf8'):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            sys.stderr._wrapped_utf8 = True
        except (AttributeError, ValueError):
            pass


def compute_pdf_hash(pdf_path: Path, chunk_size: int = 8192) -> str:
    """
    Compute SHA256 hash of a PDF file.

    Uses chunked reading to efficiently handle large files without loading
    entire file into memory.

    Args:
        pdf_path: Path to PDF file
        chunk_size: Size of chunks to read (default 8KB)

    Returns:
        str: Hash in format 'sha256:hexdigest'

    Raises:
        FileNotFoundError: If PDF file does not exist
        PermissionError: If file cannot be read

    Example:
        >>> pdf_hash = compute_pdf_hash(Path("data/chapter4.pdf"))
        >>> print(pdf_hash)
        sha256:a1b2c3d4e5f6...
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Use SHA256 for reliable content identification
    sha256_hash = hashlib.sha256()

    # Read file in chunks to handle large PDFs efficiently
    with pdf_path.open('rb') as f:
        while chunk := f.read(chunk_size):
            sha256_hash.update(chunk)

    # Return with prefix for registry compatibility
    return f"sha256:{sha256_hash.hexdigest()}"


def verify_pdf_unchanged(pdf_path: Path, expected_hash: str) -> bool:
    """
    Verify that a PDF file has not changed since extraction.

    Args:
        pdf_path: Path to PDF file
        expected_hash: Previously computed hash to compare against

    Returns:
        bool: True if file hash matches expected_hash, False otherwise

    Example:
        >>> unchanged = verify_pdf_unchanged(
        ...     Path("data/chapter4.pdf"),
        ...     "sha256:a1b2c3d4e5f6..."
        ... )
        >>> if not unchanged:
        ...     print("⚠️ PDF has been modified - re-extraction needed")
    """
    try:
        current_hash = compute_pdf_hash(pdf_path)
        return current_hash == expected_hash
    except (FileNotFoundError, PermissionError):
        return False
