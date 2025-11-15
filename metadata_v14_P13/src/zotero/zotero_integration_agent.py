#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Zotero Integration Agent - Local Database Access

Extracts complete bibliographic metadata from local Zotero database.
Reads from backup database to avoid locking issues when Zotero is running.

Key Features:
-------------
- **SQLite Access**: Direct read from zotero.sqlite.bak (no API needed)
- **PDF Lookup**: Find Zotero item by PDF filename or path
- **Complete Metadata**: Authors, title, DOI, journal, year, etc.
- **Collection Info**: User's functional folder organization
- **Parent-Child Resolution**: Navigate attachment → bibliographic record

Author: Claude Code
Date: 2025-10-03
Version: 1.0
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import sqlite3
import hashlib

# MANDATORY UTF-8 SETUP
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


class ZoteroIntegrationAgent:
    """
    Access Zotero's local SQLite database for metadata extraction.

    This agent provides the bridge between extracted content and Zotero's
    bibliographic database, enabling automatic citation information without
    web searches or manual entry.

    Architecture:
    ------------
    - Reads from zotero.sqlite.bak (avoids database locking)
    - Navigates parent-child item relationships
    - Extracts normalized metadata fields
    - Maps storage keys to physical file paths

    Usage Example:
    --------------
    >>> zotero = ZoteroIntegrationAgent(
    ...     zotero_data_dir=Path("C:/Users/Tom Ochs i9/Zotero")
    ... )
    >>>
    >>> # Find item by PDF filename
    >>> item = zotero.find_item_by_pdf("McGlade and Ekins - 2015.pdf")
    >>>
    >>> # Get complete metadata
    >>> metadata = zotero.get_metadata(item['zotero_key'])
    >>> print(metadata['title'])
    >>> print(metadata['authors'])
    >>> print(metadata['doi'])
    """

    def __init__(self, zotero_data_dir: Path):
        """
        Initialize Zotero integration agent.

        Args:
            zotero_data_dir: Path to Zotero data directory
                            (e.g., C:/Users/USERNAME/Zotero)
        """
        self.zotero_data_dir = Path(zotero_data_dir)

        # Use backup database to avoid locking issues
        self.db_path = self.zotero_data_dir / "zotero.sqlite.bak"
        self.storage_dir = self.zotero_data_dir / "storage"

        # Verify Zotero installation
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Zotero database not found at {self.db_path}\n"
                f"Expected directory: {self.zotero_data_dir}"
            )

        if not self.storage_dir.exists():
            raise FileNotFoundError(
                f"Zotero storage not found at {self.storage_dir}"
            )

    def find_item_by_pdf(self, pdf_path: Path) -> Optional[Dict[str, Any]]:
        """
        Find Zotero item by PDF filename or full path.

        Searches Zotero's itemAttachments for matching PDF file.
        Returns parent item (bibliographic record) information.

        Args:
            pdf_path: Path to PDF file (can be filename only or full path)

        Returns:
            Dictionary with item information or None if not found:
            {
                'attachment_id': int,      # PDF attachment itemID
                'parent_id': int,          # Parent item itemID
                'zotero_key': str,         # Parent item key (8 chars)
                'storage_key': str,        # Storage folder key (8 chars)
                'pdf_path': Path,          # Full path to PDF in storage
                'filename': str            # PDF filename
            }
        """
        filename = Path(pdf_path).name

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Find attachment by filename (stored as "storage:filename.pdf")
            cursor.execute("""
                SELECT ia.itemID, ia.parentItemID, i.key, ia.path
                FROM itemAttachments ia
                JOIN items i ON ia.itemID = i.itemID
                WHERE ia.path LIKE ?
            """, (f'%{filename}%',))

            result = cursor.fetchone()

            if not result:
                return None

            attachment_id, parent_id, storage_key, path = result

            # Get parent item key
            cursor.execute("SELECT key FROM items WHERE itemID = ?", (parent_id,))
            parent_key = cursor.fetchone()

            if not parent_key:
                return None

            # Resolve storage path
            pdf_full_path = self.storage_dir / storage_key / filename

            return {
                'attachment_id': attachment_id,
                'parent_id': parent_id,
                'zotero_key': parent_key[0],
                'storage_key': storage_key,
                'pdf_path': pdf_full_path,
                'filename': filename
            }

        finally:
            conn.close()

    def get_metadata(self, item_key: str) -> Dict[str, Any]:
        """
        Get complete bibliographic metadata for Zotero item.

        Extracts all metadata fields and authors for the specified item.
        Returns structured metadata ready for RAG extraction integration.

        Args:
            item_key: Zotero item key (8-character string, e.g., 'NSLF2GXS')

        Returns:
            Dictionary with complete metadata:
            {
                'zotero_key': str,
                'item_type': str,           # 'journalArticle', 'book', etc.
                'title': str,
                'authors': List[str],       # ["First Last", ...]
                'editors': List[str],       # If applicable
                'publication': str,         # Journal/book title
                'doi': str,                 # If available
                'isbn': str,                # If available
                'issn': str,                # If available
                'year': int,
                'date': str,                # Full date string
                'volume': str,
                'issue': str,
                'pages': str,
                'url': str,
                'abstract': str,
                'language': str,
                'collections': List[str],   # User's folders
                'date_added': str,
                'date_modified': str
            }
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get item ID and type
            cursor.execute("""
                SELECT i.itemID, it.typeName
                FROM items i
                JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
                WHERE i.key = ?
            """, (item_key,))

            item_info = cursor.fetchone()
            if not item_info:
                raise ValueError(f"Item not found: {item_key}")

            item_id, item_type = item_info

            # Get metadata fields
            metadata = {
                'zotero_key': item_key,
                'item_type': item_type,
                'authors': [],
                'editors': []
            }

            # Extract all metadata fields
            cursor.execute("""
                SELECT f.fieldName, idv.value
                FROM itemData id
                JOIN fields f ON id.fieldID = f.fieldID
                JOIN itemDataValues idv ON id.valueID = idv.valueID
                WHERE id.itemID = ?
            """, (item_id,))

            fields = cursor.fetchall()
            for field_name, value in fields:
                # Map Zotero field names to our schema
                if field_name == 'title':
                    metadata['title'] = value
                elif field_name == 'publicationTitle':
                    metadata['publication'] = value
                elif field_name == 'bookTitle':
                    metadata['publication'] = value
                elif field_name == 'DOI':
                    metadata['doi'] = value
                elif field_name == 'ISBN':
                    metadata['isbn'] = value
                elif field_name == 'ISSN':
                    metadata['issn'] = value
                elif field_name == 'date':
                    metadata['date'] = value
                    # Extract year
                    try:
                        metadata['year'] = int(value.split('-')[0])
                    except (ValueError, IndexError):
                        metadata['year'] = None
                elif field_name == 'volume':
                    metadata['volume'] = value
                elif field_name == 'issue':
                    metadata['issue'] = value
                elif field_name == 'pages':
                    metadata['pages'] = value
                elif field_name == 'url':
                    metadata['url'] = value
                elif field_name == 'abstractNote':
                    metadata['abstract'] = value
                elif field_name == 'language':
                    metadata['language'] = value

            # Get creators (authors, editors, etc.)
            cursor.execute("""
                SELECT c.firstName, c.lastName, ct.creatorType, ic.orderIndex
                FROM itemCreators ic
                JOIN creators c ON ic.creatorID = c.creatorID
                JOIN creatorTypes ct ON ic.creatorTypeID = ct.creatorTypeID
                WHERE ic.itemID = ?
                ORDER BY ic.orderIndex
            """, (item_id,))

            creators = cursor.fetchall()
            for first_name, last_name, creator_type, _ in creators:
                full_name = f"{first_name} {last_name}".strip()
                if creator_type == 'author':
                    metadata['authors'].append(full_name)
                elif creator_type == 'editor':
                    metadata['editors'].append(full_name)

            # Get collections (user's folders)
            cursor.execute("""
                SELECT c.collectionName
                FROM collections c
                JOIN collectionItems ci ON c.collectionID = ci.collectionID
                WHERE ci.itemID = ?
            """, (item_id,))

            collections = cursor.fetchall()
            metadata['collections'] = [col[0] for col in collections]

            # Get dates
            cursor.execute("""
                SELECT dateAdded, dateModified
                FROM items
                WHERE itemID = ?
            """, (item_id,))

            dates = cursor.fetchone()
            if dates:
                metadata['date_added'] = dates[0]
                metadata['date_modified'] = dates[1]

            return metadata

        finally:
            conn.close()

    def get_pdf_attachments(self, item_key: str) -> List[Dict[str, Any]]:
        """
        Get all PDF attachments for a Zotero item.

        Returns PDFs in Zotero order (article first, then supplementary materials).

        Args:
            item_key: Zotero item key (8 characters)

        Returns:
            List of PDF attachment dictionaries:
            [
                {
                    'attachment_key': str,     # Attachment's own Zotero key
                    'filename': str,           # PDF filename
                    'path': Path,              # Full path to PDF
                    'size_mb': float,          # File size in MB
                    'content_type': str        # MIME type
                },
                ...
            ]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get item ID from key
            cursor.execute("SELECT itemID FROM items WHERE key = ?", (item_key,))
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"Item not found: {item_key}")

            item_id = result[0]

            # Get all PDF attachments (ordered by itemID to maintain Zotero order)
            cursor.execute("""
                SELECT
                    i.key,
                    ia.path,
                    ia.contentType
                FROM itemAttachments ia
                JOIN items i ON ia.itemID = i.itemID
                WHERE ia.parentItemID = ?
                AND ia.contentType = 'application/pdf'
                ORDER BY ia.itemID
            """, (item_id,))

            attachments = []
            for att_key, path, content_type in cursor.fetchall():
                # Extract filename from path (stored as "storage:filename.pdf")
                filename = path.split(':')[-1] if ':' in path else path

                # Build full path
                full_path = self.storage_dir / att_key / filename

                # Get file size if exists
                size_mb = 0.0
                if full_path.exists():
                    size_mb = full_path.stat().st_size / (1024 * 1024)

                attachments.append({
                    'attachment_key': att_key,
                    'filename': filename,
                    'path': full_path,
                    'size_mb': size_mb,
                    'content_type': content_type
                })

            return attachments

        finally:
            conn.close()

    def search_by_title(self, title: str, exact: bool = False) -> List[Dict[str, Any]]:
        """
        Search Zotero library by title.

        Args:
            title: Title text to search for
            exact: If True, require exact match (case-insensitive)
                   If False, use partial match (default)

        Returns:
            List of matching items with metadata and PDF attachments:
            [
                {
                    'zotero_key': str,
                    'title': str,
                    'authors': List[str],
                    'year': int,
                    'item_type': str,
                    'pdf_count': int,
                    'pdfs': List[Dict]  # From get_pdf_attachments()
                },
                ...
            ]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Search in itemData for title field
            if exact:
                cursor.execute("""
                    SELECT DISTINCT i.key, i.itemID
                    FROM items i
                    JOIN itemData id ON i.itemID = id.itemID
                    JOIN fields f ON id.fieldID = f.fieldID
                    JOIN itemDataValues idv ON id.valueID = idv.valueID
                    WHERE f.fieldName = 'title'
                    AND LOWER(idv.value) = LOWER(?)
                """, (title,))
            else:
                cursor.execute("""
                    SELECT DISTINCT i.key, i.itemID
                    FROM items i
                    JOIN itemData id ON i.itemID = id.itemID
                    JOIN fields f ON id.fieldID = f.fieldID
                    JOIN itemDataValues idv ON id.valueID = idv.valueID
                    WHERE f.fieldName = 'title'
                    AND LOWER(idv.value) LIKE LOWER(?)
                """, (f'%{title}%',))

            results = []
            for item_key, item_id in cursor.fetchall():
                # Get full metadata
                metadata = self.get_metadata(item_key)

                # Get PDF attachments
                pdfs = self.get_pdf_attachments(item_key)

                # Build result
                results.append({
                    'zotero_key': item_key,
                    'title': metadata.get('title', ''),
                    'authors': metadata.get('authors', []),
                    'year': metadata.get('year'),
                    'item_type': metadata.get('item_type', ''),
                    'pdf_count': len(pdfs),
                    'pdfs': pdfs
                })

            return results

        finally:
            conn.close()

    def search_by_author(self, author: str) -> List[Dict[str, Any]]:
        """
        Search Zotero library by author name.

        Args:
            author: Author name to search for (partial match)

        Returns:
            List of matching items (same format as search_by_title)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Search in creators
            cursor.execute("""
                SELECT DISTINCT i.key, i.itemID
                FROM items i
                JOIN itemCreators ic ON i.itemID = ic.itemID
                JOIN creators c ON ic.creatorID = c.creatorID
                WHERE LOWER(c.firstName) LIKE LOWER(?)
                OR LOWER(c.lastName) LIKE LOWER(?)
            """, (f'%{author}%', f'%{author}%'))

            results = []
            for item_key, item_id in cursor.fetchall():
                metadata = self.get_metadata(item_key)
                pdfs = self.get_pdf_attachments(item_key)

                results.append({
                    'zotero_key': item_key,
                    'title': metadata.get('title', ''),
                    'authors': metadata.get('authors', []),
                    'year': metadata.get('year'),
                    'item_type': metadata.get('item_type', ''),
                    'pdf_count': len(pdfs),
                    'pdfs': pdfs
                })

            return results

        finally:
            conn.close()

    def search_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Search Zotero library by DOI (exact match).

        Args:
            doi: DOI to search for

        Returns:
            Item dictionary or None if not found (same format as search_by_title)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Search for DOI field
            cursor.execute("""
                SELECT DISTINCT i.key, i.itemID
                FROM items i
                JOIN itemData id ON i.itemID = id.itemID
                JOIN fields f ON id.fieldID = f.fieldID
                JOIN itemDataValues idv ON id.valueID = idv.valueID
                WHERE f.fieldName = 'DOI'
                AND LOWER(idv.value) = LOWER(?)
            """, (doi,))

            result = cursor.fetchone()
            if not result:
                return None

            item_key, item_id = result
            metadata = self.get_metadata(item_key)
            pdfs = self.get_pdf_attachments(item_key)

            return {
                'zotero_key': item_key,
                'title': metadata.get('title', ''),
                'authors': metadata.get('authors', []),
                'year': metadata.get('year'),
                'item_type': metadata.get('item_type', ''),
                'pdf_count': len(pdfs),
                'pdfs': pdfs
            }

        finally:
            conn.close()

    def get_citation(self, item_key: str, style: str = 'apa') -> str:
        """
        Generate formatted citation for item.

        Creates human-readable citation string in specified style.

        Args:
            item_key: Zotero item key
            style: Citation style ('apa', 'mla', 'chicago', 'simple')

        Returns:
            Formatted citation string
        """
        metadata = self.get_metadata(item_key)

        if style == 'simple' or style == 'apa':
            # Simple format: Authors (Year). Title. Publication.
            authors_str = ', '.join(metadata.get('authors', []))
            year = metadata.get('year', 'n.d.')
            title = metadata.get('title', 'Untitled')
            publication = metadata.get('publication', '')

            citation = f"{authors_str} ({year}). {title}."
            if publication:
                citation += f" {publication}."

            # Add DOI if available
            doi = metadata.get('doi')
            if doi:
                citation += f" https://doi.org/{doi}"

            return citation

        else:
            # Fallback to simple format
            return self.get_citation(item_key, style='simple')

    def generate_document_id(self, item_key: str) -> str:
        """
        Generate unique document ID for use in RAG system.

        Creates stable, readable ID based on metadata.
        Format: {type}_{author_last}_{year}_{title_words}

        Args:
            item_key: Zotero item key

        Returns:
            Document ID string (e.g., 'journal_mcglade_2015_fossil_fuels')
        """
        metadata = self.get_metadata(item_key)

        # Get item type prefix
        item_type = metadata.get('item_type', 'document')
        if item_type == 'journalArticle':
            type_prefix = 'journal'
        elif item_type == 'book':
            type_prefix = 'book'
        elif item_type == 'bookSection':
            type_prefix = 'chapter'
        else:
            type_prefix = item_type

        # Get first author's last name
        authors = metadata.get('authors', [])
        if authors:
            author_last = authors[0].split()[-1].lower()
        else:
            author_last = 'unknown'

        # Get year
        year = metadata.get('year', '0000')

        # Get first 3 significant words from title
        title = metadata.get('title', 'untitled')
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        title_words = [
            w.lower() for w in title.split()
            if w.lower() not in stop_words and len(w) > 2
        ][:3]
        title_part = '_'.join(title_words) if title_words else 'untitled'

        # Combine parts
        doc_id = f"{type_prefix}_{author_last}_{year}_{title_part}"

        # Clean and truncate
        doc_id = ''.join(c if c.isalnum() or c == '_' else '_' for c in doc_id)
        doc_id = doc_id[:80]  # Reasonable length limit

        return doc_id


def main():
    """Test Zotero integration."""
    print("Testing Zotero Integration Agent...")

    zotero_dir = Path(r"C:\Users\Tom Ochs i9\Zotero")
    zotero = ZoteroIntegrationAgent(zotero_dir)

    # Test: Find item by PDF filename
    print("\n1. Testing PDF lookup...")
    test_filename = "McGlade and Ekins - 2015 - The geographical distribution of fossil fuels unus.pdf"
    item = zotero.find_item_by_pdf(test_filename)

    if item:
        print(f"   ✅ Found item: {item['zotero_key']}")
        print(f"   Storage: {item['storage_key']}")
        print(f"   PDF: {item['pdf_path']}")

        # Test: Get metadata
        print("\n2. Testing metadata extraction...")
        metadata = zotero.get_metadata(item['zotero_key'])

        print(f"   Title: {metadata.get('title', 'N/A')}")
        print(f"   Authors: {', '.join(metadata.get('authors', []))}")
        print(f"   Journal: {metadata.get('publication', 'N/A')}")
        print(f"   Year: {metadata.get('year', 'N/A')}")
        print(f"   DOI: {metadata.get('doi', 'N/A')}")
        print(f"   Collections: {', '.join(metadata.get('collections', []))}")

        # Test: Generate document ID
        print("\n3. Testing document ID generation...")
        doc_id = zotero.generate_document_id(item['zotero_key'])
        print(f"   Document ID: {doc_id}")

        # Test: Generate citation
        print("\n4. Testing citation generation...")
        citation = zotero.get_citation(item['zotero_key'])
        print(f"   Citation: {citation}")

        print("\n✅ Zotero integration test complete")
    else:
        print(f"   ❌ PDF not found in Zotero library")


if __name__ == "__main__":
    main()
