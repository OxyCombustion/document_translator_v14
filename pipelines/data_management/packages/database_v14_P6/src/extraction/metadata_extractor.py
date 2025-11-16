# -*- coding: utf-8 -*-
"""
Metadata Extraction System

Extracts document metadata from multiple sources:
- PDF metadata (title, author, subject)
- Zotero library
- User prompts (fallback)

Author: Claude Code
Date: 2025-01-21
Version: 1.0
"""

import sys
import os

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

from pathlib import Path
from typing import Dict, Optional, List, Any
import fitz  # PyMuPDF
import re


class MetadataExtractor:
    """Extract document metadata from PDFs and Zotero."""

    def __init__(self, zotero_db_path: Optional[Path] = None):
        """
        Initialize metadata extractor.

        Args:
            zotero_db_path: Path to Zotero SQLite database
        """
        self.zotero_db_path = zotero_db_path

    def extract_from_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            'title': None,
            'authors': [],
            'year': None,
            'subject': None,
            'keywords': [],
            'creator': None,
            'producer': None
        }

        try:
            doc = fitz.open(pdf_path)

            # Get PDF metadata
            pdf_meta = doc.metadata

            if pdf_meta:
                metadata['title'] = pdf_meta.get('title')
                metadata['subject'] = pdf_meta.get('subject')
                metadata['creator'] = pdf_meta.get('creator')
                metadata['producer'] = pdf_meta.get('producer')

                # Parse author
                author_str = pdf_meta.get('author', '')
                if author_str:
                    # Split by common delimiters
                    authors = re.split(r'[,;]|\s+and\s+', author_str)
                    metadata['authors'] = [a.strip() for a in authors if a.strip()]

                # Extract year from creation date
                creation_date = pdf_meta.get('creationDate', '')
                year_match = re.search(r'(\d{4})', creation_date)
                if year_match:
                    metadata['year'] = int(year_match.group(1))

                # Parse keywords
                keywords_str = pdf_meta.get('keywords', '')
                if keywords_str:
                    keywords = re.split(r'[,;]', keywords_str)
                    metadata['keywords'] = [k.strip() for k in keywords if k.strip()]

            doc.close()

        except Exception as e:
            print(f"⚠️  PDF metadata extraction failed: {e}")

        return metadata

    def infer_from_filename(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Infer metadata from filename.

        Common patterns:
        - Ch-04_Heat_Transfer.pdf → Chapter 4
        - Smith2020_ConvectiveHeatTransfer.pdf → Smith 2020

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with inferred metadata
        """
        metadata = {
            'chapter_number': None,
            'chapter_title': None,
            'inferred_author': None,
            'inferred_year': None
        }

        filename = pdf_path.stem

        # Pattern: Ch-04_Heat_Transfer
        chapter_match = re.match(r'[Cc]h-?(\d+)[_-](.+)', filename)
        if chapter_match:
            metadata['chapter_number'] = int(chapter_match.group(1))
            title = chapter_match.group(2).replace('_', ' ').replace('-', ' ')
            metadata['chapter_title'] = title.title()

        # Pattern: Smith2020_Title
        author_year_match = re.match(r'([A-Z][a-z]+)(\d{4})', filename)
        if author_year_match:
            metadata['inferred_author'] = author_year_match.group(1)
            metadata['inferred_year'] = int(author_year_match.group(2))

        return metadata

    def extract_from_zotero(self, pdf_path: Path) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from Zotero database.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with Zotero metadata or None
        """
        if not self.zotero_db_path or not self.zotero_db_path.exists():
            return None

        try:
            import sqlite3

            conn = sqlite3.connect(self.zotero_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Search for PDF by filename
            cursor.execute("""
                SELECT
                    i.itemID,
                    i.key as zotero_key,
                    iv.value as title,
                    GROUP_CONCAT(c.firstName || ' ' || c.lastName, '; ') as authors
                FROM items i
                LEFT JOIN itemData id ON i.itemID = id.itemID
                LEFT JOIN itemDataValues iv ON id.valueID = iv.valueID
                LEFT JOIN itemCreators ic ON i.itemID = ic.itemID
                LEFT JOIN creators c ON ic.creatorID = c.creatorID
                LEFT JOIN itemAttachments ia ON i.itemID = ia.parentItemID
                WHERE ia.path LIKE ?
                GROUP BY i.itemID
                LIMIT 1
            """, (f'%{pdf_path.name}%',))

            row = cursor.fetchone()

            if row:
                metadata = {
                    'zotero_key': row['zotero_key'],
                    'title': row['title'],
                    'authors': row['authors'].split('; ') if row['authors'] else []
                }

                conn.close()
                return metadata

            conn.close()

        except Exception as e:
            print(f"⚠️  Zotero metadata extraction failed: {e}")

        return None

    def merge_metadata(self,
                      pdf_meta: Dict[str, Any],
                      zotero_meta: Optional[Dict[str, Any]],
                      filename_meta: Dict[str, Any],
                      user_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Merge metadata from multiple sources with priority.

        Priority: User > Zotero > PDF > Filename

        Args:
            pdf_meta: Metadata from PDF
            zotero_meta: Metadata from Zotero
            filename_meta: Metadata inferred from filename
            user_meta: User-provided metadata (highest priority)

        Returns:
            Merged metadata dictionary
        """
        merged = {}

        # Start with filename inferences (lowest priority)
        merged.update(filename_meta)

        # Overlay PDF metadata
        for key, value in pdf_meta.items():
            if value:
                merged[key] = value

        # Overlay Zotero metadata (higher priority)
        if zotero_meta:
            for key, value in zotero_meta.items():
                if value:
                    merged[key] = value

        # Overlay user metadata (highest priority)
        if user_meta:
            for key, value in user_meta.items():
                if value is not None:
                    merged[key] = value

        return merged

    def extract_complete_metadata(self,
                                  pdf_path: Path,
                                  user_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract complete metadata from all available sources.

        Args:
            pdf_path: Path to PDF file
            user_metadata: User-provided metadata (optional)

        Returns:
            Complete merged metadata
        """
        print(f"\n{'='*80}")
        print(f"METADATA EXTRACTION")
        print(f"{'='*80}")
        print(f"PDF: {pdf_path}")
        print()

        # Extract from all sources
        print("📄 Extracting PDF metadata...")
        pdf_meta = self.extract_from_pdf(pdf_path)

        print("📁 Inferring from filename...")
        filename_meta = self.infer_from_filename(pdf_path)

        print("📚 Checking Zotero database...")
        zotero_meta = self.extract_from_zotero(pdf_path)

        # Merge all sources
        print("🔀 Merging metadata...")
        complete_meta = self.merge_metadata(pdf_meta, zotero_meta, filename_meta, user_metadata)

        # Display results
        print()
        print("Extracted Metadata:")
        for key, value in complete_meta.items():
            if value:
                print(f"  {key}: {value}")

        print()
        return complete_meta


if __name__ == "__main__":
    # Test metadata extraction
    test_pdf = Path("tests/test_data/Ch-04_Heat_Transfer.pdf")

    extractor = MetadataExtractor()
    metadata = extractor.extract_complete_metadata(test_pdf)

    print(f"\n✅ Metadata extraction complete")
