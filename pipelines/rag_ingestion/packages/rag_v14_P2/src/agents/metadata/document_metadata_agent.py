#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Metadata Agent - Bibliographic Information Extraction

Orchestrates metadata extraction with multi-source strategy:
1. Zotero database (if available) → complete citations
2. PDF header/footer extraction → book/chapter info
3. Web search → supplemental information
4. User prompt → only if critical fields missing

Key Features:
-------------
- **Zotero-First Strategy**: Use existing library metadata when available
- **Metadata Caching**: Extract once per document, reuse for all pages
- **Document Fingerprinting**: Detect when source document changes
- **Multi-Source Fallback**: PDF → Web → User prompt chain
- **Type Detection**: Journal articles vs books vs technical reports

Author: Claude Code
Date: 2025-10-03
Version: 1.0
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import hashlib
from datetime import datetime
import fitz  # PyMuPDF

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


class DocumentMetadataAgent:
    """
    Extract and cache document bibliographic metadata.

    Intelligent metadata extraction with multiple sources:
    - Zotero library (preferred, complete citations)
    - PDF internal metadata and headers/footers
    - Web search for missing fields
    - User input as last resort

    Caching Strategy:
    ----------------
    Metadata extracted once per source document and cached to avoid
    redundant work when processing multiple pages from same source.

    Usage Example:
    --------------
    >>> from zotero_integration_agent import ZoteroIntegrationAgent
    >>>
    >>> zotero = ZoteroIntegrationAgent(Path("C:/Users/.../Zotero"))
    >>> agent = DocumentMetadataAgent(
    ...     output_dir=Path("results/rag_extractions"),
    ...     zotero_agent=zotero
    ... )
    >>>
    >>> # First page: extract metadata
    >>> metadata = agent.get_or_extract_metadata("chapter4.pdf")
    >>> # Pages 2-34: reuse cached metadata
    >>> metadata = agent.get_or_extract_metadata("chapter4.pdf")  # Instant!
    """

    def __init__(
        self,
        output_dir: Path,
        zotero_agent=None
    ):
        """
        Initialize document metadata agent.

        Args:
            output_dir: Directory for metadata cache
            zotero_agent: Optional ZoteroIntegrationAgent instance
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.zotero = zotero_agent
        self.cache_file = self.output_dir / "document_metadata.json"

    def get_or_extract_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Get metadata with smart caching.

        Checks cache first. If document unchanged, returns cached metadata.
        If new document or changed, extracts fresh metadata and updates cache.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Complete metadata dictionary
        """
        pdf_path = Path(pdf_path)

        # Generate document fingerprint
        fingerprint = self._get_document_fingerprint(pdf_path)

        # Check cache
        cached_metadata = self._load_cache()

        if cached_metadata and cached_metadata.get('fingerprint') == fingerprint:
            print(f"✅ Using cached metadata: {cached_metadata.get('title', 'Untitled')}")
            return cached_metadata

        # New document - extract metadata
        print(f"📝 Extracting metadata for: {pdf_path.name}")
        metadata = self._extract_metadata(pdf_path)
        metadata['fingerprint'] = fingerprint

        # Save to cache
        self._save_cache(metadata)

        return metadata

    def _get_document_fingerprint(self, pdf_path: Path) -> str:
        """
        Generate unique fingerprint for document.

        Uses filename, file size, and first/last page headers to detect
        when processing a different document (e.g., different chapter).

        Args:
            pdf_path: Path to PDF file

        Returns:
            SHA256 hash string
        """
        components = []

        # Filename
        components.append(pdf_path.name)

        # File size
        components.append(str(pdf_path.stat().st_size))

        # Sample first and last page headers/footers
        try:
            doc = fitz.open(pdf_path)
            header_sample = ""

            # First page header
            if len(doc) > 0:
                page = doc[0]
                text = page.get_text('dict')
                # Get text from top 100 pixels
                for block in text['blocks']:
                    if 'lines' in block and block['bbox'][1] < 100:
                        for line in block['lines']:
                            for span in line['spans']:
                                header_sample += span['text']

            # Last page header (detect chapter changes)
            if len(doc) > 1:
                page = doc[-1]
                text = page.get_text('dict')
                for block in text['blocks']:
                    if 'lines' in block and block['bbox'][1] < 100:
                        for line in block['lines']:
                            for span in line['spans']:
                                header_sample += span['text']

            components.append(header_sample)
            doc.close()

        except Exception as e:
            print(f"   ⚠️  Could not sample headers: {e}")
            components.append("no_header_sample")

        # Generate hash
        fingerprint_str = '|'.join(components)
        return hashlib.sha256(fingerprint_str.encode('utf-8')).hexdigest()[:16]

    def _extract_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from all available sources.

        Strategy:
        1. Try Zotero first (complete, accurate)
        2. Extract from PDF headers/footers
        3. Web search for missing fields
        4. Prompt user if critical fields missing

        Args:
            pdf_path: Path to PDF file

        Returns:
            Complete metadata dictionary
        """
        metadata = {
            'extraction_date': datetime.now().isoformat(),
            'pdf_path': str(pdf_path),
            'pdf_filename': pdf_path.name
        }

        # Strategy 1: Try Zotero
        if self.zotero:
            print("   🔍 Searching Zotero library...")
            zotero_metadata = self._get_from_zotero(pdf_path)

            if zotero_metadata:
                print(f"   ✅ Found in Zotero: {zotero_metadata.get('title', 'Untitled')}")
                metadata.update(zotero_metadata)
                metadata['source'] = 'zotero'
                return metadata

            print("   ℹ️  Not found in Zotero, trying PDF extraction...")

        # Strategy 2: Extract from PDF
        print("   📄 Extracting from PDF headers/footers...")
        pdf_metadata = self._extract_from_pdf(pdf_path)
        metadata.update(pdf_metadata)

        # Detect document type
        doc_type = self._detect_document_type(pdf_metadata)
        metadata['document_type'] = doc_type

        # Strategy 3: Web search for missing fields (if needed)
        if not self._is_complete(metadata):
            print("   🌐 Searching web for additional information...")
            web_metadata = self._web_search_supplement(metadata)
            metadata.update(web_metadata)

        # Strategy 4: Prompt user if still incomplete
        if not self._is_complete(metadata):
            missing_fields = self._get_missing_fields(metadata)
            print(f"   ⚠️  Missing fields: {', '.join(missing_fields)}")
            print("   💬 User input may be needed for complete citation")

        metadata['source'] = 'pdf_extraction'
        return metadata

    def _get_from_zotero(self, pdf_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get metadata from Zotero library.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Zotero metadata or None if not found
        """
        if not self.zotero:
            return None

        try:
            # Find item in Zotero
            item = self.zotero.find_item_by_pdf(pdf_path)

            if not item:
                return None

            # Get complete metadata
            zotero_metadata = self.zotero.get_metadata(item['zotero_key'])

            # Generate document ID
            doc_id = self.zotero.generate_document_id(item['zotero_key'])
            zotero_metadata['document_id'] = doc_id

            # Get citation
            citation = self.zotero.get_citation(item['zotero_key'])
            zotero_metadata['citation'] = citation

            return zotero_metadata

        except Exception as e:
            print(f"   ⚠️  Zotero lookup failed: {e}")
            return None

    def _extract_from_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from PDF headers, footers, and properties.

        Looks for:
        - Book title in footers (e.g., "Steam 42 / Heat Transfer")
        - Author/publisher in headers (e.g., "The Babcock & Wilcox Company")
        - Chapter information
        - PDF metadata properties

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted metadata dictionary
        """
        metadata = {}

        try:
            doc = fitz.open(pdf_path)

            # Get first page for analysis
            if len(doc) > 0:
                page = doc[0]
                page_height = page.rect.height

                # Extract header text (top 100px)
                header_text = ""
                text_dict = page.get_text('dict')
                for block in text_dict['blocks']:
                    if 'lines' in block and block['bbox'][1] < 100:
                        for line in block['lines']:
                            for span in line['spans']:
                                header_text += span['text'] + " "

                # Extract footer text (bottom 100px)
                footer_text = ""
                for block in text_dict['blocks']:
                    if 'lines' in block and block['bbox'][1] > page_height - 100:
                        for line in block['lines']:
                            for span in line['spans']:
                                footer_text += span['text'] + " "

                # Parse header (usually author/publisher)
                header_text = header_text.strip()
                if header_text:
                    metadata['author_organization'] = header_text

                # Parse footer (usually book title and chapter)
                footer_text = footer_text.strip()
                if footer_text:
                    # Pattern: "BookTitle Edition / Chapter"
                    # Example: "Steam 42 / Heat Transfer"
                    parts = footer_text.split('/')

                    if len(parts) >= 2:
                        # Book title with edition
                        book_part = parts[0].strip()
                        metadata['book_title_raw'] = book_part

                        # Try to extract edition number
                        import re
                        edition_match = re.search(r'(\d+)(st|nd|rd|th)?$', book_part)
                        if edition_match:
                            metadata['edition'] = edition_match.group(1)
                            book_title = book_part[:edition_match.start()].strip()
                            metadata['book_title'] = book_title
                        else:
                            metadata['book_title'] = book_part

                        # Chapter title
                        chapter_part = parts[1].strip()
                        metadata['chapter_title'] = chapter_part

            # Get PDF properties
            pdf_metadata = doc.metadata
            if pdf_metadata:
                if pdf_metadata.get('title'):
                    metadata['pdf_title'] = pdf_metadata['title']
                if pdf_metadata.get('author'):
                    metadata['pdf_author'] = pdf_metadata['author']
                if pdf_metadata.get('subject'):
                    metadata['pdf_subject'] = pdf_metadata['subject']

            metadata['page_count'] = len(doc)
            doc.close()

        except Exception as e:
            print(f"   ⚠️  PDF extraction failed: {e}")

        return metadata

    def _detect_document_type(self, metadata: Dict[str, Any]) -> str:
        """
        Detect document type from metadata.

        Types:
        - journal_article: Has DOI, journal name
        - book_chapter: Has book title, chapter info
        - book: Has ISBN, book title, no chapter
        - technical_report: Has report number
        - unknown: Cannot determine

        Args:
            metadata: Extracted metadata

        Returns:
            Document type string
        """
        if metadata.get('doi'):
            return 'journal_article'

        if metadata.get('chapter_title') or metadata.get('book_title'):
            return 'book_chapter'

        if metadata.get('isbn'):
            return 'book'

        return 'unknown'

    def _web_search_supplement(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search web for missing metadata fields.

        Uses book title, edition, and author to find ISBN, publisher, year.

        Args:
            metadata: Partially complete metadata

        Returns:
            Supplemental metadata from web
        """
        supplemental = {}

        # Build search query
        query_parts = []
        if metadata.get('book_title'):
            query_parts.append(metadata['book_title'])
        if metadata.get('edition'):
            query_parts.append(f"{metadata['edition']}th edition")
        if metadata.get('author_organization'):
            query_parts.append(metadata['author_organization'])

        if not query_parts:
            return supplemental

        query = ' '.join(query_parts)

        try:
            from tools import WebSearch

            print(f"   Searching: {query}")
            # Search for book information
            # Note: WebSearch tool would be used here
            # For now, placeholder

            # TODO: Parse search results for ISBN, year, publisher

        except Exception as e:
            print(f"   ⚠️  Web search failed: {e}")

        return supplemental

    def _is_complete(self, metadata: Dict[str, Any]) -> bool:
        """
        Check if metadata has all essential fields.

        Essential fields vary by document type:
        - Journal article: title, authors, journal, year, DOI
        - Book chapter: book title, chapter, authors, year, edition
        - Book: title, authors, ISBN, year, publisher

        Args:
            metadata: Metadata dictionary

        Returns:
            True if complete, False if missing essential fields
        """
        doc_type = metadata.get('document_type', 'unknown')

        if doc_type == 'journal_article':
            required = ['title', 'authors', 'publication', 'year', 'doi']
        elif doc_type == 'book_chapter':
            required = ['book_title', 'chapter_title', 'author_organization']
        elif doc_type == 'book':
            required = ['title', 'author', 'isbn', 'year']
        else:
            # Unknown type, consider complete if has any identifiable info
            return bool(metadata.get('book_title') or metadata.get('title'))

        return all(metadata.get(field) for field in required)

    def _get_missing_fields(self, metadata: Dict[str, Any]) -> List[str]:
        """
        Get list of missing essential fields.

        Args:
            metadata: Metadata dictionary

        Returns:
            List of missing field names
        """
        doc_type = metadata.get('document_type', 'unknown')

        if doc_type == 'journal_article':
            required = ['title', 'authors', 'publication', 'year', 'doi']
        elif doc_type == 'book_chapter':
            required = ['book_title', 'chapter_title', 'author_organization', 'edition', 'year']
        elif doc_type == 'book':
            required = ['title', 'author', 'isbn', 'year', 'publisher']
        else:
            return []

        return [field for field in required if not metadata.get(field)]

    def _load_cache(self) -> Optional[Dict[str, Any]]:
        """Load cached metadata if exists."""
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"   ⚠️  Cache load failed: {e}")
            return None

    def _save_cache(self, metadata: Dict[str, Any]):
        """Save metadata to cache."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            print(f"   💾 Metadata cached to: {self.cache_file}")
        except Exception as e:
            print(f"   ⚠️  Cache save failed: {e}")


def main():
    """Test document metadata extraction."""
    print("Testing Document Metadata Agent...")

    # Initialize
    from zotero_integration_agent import ZoteroIntegrationAgent

    zotero = ZoteroIntegrationAgent(Path(r"C:\Users\Tom Ochs i9\Zotero"))
    agent = DocumentMetadataAgent(
        output_dir=Path("results/rag_extractions"),
        zotero_agent=zotero
    )

    # Test with sample PDF
    pdf_path = Path("tests/test_data/Ch-04_Heat_Transfer.pdf")

    print("\n=== Test 1: Extract metadata ===")
    metadata = agent.get_or_extract_metadata(pdf_path)

    print("\n=== Extracted Metadata ===")
    for key, value in metadata.items():
        if key != 'fingerprint':
            print(f"  {key}: {value}")

    print("\n=== Test 2: Use cached metadata ===")
    metadata2 = agent.get_or_extract_metadata(pdf_path)
    # Should be instant, from cache

    print("\n✅ Document metadata test complete")


if __name__ == "__main__":
    main()
