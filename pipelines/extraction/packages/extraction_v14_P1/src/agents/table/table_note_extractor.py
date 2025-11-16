#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Table Note Extractor - Multi-Strategy Note Detection

This is a helper class (not an agent) that implements multiple strategies
for extracting table notes. It's used by TableExtractionAgent to find notes
associated with tables.

Design Rationale:
-----------------
- **Multi-Strategy**: Different tables have notes in different locations
  - Inside table: "Notes:" row followed by note text rows
  - Below table: Text within 400px below table bbox
  - Next page: Note continues on next page
  - Image-based: Notes in non-searchable image format

- **Cascading Fallback**: Try strategies in order until one succeeds
- **Generic & Reusable**: Works for any table in any document
- **No State**: Pure function approach, no instance variables
- **Testable**: Each strategy can be unit tested independently

Alternatives Considered:
------------------------
1. Single strategy (400px search): Misses notes in other locations
2. ML-based detection: Overkill, adds complexity and training requirements
3. Always extract full page: Too much noise, hard to separate notes from body text

Usage:
------
>>> from table_note_extractor import TableNoteExtractor
>>> extractor = TableNoteExtractor(pdf_path, pdf_doc)
>>> notes = extractor.extract_notes(table_zone)
"""

import sys
import os
from pathlib import Path
from typing import Optional, List, Tuple
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

# Import using proper v14 package structure (no sys.path manipulation)
from pipelines.shared.packages.common.src.base.base_extraction_agent import Zone


class TableNoteExtractor:
    """
    Multi-strategy table note extraction.

    This is NOT an agent - it's a helper class used by TableExtractionAgent.
    It encapsulates note extraction logic separate from table data extraction.
    """

    def __init__(self, pdf_path: Path, pdf_doc: fitz.Document):
        """
        Initialize note extractor.

        Args:
            pdf_path: Path to PDF (for reference)
            pdf_doc: Open PyMuPDF document object
        """
        self.pdf_path = pdf_path
        self.pdf_doc = pdf_doc

    def extract_notes(self, zone: Zone) -> str:
        """
        Extract notes for a table using multi-strategy approach.

        Tries strategies in order:
        1. Inside-table detection (look for "Notes:" row in table data)
        2. Below-table search (400px zone below table)
        3. Extended search (800px zone, catches further notes)
        4. Full remaining page search (entire rest of page)
        5. Full next-page search (entire next page)
        6. Multi-page search (search up to 3 pages ahead)

        Args:
            zone: Table zone to extract notes for

        Returns:
            Note text (empty string if no notes found)
        """
        # Strategy 1: Inside-table detection
        notes = self._extract_inside_table_notes(zone)
        if notes:
            return notes

        # Strategy 2: Below-table search (standard 400px)
        notes = self._extract_below_table_notes(zone, search_height=400)
        if notes:
            return notes

        # Strategy 3: Extended below-table search (800px for far notes)
        notes = self._extract_below_table_notes(zone, search_height=800)
        if notes:
            return notes

        # Strategy 4: Full remaining page search
        notes = self._extract_full_page_below_table(zone)
        if notes:
            return notes

        # Strategy 5: Full next-page search
        notes = self._extract_full_next_page_notes(zone)
        if notes:
            return notes

        # Strategy 6: Multi-page search (up to 3 pages ahead)
        notes = self._extract_multi_page_notes(zone, max_pages=3)
        if notes:
            return notes

        # No notes found
        return ""

    def _extract_inside_table_notes(self, zone: Zone) -> str:
        """
        Strategy 1: Extract notes from inside table data.

        Some tables have "Notes:" as last row, with note content in subsequent rows.
        This is detected by looking for "Notes:" marker in the zone bbox.

        Args:
            zone: Table zone

        Returns:
            Note text or empty string
        """
        try:
            page = self.pdf_doc[zone.page - 1]  # 0-indexed
            x0, y0, x1, y1 = zone.bbox

            # Extract text from table bbox
            table_text = page.get_text("text", clip=(x0, y0, x1, y1))

            # Look for "Notes:" marker
            lines = table_text.split('\n')
            note_start_idx = None

            for i, line in enumerate(lines):
                if line.strip().lower() in ['notes:', 'note:', 'notes', 'note']:
                    note_start_idx = i
                    break

            if note_start_idx is not None and note_start_idx < len(lines) - 1:
                # Extract all lines after "Notes:" marker
                note_lines = lines[note_start_idx + 1:]
                notes = '\n'.join(line.strip() for line in note_lines if line.strip())
                if notes:
                    return notes

        except Exception as e:
            print(f"      Inside-table note extraction failed: {e}")

        return ""

    def _extract_below_table_notes(self, zone: Zone, search_height: int = 400) -> str:
        """
        Strategy 2 & 3: Extract notes from below table.

        Searches a zone below the table for note text. Uses heuristics to
        identify note-like content (starts with "Note:", contains references, etc.)

        ENHANCED: Now searches full page width (not just table width) to catch
        notes that might be in adjacent columns or wider text blocks.

        Args:
            zone: Table zone
            search_height: Height of search zone in pixels (400 or 800)

        Returns:
            Note text or empty string
        """
        try:
            page = self.pdf_doc[zone.page - 1]  # 0-indexed
            x0_table, y0, x1_table, y1 = zone.bbox
            page_height = page.rect.height
            page_width = page.rect.width

            # Define search zone below table
            search_y0 = y1  # Start at bottom of table
            search_y1 = min(y1 + search_height, page_height)

            # ENHANCEMENT: Search full page width, not just table width
            # This catches notes in adjacent columns or wider text blocks
            search_x0 = 0
            search_x1 = page_width

            # Extract text from search zone
            search_text = page.get_text("text", clip=(search_x0, search_y0, search_x1, search_y1))

            # Look for note markers
            lines = search_text.split('\n')
            note_lines = []
            collecting = False

            for line in lines:
                line_lower = line.strip().lower()

                # ENHANCEMENT: More permissive note detection
                # Start collecting when we see various note markers
                if (line_lower.startswith('note:') or
                    line_lower.startswith('notes:') or
                    line_lower.startswith('note ') or
                    line_lower.startswith('notes ') or
                    'note:' in line_lower[:20]):  # Note within first 20 chars
                    collecting = True

                if collecting:
                    note_lines.append(line.strip())

                    # Stop collecting if we hit next section (all caps header)
                    if (line.strip().isupper() and
                        len(line.strip()) > 15 and
                        'NOTE' not in line.strip()):
                        break

            if note_lines:
                notes = '\n'.join(note_lines)
                # Filter out empty notes
                if len(notes.strip()) > 10:  # Minimum 10 chars for valid note
                    return notes

        except Exception as e:
            print(f"      Below-table note extraction failed: {e}")

        return ""

    def _extract_next_page_notes(self, zone: Zone) -> str:
        """
        Strategy 4: Extract notes from top of next page.

        Some tables have notes that continue on the next page. This searches
        the first 200px of the next page for note content.

        Args:
            zone: Table zone

        Returns:
            Note text or empty string
        """
        try:
            # Check if next page exists
            if zone.page >= len(self.pdf_doc):
                return ""

            next_page = self.pdf_doc[zone.page]  # zone.page is 1-indexed, so this gives next page
            x0, y0_table, x1, y1_table = zone.bbox

            # Search first 200px of next page
            search_y0 = 0
            search_y1 = 200

            # Extract text
            search_text = next_page.get_text("text", clip=(x0, search_y0, x1, search_y1))

            # Look for note markers
            lines = search_text.split('\n')
            note_lines = []
            collecting = False

            for line in lines:
                line_lower = line.strip().lower()

                if line_lower.startswith('note:') or line_lower.startswith('notes:'):
                    collecting = True

                if collecting:
                    note_lines.append(line.strip())

            if note_lines:
                notes = '\n'.join(note_lines)
                if len(notes.strip()) > 10:
                    return notes

        except Exception as e:
            print(f"      Next-page note extraction failed: {e}")

        return ""

    def _extract_full_page_below_table(self, zone: Zone) -> str:
        """
        Strategy 4: Extract notes from entire remaining page.

        Searches from table bottom to page bottom for any note content.
        More aggressive than 400px/800px strategies.

        ENHANCED: Now searches full page width to catch all possible notes.

        Args:
            zone: Table zone

        Returns:
            Note text or empty string
        """
        try:
            page = self.pdf_doc[zone.page - 1]  # 0-indexed
            x0_table, y0, x1_table, y1 = zone.bbox
            page_height = page.rect.height
            page_width = page.rect.width

            # Search from table bottom to page bottom
            search_y0 = y1
            search_y1 = page_height

            # ENHANCEMENT: Search full page width
            search_x0 = 0
            search_x1 = page_width

            # Extract text from entire remaining page
            search_text = page.get_text("text", clip=(search_x0, search_y0, search_x1, search_y1))

            # Look for note patterns
            notes = self._extract_notes_from_text(search_text)
            if notes:
                return notes

        except Exception as e:
            print(f"      Full-page note extraction failed: {e}")

        return ""

    def _extract_full_next_page_notes(self, zone: Zone) -> str:
        """
        Strategy 5: Extract notes from entire next page.

        Searches full next page for note content. Handles cases where
        notes span multiple pages or are far from table.

        ENHANCED: Now searches full page width.

        Args:
            zone: Table zone

        Returns:
            Note text or empty string
        """
        try:
            # Check if next page exists
            if zone.page >= len(self.pdf_doc):
                return ""

            next_page = self.pdf_doc[zone.page]  # zone.page is 1-indexed
            page_height = next_page.rect.height
            page_width = next_page.rect.width

            # ENHANCEMENT: Search full page width
            search_text = next_page.get_text("text", clip=(0, 0, page_width, page_height))

            # Look for note patterns
            notes = self._extract_notes_from_text(search_text)
            if notes:
                return notes

        except Exception as e:
            print(f"      Full next-page note extraction failed: {e}")

        return ""

    def _extract_multi_page_notes(self, zone: Zone, max_pages: int = 3) -> str:
        """
        Strategy 6: Extract notes from multiple pages ahead.

        Searches up to max_pages ahead for note content. Handles cases
        where notes are far from table or on distant pages.

        Args:
            zone: Table zone
            max_pages: Maximum pages to search ahead

        Returns:
            Note text or empty string
        """
        try:
            x0, y0_table, x1, y1_table = zone.bbox
            all_notes = []

            # Search each page up to max_pages ahead
            for page_offset in range(1, max_pages + 1):
                next_page_num = zone.page + page_offset
                if next_page_num >= len(self.pdf_doc):
                    break

                page = self.pdf_doc[next_page_num]
                page_height = page.rect.height

                # Extract text from full page
                search_text = page.get_text("text", clip=(x0, 0, x1, page_height))

                # Look for note patterns
                notes = self._extract_notes_from_text(search_text)
                if notes:
                    all_notes.append(notes)

            # Combine notes from all pages
            if all_notes:
                return '\n\n'.join(all_notes)

        except Exception as e:
            print(f"      Multi-page note extraction failed: {e}")

        return ""

    def _extract_notes_from_text(self, text: str) -> str:
        """
        Extract notes from text using pattern recognition.

        Looks for various note patterns:
        - "Note:" or "Notes:" markers
        - Numbered notes: "1.", "2.", etc.
        - Note references: "Note 1:", "Note 2:", etc.

        Args:
            text: Text to search for notes

        Returns:
            Extracted note text or empty string
        """
        lines = text.split('\n')
        note_lines = []
        collecting = False

        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            # Start collecting when we see note markers
            if (line_lower.startswith('note:') or
                line_lower.startswith('notes:') or
                line_lower.startswith('note ') or
                line_lower.startswith('notes ')):
                collecting = True

            if collecting:
                # Stop if we hit a new section header
                if (line_stripped.isupper() and len(line_stripped) > 10 and
                    'NOTE' not in line_stripped):
                    break

                note_lines.append(line_stripped)

        if note_lines:
            notes = '\n'.join(note_lines)
            # Filter out very short "notes" (likely false positives)
            if len(notes.strip()) > 10:
                return notes

        return ""

    def detect_note_references(self, table_text: str) -> List[str]:
        """
        Detect note references in table text (e.g., "see Note 1", "(see Note 2)").

        This helps identify which tables SHOULD have notes, even if we can't
        find them immediately.

        Args:
            table_text: Extracted table text

        Returns:
            List of note reference strings found (e.g., ["Note 1", "Note 2"])
        """
        import re

        references = []

        # Pattern 1: "(see Note 1)" or "(see Note 2)"
        pattern1 = r'\(see Note (\d+)\)'
        matches1 = re.findall(pattern1, table_text, re.IGNORECASE)
        references.extend([f"Note {num}" for num in matches1])

        # Pattern 2: "see Note 1" without parentheses
        pattern2 = r'see Note (\d+)'
        matches2 = re.findall(pattern2, table_text, re.IGNORECASE)
        references.extend([f"Note {num}" for num in matches2])

        # Pattern 3: Superscript numbers (often indicate footnotes)
        pattern3 = r'(\d+)'  # Simple digit pattern, could be enhanced
        # This is too broad, skip for now

        return list(set(references))  # Remove duplicates


if __name__ == "__main__":
    # Simple test
    pdf_path = Path("tests/test_data/Ch-04_Heat_Transfer.pdf")

    if not pdf_path.exists():
        print(f"ERROR: Test PDF not found: {pdf_path}")
        sys.exit(1)

    doc = fitz.open(str(pdf_path))
    extractor = TableNoteExtractor(pdf_path, doc)

    # Test on Table 7 (page 10) - known to have note references
    test_zone = Zone(
        zone_id="table_10_test",
        type="table",
        page=10,
        bbox=[324.08, 370.25, 575.59, 748.15],  # Approximate Table 7 bbox
        metadata={}
    )

    print("Testing Table 7 (page 10) note extraction...")
    notes = extractor.extract_notes(test_zone)

    if notes:
        print(f"✓ Notes found ({len(notes)} chars):")
        print(notes[:200] + "..." if len(notes) > 200 else notes)
    else:
        print("✗ No notes found (known issue - Table 7 notes are missing)")

    doc.close()
