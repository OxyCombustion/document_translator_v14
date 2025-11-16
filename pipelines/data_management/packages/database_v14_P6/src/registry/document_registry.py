# -*- coding: utf-8 -*-
"""
Document Registry Manager - Core Database System

This module provides the central interface for managing the document registry database,
including document metadata, extractions, objects, search, and validation.

Key Features:
- Document registration (books, papers, manuals, standards)
- Extraction tracking and versioning
- Object-level metadata (equations, tables, figures, text)
- Full-text search (FTS5)
- Cross-reference management
- Validation and quality tracking

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

import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class DocumentMetadata:
    """Complete document metadata."""
    doc_id: str
    doc_type: str
    title: str
    authors: List[str]
    year: Optional[int] = None
    isbn: Optional[str] = None
    doi: Optional[str] = None
    zotero_key: Optional[str] = None
    subject_areas: Optional[List[str]] = None
    language: str = 'en'
    abstract: Optional[str] = None
    keywords: Optional[List[str]] = None

    # Type-specific metadata (populated based on doc_type)
    # Books
    edition: Optional[str] = None
    publisher: Optional[str] = None
    total_chapters: Optional[int] = None
    volume: Optional[str] = None
    series: Optional[str] = None

    # Papers
    journal: Optional[str] = None
    paper_volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    conference: Optional[str] = None
    conference_location: Optional[str] = None
    conference_date: Optional[str] = None
    peer_reviewed: bool = True
    open_access: bool = False

    # Manuals
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    manual_type: Optional[str] = None
    revision: Optional[str] = None

    # Standards
    standard_body: Optional[str] = None
    standard_number: Optional[str] = None
    status: Optional[str] = None
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None


@dataclass
class ExtractionMetadata:
    """Extraction tracking metadata."""
    extraction_id: str
    doc_id: str
    pdf_file: str
    pdf_hash: str
    output_directory: str
    chapter_number: Optional[int] = None
    chapter_title: Optional[str] = None
    section_id: Optional[str] = None
    extraction_date: Optional[str] = None
    pipeline_version: str = 'v13.1.0'
    status: str = 'complete'
    error_message: Optional[str] = None
    processing_time_seconds: Optional[float] = None


class DocumentRegistry:
    """
    Central document registry and metadata management system.

    This class provides the core interface for:
    - Registering documents and their metadata
    - Tracking extractions and versions
    - Managing extracted objects
    - Full-text and semantic search
    - Validation and quality tracking
    """

    def __init__(self, db_path: str = "databases/document_registry.db"):
        """
        Initialize document registry.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self.conn = None
        self._initialize_database()

    def _initialize_database(self):
        """Initialize database with schema if needed."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Access columns by name

        # Load and execute schema
        schema_path = Path(__file__).parent / 'schema.sql'
        if schema_path.exists():
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
                self.conn.executescript(schema_sql)
                self.conn.commit()
        else:
            print(f"⚠️  Schema file not found: {schema_path}")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    # =========================================================================
    # DOCUMENT REGISTRATION
    # =========================================================================

    def register_document(self, metadata: DocumentMetadata) -> str:
        """
        Register a new document in the registry.

        Args:
            metadata: Complete document metadata

        Returns:
            doc_id of registered document
        """
        cursor = self.conn.cursor()

        # Insert into main documents table
        cursor.execute("""
            INSERT OR REPLACE INTO documents
            (doc_id, doc_type, title, authors, year, isbn, doi, zotero_key,
             subject_areas, language, abstract, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.doc_id,
            metadata.doc_type,
            metadata.title,
            json.dumps(metadata.authors) if metadata.authors else None,
            metadata.year,
            metadata.isbn,
            metadata.doi,
            metadata.zotero_key,
            json.dumps(metadata.subject_areas) if metadata.subject_areas else None,
            metadata.language,
            metadata.abstract,
            json.dumps(metadata.keywords) if metadata.keywords else None
        ))

        # Insert type-specific metadata
        if metadata.doc_type == 'book':
            cursor.execute("""
                INSERT OR REPLACE INTO books
                (doc_id, edition, publisher, total_chapters, volume, series)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                metadata.doc_id,
                metadata.edition,
                metadata.publisher,
                metadata.total_chapters,
                metadata.volume,
                metadata.series
            ))

        elif metadata.doc_type == 'paper':
            cursor.execute("""
                INSERT OR REPLACE INTO papers
                (doc_id, journal, volume, issue, pages, conference,
                 conference_location, conference_date, peer_reviewed, open_access)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.doc_id,
                metadata.journal,
                metadata.paper_volume,
                metadata.issue,
                metadata.pages,
                metadata.conference,
                metadata.conference_location,
                metadata.conference_date,
                metadata.peer_reviewed,
                metadata.open_access
            ))

        elif metadata.doc_type == 'manual':
            cursor.execute("""
                INSERT OR REPLACE INTO manuals
                (doc_id, manufacturer, model, manual_type, revision)
                VALUES (?, ?, ?, ?, ?)
            """, (
                metadata.doc_id,
                metadata.manufacturer,
                metadata.model,
                metadata.manual_type,
                metadata.revision
            ))

        elif metadata.doc_type == 'standard':
            cursor.execute("""
                INSERT OR REPLACE INTO standards
                (doc_id, standard_body, standard_number, status, supersedes, superseded_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                metadata.doc_id,
                metadata.standard_body,
                metadata.standard_number,
                metadata.status,
                metadata.supersedes,
                metadata.superseded_by
            ))

        self.conn.commit()
        return metadata.doc_id

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete document metadata.

        Args:
            doc_id: Document identifier

        Returns:
            Dictionary with complete metadata or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM v_documents_complete WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def find_documents(self,
                      doc_type: Optional[str] = None,
                      subject: Optional[str] = None,
                      year_min: Optional[int] = None,
                      year_max: Optional[int] = None,
                      author: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for documents by criteria.

        Args:
            doc_type: Filter by document type
            subject: Filter by subject area (partial match)
            year_min: Minimum year
            year_max: Maximum year
            author: Filter by author name (partial match)

        Returns:
            List of matching documents
        """
        cursor = self.conn.cursor()

        query = "SELECT * FROM v_documents_complete WHERE 1=1"
        params = []

        if doc_type:
            query += " AND doc_type = ?"
            params.append(doc_type)

        if subject:
            query += " AND subject_areas LIKE ?"
            params.append(f'%{subject}%')

        if year_min:
            query += " AND year >= ?"
            params.append(year_min)

        if year_max:
            query += " AND year <= ?"
            params.append(year_max)

        if author:
            query += " AND authors LIKE ?"
            params.append(f'%{author}%')

        query += " ORDER BY year DESC, title"

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # EXTRACTION TRACKING
    # =========================================================================

    def register_extraction(self, metadata: ExtractionMetadata) -> str:
        """
        Register a new extraction.

        Args:
            metadata: Extraction metadata

        Returns:
            extraction_id
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO extractions
            (extraction_id, doc_id, chapter_number, chapter_title, section_id,
             pdf_file, pdf_hash, extraction_date, pipeline_version,
             output_directory, status, error_message, processing_time_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.extraction_id,
            metadata.doc_id,
            metadata.chapter_number,
            metadata.chapter_title,
            metadata.section_id,
            metadata.pdf_file,
            metadata.pdf_hash,
            metadata.extraction_date or datetime.now().isoformat(),
            metadata.pipeline_version,
            metadata.output_directory,
            metadata.status,
            metadata.error_message,
            metadata.processing_time_seconds
        ))

        self.conn.commit()
        return metadata.extraction_id

    def get_extraction(self, extraction_id: str) -> Optional[Dict[str, Any]]:
        """Get extraction metadata."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM v_extraction_summary WHERE extraction_id = ?", (extraction_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def find_extractions(self,
                        doc_id: Optional[str] = None,
                        status: Optional[str] = None,
                        chapter_number: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Find extractions by criteria.

        Args:
            doc_id: Filter by document
            status: Filter by status
            chapter_number: Filter by chapter number

        Returns:
            List of matching extractions
        """
        cursor = self.conn.cursor()

        query = "SELECT * FROM v_extraction_summary WHERE 1=1"
        params = []

        if doc_id:
            query += " AND doc_id = ?"
            params.append(doc_id)

        if status:
            query += " AND status = ?"
            params.append(status)

        if chapter_number is not None:
            query += " AND chapter_number = ?"
            params.append(chapter_number)

        query += " ORDER BY extraction_date DESC"

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # OBJECT MANAGEMENT
    # =========================================================================

    def add_extracted_object(self,
                            extraction_id: str,
                            object_type: str,
                            page_number: int,
                            bbox: List[float],
                            object_number: Optional[str] = None,
                            file_path: Optional[str] = None,
                            confidence: Optional[float] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add an extracted object to the database.

        Args:
            extraction_id: Parent extraction
            object_type: 'equation', 'table', 'figure', 'text_block'
            page_number: Page number (1-indexed)
            bbox: Bounding box [x0, y0, x1, y1]
            object_number: Object number/identifier
            file_path: Relative path to extracted file
            confidence: Detection confidence (0-1)
            metadata: Additional metadata (LaTeX, caption, etc.)

        Returns:
            object_id
        """
        # Generate object_id
        object_id = f"{extraction_id}_{object_type}_{page_number}_{object_number or 'unnumbered'}"

        cursor = self.conn.cursor()

        # Insert main object record
        cursor.execute("""
            INSERT OR REPLACE INTO extracted_objects
            (object_id, extraction_id, object_type, object_number,
             page_number, bbox, file_path, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            object_id,
            extraction_id,
            object_type,
            object_number,
            page_number,
            json.dumps(bbox),
            file_path,
            confidence
        ))

        # Insert metadata if provided
        if metadata:
            cursor.execute("""
                INSERT OR REPLACE INTO object_metadata
                (object_id, latex_code, caption, table_data, image_format,
                 text_content, notes, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                object_id,
                metadata.get('latex_code'),
                metadata.get('caption'),
                json.dumps(metadata.get('table_data')) if metadata.get('table_data') else None,
                metadata.get('image_format'),
                metadata.get('text_content'),
                metadata.get('notes'),
                json.dumps(metadata)
            ))

        self.conn.commit()
        return object_id

    # =========================================================================
    # FULL-TEXT SEARCH
    # =========================================================================

    def index_extraction_for_search(self,
                                    extraction_id: str,
                                    chapter_title: Optional[str] = None,
                                    text_content: Optional[str] = None,
                                    table_content: Optional[str] = None,
                                    equation_latex: Optional[str] = None,
                                    figure_captions: Optional[str] = None,
                                    bibliography_text: Optional[str] = None):
        """
        Add extraction to full-text search index.

        Args:
            extraction_id: Extraction to index
            chapter_title: Chapter/document title
            text_content: Combined text content
            table_content: Combined table content
            equation_latex: Combined LaTeX content
            figure_captions: Combined figure captions
            bibliography_text: Combined bibliography entries
        """
        # Get doc_id for this extraction
        cursor = self.conn.cursor()
        cursor.execute("SELECT doc_id FROM extractions WHERE extraction_id = ?", (extraction_id,))
        row = cursor.fetchone()

        if not row:
            return

        doc_id = row['doc_id']

        cursor.execute("""
            INSERT OR REPLACE INTO extraction_search
            (extraction_id, doc_id, chapter_title, text_content, table_content,
             equation_latex, figure_captions, bibliography_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            extraction_id,
            doc_id,
            chapter_title,
            text_content,
            table_content,
            equation_latex,
            figure_captions,
            bibliography_text
        ))

        self.conn.commit()

    def search_full_text(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Perform full-text search across all extractions.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching extractions with snippets
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                s.extraction_id,
                s.doc_id,
                s.chapter_title,
                d.title AS document_title,
                d.doc_type,
                snippet(extraction_search, 2, '<b>', '</b>', '...', 50) AS snippet,
                rank
            FROM extraction_search s
            JOIN documents d ON s.doc_id = d.doc_id
            WHERE extraction_search MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))

        return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    @staticmethod
    def compute_pdf_hash(pdf_path: Path) -> str:
        """Compute SHA256 hash of PDF file."""
        sha256_hash = hashlib.sha256()
        with open(pdf_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def generate_doc_id(title: str, year: Optional[int] = None, author: Optional[str] = None) -> str:
        """
        Generate a human-readable document ID slug.

        Args:
            title: Document title
            year: Publication year
            author: Primary author

        Returns:
            Slug like 'steam_generation_and_use_babcock_wilcox_41ed_2005'
        """
        import re

        # Clean title
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '_', slug)

        # Add author if provided
        if author:
            author_slug = author.lower().split()[-1]  # Last name
            author_slug = re.sub(r'[^\w]', '', author_slug)
            slug = f"{slug}_{author_slug}"

        # Add year if provided
        if year:
            slug = f"{slug}_{year}"

        # Limit length
        if len(slug) > 100:
            slug = slug[:100]

        return slug

    @staticmethod
    def generate_extraction_id(doc_id: str, chapter_number: Optional[int] = None) -> str:
        """
        Generate extraction ID.

        Args:
            doc_id: Parent document ID
            chapter_number: Chapter number if applicable

        Returns:
            Extraction ID like 'steam_2005_ch04_20250121_143022'
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if chapter_number is not None:
            return f"{doc_id}_ch{chapter_number:02d}_{timestamp}"
        else:
            return f"{doc_id}_{timestamp}"

    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        cursor = self.conn.cursor()

        stats = {}

        # Document counts by type
        cursor.execute("""
            SELECT doc_type, COUNT(*) as count
            FROM documents
            GROUP BY doc_type
        """)
        stats['documents_by_type'] = {row['doc_type']: row['count'] for row in cursor.fetchall()}

        # Total extractions
        cursor.execute("SELECT COUNT(*) as count FROM extractions")
        stats['total_extractions'] = cursor.fetchone()['count']

        # Total objects by type
        cursor.execute("""
            SELECT object_type, COUNT(*) as count
            FROM extracted_objects
            GROUP BY object_type
        """)
        stats['objects_by_type'] = {row['object_type']: row['count'] for row in cursor.fetchall()}

        # Total documents
        cursor.execute("SELECT COUNT(*) as count FROM documents")
        stats['total_documents'] = cursor.fetchone()['count']

        return stats


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_book_metadata(title: str,
                        authors: List[str],
                        year: int,
                        edition: Optional[str] = None,
                        publisher: Optional[str] = None,
                        **kwargs) -> DocumentMetadata:
    """Create book metadata object."""
    doc_id = DocumentRegistry.generate_doc_id(title, year, authors[0] if authors else None)

    return DocumentMetadata(
        doc_id=doc_id,
        doc_type='book',
        title=title,
        authors=authors,
        year=year,
        edition=edition,
        publisher=publisher,
        **kwargs
    )


if __name__ == "__main__":
    # Test database initialization
    print("Initializing document registry database...")
    registry = DocumentRegistry()

    print(f"✅ Database initialized: {registry.db_path}")
    print(f"📊 Statistics: {registry.get_statistics()}")

    registry.close()
