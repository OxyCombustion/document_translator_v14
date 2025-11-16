#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Table Extraction Agent - RAG-Ready Structured Table Data Extraction

Extracts tables as structured data (JSON, CSV) with images and captions.
Uses Docling markdown output and converts to multiple machine-readable formats.

Key Features:
-------------
- **Structured Data**: Pandas DataFrame → JSON/CSV for ML/LLM processing
- **Markdown Preservation**: Keep Docling markdown for human readability
- **Image Extraction**: Crop table images at proper resolution
- **Caption Detection**: Auto-detect "Table X:" patterns above bbox
- **Multi-Format Output**: JSON (structured), CSV (raw data), markdown (readable)

Technical Approach:
-------------------
1. Parse Docling markdown to pandas DataFrame
2. Crop table image using bbox coordinates
3. Extract caption from text above table
4. Convert to multiple formats (JSON, CSV, markdown)
5. Build ExtractedObject with all representations

Design Rationale:
-----------------
- **Why Docling markdown**: Already provides accurate table structure
- **Why pandas**: Standard library for tabular data, easy CSV/JSON conversion
- **Why multiple formats**: Different use cases (CSV for spreadsheets, JSON for APIs)
- **Why caption detection**: Essential context for LLM understanding

Alternatives Considered:
------------------------
1. OCR-based table extraction: Rejected - Docling already provides structure
2. HTML parsing: Rejected - markdown is simpler and sufficient
3. Image-only extraction: Rejected - structured data is more useful for RAG

Author: Claude Code
Date: 2025-10-03
Version: 1.0
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import re
import io

# MANDATORY UTF-8 SETUP - NO EXCEPTIONS
if sys.platform == 'win32':
    import io as io_module
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io_module.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')
    if not hasattr(sys.stderr, '_wrapped_utf8'):
        try:
            sys.stderr = io_module.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            sys.stderr._wrapped_utf8 = True
        except (AttributeError, ValueError):
            pass

import fitz  # PyMuPDF
import pandas as pd

# Import base agent (v14 package import)
from common.src.base.base_extraction_agent import BaseExtractionAgent, Zone, ExtractedObject


class TableExtractionAgent(BaseExtractionAgent):
    """
    Specialized agent for extracting tables as structured data.

    This agent converts Docling markdown tables to multiple RAG-ready formats.

    Usage Example:
    --------------
    >>> from pathlib import Path
    >>> agent = TableExtractionAgent(
    ...     pdf_path=Path("doc.pdf"),
    ...     output_dir=Path("results/rag_extractions")
    ... )
    >>> zones = [Zone(id="table_1", type="table", page=2, bbox=[...],
    ...               metadata={"markdown": "| col1 | col2 |\\n..."})]
    >>> results = agent.process_zones(zones)
    >>> # Results contain structured JSON, CSV, markdown, images

    Output Format:
    --------------
    ExtractedObject with:
        content: {
            "structured_data": {
                "headers": ["Material", "Btu/h ft F", "W/m C"],
                "rows": [["Gases...", "0.004 to 0.70", "0.007 to 1.2"], ...]
            },
            "markdown": "| Material | Btu/h ft F | W/m C |\\n...",
            "csv_path": "results/rag_extractions/tables/table_1.csv",
            "image_path": "results/rag_extractions/tables/table_1.png"
        },
        context: {
            "caption": "Table 1 Thermal Conductivity, k, of Common Materials",
            "rows": 7,
            "columns": 3
        }
    """

    def __init__(self, pdf_path: Path, output_dir: Path):
        """
        Initialize table extraction agent.

        Args:
            pdf_path: Path to source PDF
            output_dir: Base output directory

        Raises:
            ImportError: If pandas library not installed
            FileNotFoundError: If PDF not found
        """
        super().__init__(pdf_path, output_dir)

        self.agent_type = "table_extraction"
        self.agent_version = "2.0.0"  # Bumped for enhanced markdown parsing

        # Create output subdirectories
        self.tables_dir = self.output_dir / "tables"
        self.tables_dir.mkdir(parents=True, exist_ok=True)

        # Open PDF document
        self.doc = fitz.open(str(self.pdf_path))
        print(f"📄 PDF loaded: {len(self.doc)} pages")

    def extract_from_zone(self, zone: Zone) -> Optional[ExtractedObject]:
        """
        Extract table from zone using Docling markdown.

        Process:
        --------
        1. Get markdown from zone metadata
        2. Parse markdown to pandas DataFrame
        3. Convert to JSON structured data
        4. Save as CSV
        5. Crop table image
        6. Extract caption
        7. Build ExtractedObject with all formats

        Args:
            zone: Zone containing table

        Returns:
            ExtractedObject with structured data, CSV, markdown, image
        """
        try:
            # Validate table-specific metadata
            if not zone.metadata or "markdown" not in zone.metadata:
                print(f"    ⚠️  No markdown in metadata")
                return None

            markdown = zone.metadata["markdown"]

            # Parse markdown to DataFrame
            df = self._parse_markdown_table(markdown)
            if df is None or df.empty:
                print(f"    ❌ Failed to parse markdown table")
                return None

            # Convert to structured JSON
            structured_data = self._dataframe_to_structured(df)

            # Extract notes (GENERIC: works for any table) - do this BEFORE CSV save
            notes = self._extract_notes(zone)

            # Save as CSV with notes
            csv_path = self._save_csv(zone.zone_id, df, notes)

            # Crop table image
            image_path = self._crop_table_image(zone)

            # Extract caption
            caption = self._extract_caption(zone)

            # Build ExtractedObject
            return ExtractedObject(
                id=zone.zone_id,
                type="table",
                page=zone.page,
                bbox=zone.bbox,
                content={
                    "structured_data": structured_data,
                    "markdown": markdown,
                    "csv_path": str(csv_path.relative_to(self.output_dir.parent)) if csv_path else "",
                    "image_path": str(image_path.relative_to(self.output_dir.parent)) if image_path else "",
                    "notes": notes  # ADDED: Generic note extraction
                },
                context={
                    "caption": caption,
                    "rows": len(df),
                    "columns": len(df.columns),
                    "description": "",
                    "has_notes": bool(notes)  # ADDED: Flag for downstream processing
                },
                references={
                    "mentioned_in_text": [],  # Will be filled by post-processing
                    "related_equations": [],
                    "related_figures": []
                },
                metadata={
                    "extraction_method": "docling_markdown_v2.0",
                    "parsing_library": "pandas",
                    "confidence": 1.0  # Docling markdown is highly reliable
                },
                document_id=self.document_metadata.get("document_id"),
                zotero_key=self.document_metadata.get("zotero_key")
            )

        except Exception as e:
            print(f"    ❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _parse_markdown_table(self, markdown: str) -> Optional[pd.DataFrame]:
        """
        Enhanced markdown table parser with Docling export issue handling.

        Handles Common Docling Markdown Issues:
        ---------------------------------------
        1. Repeated table caption as first row (all columns identical)
        2. Section headers spanning multiple columns (first col has text, others empty)
        3. Merged cells with multiple space-separated values
        4. Note rows that should be filtered out
        5. Malformed headers with table metadata

        Args:
            markdown: Markdown table string from Docling

        Returns:
            Cleaned DataFrame with parsed table data, or None if parsing fails
        """
        try:
            lines = markdown.strip().split('\n')
            cleaned_lines = []

            # Step 1: Detect and skip repeated caption row
            for i, line in enumerate(lines):
                # Skip alignment lines (contain only |, -, and spaces)
                if re.match(r'^\s*\|[\s\-|]+\|\s*$', line):
                    continue

                # Check if first row is repeated caption (all cells identical or contain "Table")
                if i == 0:
                    cells = [c.strip() for c in line.split('|') if c.strip()]
                    if len(cells) > 1:
                        # If all cells are identical or all contain "Table", skip this row
                        if len(set(cells)) == 1:
                            print(f"    🔧 Skipping repeated caption row: {cells[0][:50]}...")
                            continue
                        # If all cells contain "Table" and table number, skip
                        if all('Table' in c and any(char.isdigit() for char in c) for c in cells):
                            print(f"    🔧 Skipping table metadata row: {cells[0][:50]}...")
                            continue

                cleaned_lines.append(line)

            if len(cleaned_lines) < 2:  # Need at least header + 1 data row
                print(f"    ⚠️  Too few lines after cleaning: {len(cleaned_lines)}")
                return None

            # Step 2: Detect and skip section header rows
            data_lines = []
            for line in cleaned_lines:
                cells = [c.strip() for c in line.split('|')]
                # Filter out empty strings but keep structure
                non_empty_cells = [c for c in cells if c]

                # Check if this is a section header (first cell has content, rest are empty or duplicates)
                if len(non_empty_cells) >= 2:
                    # Check if first cell has content and rest are empty or identical to first
                    first_cell = non_empty_cells[0]
                    rest_cells = non_empty_cells[1:]

                    # Section header pattern: "Gas Name" | "Gas Name" | "" | "" | "" (repeated or empty)
                    if first_cell and (all(not c for c in rest_cells) or all(c == first_cell for c in rest_cells)):
                        print(f"    🔧 Skipping section header: {first_cell[:50]}...")
                        continue

                data_lines.append(line)

            # Step 3: Split merged cells (detect multiple space-separated numeric values)
            for i, line in enumerate(data_lines):
                cells = [c.strip() for c in line.split('|')]

                for j, cell in enumerate(cells):
                    if not cell:
                        continue

                    # Check for merged numeric values (e.g., "2500 3000" or "0.0148 0.0127")
                    parts = cell.split()
                    if len(parts) == 2:
                        # Check if both parts look numeric
                        if self._is_numeric(parts[0]) and self._is_numeric(parts[1]):
                            print(f"    ⚠️  Merged cell at row {i}, col {j}: '{cell}' → using first value '{parts[0]}'")
                            # Conservative: take first value only
                            cells[j] = parts[0]

                # Reconstruct line
                data_lines[i] = '|' + '|'.join(cells) + '|'

            # Step 4: Parse with pandas
            cleaned_markdown = '\n'.join(data_lines)

            df = pd.read_csv(
                io.StringIO(cleaned_markdown),
                sep='|',
                skipinitialspace=True,
                skip_blank_lines=True,
                engine='python',
                on_bad_lines='warn'  # Warn instead of failing on bad lines
            )

            # Step 5: Clean up DataFrame
            # Remove first/last empty columns (from leading/trailing |)
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            df = df.dropna(axis=1, how='all')

            # Strip whitespace from all cells
            df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

            # Remove completely empty rows
            df = df.dropna(how='all')

            print(f"    ✅ Parsed table: {len(df)} rows × {len(df.columns)} columns")

            return df

        except Exception as e:
            print(f"    ⚠️  Markdown parsing failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _is_numeric(self, s: str) -> bool:
        """
        Check if string represents a numeric value.

        Args:
            s: String to check

        Returns:
            True if s can be parsed as a number
        """
        try:
            float(s)
            return True
        except (ValueError, TypeError):
            return False

    def _dataframe_to_structured(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Convert DataFrame to structured JSON format.

        Args:
            df: pandas DataFrame

        Returns:
            Dictionary with headers and rows
        """
        return {
            "headers": df.columns.tolist(),
            "rows": df.values.tolist()
        }

    def _save_csv(self, zone_id: str, df: pd.DataFrame, notes: str = "") -> Optional[Path]:
        """
        Save DataFrame as CSV file with optional notes section.

        Filters out "Notes:" marker rows from table data and appends
        actual note content as separate section below table.

        Args:
            zone_id: Zone identifier
            df: pandas DataFrame
            notes: Note text to append (optional)

        Returns:
            Path to CSV file, or None if save failed
        """
        try:
            # Filter out "Notes:" marker rows from DataFrame
            df_clean = df.copy()

            # Check first column for "Notes:" markers (case-insensitive)
            if len(df_clean.columns) > 0:
                first_col = df_clean.columns[0]
                # Remove rows where first column contains only "Notes:", "Note:", etc.
                note_markers = ['notes:', 'note:', 'notes', 'note']
                mask = df_clean[first_col].astype(str).str.lower().str.strip().isin(note_markers)
                df_clean = df_clean[~mask]

            # Save cleaned DataFrame
            csv_path = self.tables_dir / f"{zone_id}.csv"
            df_clean.to_csv(csv_path, index=False, encoding='utf-8')

            # Append notes if present
            if notes:
                with open(csv_path, 'a', encoding='utf-8') as f:
                    f.write('\n\nNOTES:\n')
                    f.write(notes + '\n')

            return csv_path
        except Exception as e:
            print(f"    ⚠️  CSV save failed: {e}")
            return None

    def _crop_table_image(self, zone: Zone) -> Optional[Path]:
        """
        Crop table image using bbox coordinates.

        Args:
            zone: Zone with bbox

        Returns:
            Path to cropped image, or None if crop failed
        """
        try:
            # Get page
            page_idx = zone.page - 1
            if page_idx >= len(self.doc):
                return None

            page = self.doc[page_idx]
            page_height = float(page.rect.height)

            # Convert bbox (Docling uses bottom-left origin)
            x0, y0, x1, y1 = zone.bbox
            y0_flip = page_height - y0
            y1_flip = page_height - y1
            y0_flip, y1_flip = min(y0_flip, y1_flip), max(y0_flip, y1_flip)

            # Create rect
            rect = fitz.Rect(x0, y0_flip, x1, y1_flip)

            # Render at 150 DPI
            mat = fitz.Matrix(150/72, 150/72)
            pix = page.get_pixmap(matrix=mat, clip=rect)

            # Save image
            img_path = self.tables_dir / f"{zone.zone_id}.png"
            pix.save(str(img_path))

            return img_path

        except Exception as e:
            print(f"    ⚠️  Image crop failed: {e}")
            return None

    def _extract_caption(self, zone: Zone) -> str:
        """
        Extract table caption from text above bbox.

        Searches for patterns like "Table X:" or "Table X."

        Args:
            zone: Zone with page and bbox

        Returns:
            Caption string, or empty if not found
        """
        try:
            # Get page
            page_idx = zone.page - 1
            if page_idx >= len(self.doc):
                return ""

            page = self.doc[page_idx]
            page_text = page.get_text()

            # Look for "Table X" patterns
            patterns = [
                r'(Table\s+\d+[a-z]?[\s\.:][^\n]+)',
                r'(TABLE\s+\d+[a-z]?[\s\.:][^\n]+)'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    # Return first match (tables are usually numbered sequentially)
                    caption = matches[0].strip()
                    # Clean up: remove extra whitespace
                    caption = re.sub(r'\s+', ' ', caption)
                    return caption

            return ""

        except Exception as e:
            print(f"    ⚠️  Caption extraction failed: {e}")
            return ""

    def _extract_notes(self, zone: Zone) -> str:
        """
        ENHANCED GENERIC: Extract notes/footnotes from inside table AND below table.

        Two-part note detection:
        1. INSIDE TABLE: Check markdown for "Notes:" rows and inline references
        2. BELOW TABLE: Search 50-250px below bbox for note patterns

        This handles both:
        - Tables with notes BELOW table bbox (e.g., Table 8a)
        - Tables with "Notes:" row INSIDE table data (e.g., Tables 7, 8b)

        Algorithm:
        ----------
        PART 1: Check markdown for inside-table notes
        PART 2: Check below table bbox for traditional notes
        PART 3: Combine results from both sources

        Args:
            zone: Zone with page, bbox, and metadata containing markdown

        Returns:
            Combined note text from both sources, or empty if no notes found
        """
        all_notes = []

        # PART 1: Extract notes from inside table markdown
        notes_from_table = self._extract_notes_from_table_data(zone)
        if notes_from_table:
            all_notes.append(notes_from_table)

        # PART 2: Extract notes from below table bbox
        notes_below_table = self._extract_notes_below_table(zone)
        if notes_below_table:
            all_notes.append(notes_below_table)

        # Combine both sources
        if all_notes:
            combined = " ".join(all_notes)
            # Clean up: normalize whitespace
            combined = re.sub(r'\s+', ' ', combined)
            return combined.strip()

        return ""

    def _extract_notes_from_table_data(self, zone: Zone) -> str:
        """
        PART 1: Extract notes from inside table markdown.

        Detects:
        - "Notes:" rows in table data
        - Inline references: "(see Note 1)", "(Note 2)", etc.
        - Note content that follows "Notes:" indicator

        Strategy:
        ---------
        1. Parse markdown to detect "Notes:" patterns
        2. Identify rows containing note references
        3. Search PDF text below table for actual note content
        4. Return combined note text

        Args:
            zone: Zone with metadata containing markdown

        Returns:
            Note text extracted from table data, or empty string
        """
        try:
            markdown = zone.metadata.get("markdown", "")
            if not markdown:
                return ""

            # Check if markdown contains "Notes:" or inline note references
            has_notes_marker = False
            inline_references = []

            # Pattern 1: "Notes:" row (case-insensitive)
            if re.search(r'\|\s*Notes?\s*[:.]?\s*\|', markdown, re.IGNORECASE):
                has_notes_marker = True

            # Pattern 2: Inline references like "(see Note 1)", "(Note 2)"
            inline_patterns = [
                r'\(see Note (\d+)\)',
                r'\(Note (\d+)\)',
                r'see Note (\d+)',
                r'Note (\d+)'
            ]
            for pattern in inline_patterns:
                matches = re.findall(pattern, markdown, re.IGNORECASE)
                inline_references.extend(matches)

            # If no note indicators found, return empty
            if not has_notes_marker and not inline_references:
                return ""

            # Found note indicators - search for actual note content
            # Note content is typically BELOW the table, even if "Notes:" is inside
            note_content = self._search_note_content_below_table(zone, inline_references)

            return note_content

        except Exception as e:
            print(f"    ⚠️  Inside-table note extraction failed: {e}")
            return ""

    def _search_note_content_below_table(self, zone: Zone, note_numbers: List[str]) -> str:
        """
        Search for actual note content below table bbox.

        When table contains "Notes:" row or inline references, the actual
        note text is often in the PDF below the table.

        Args:
            zone: Zone with page and bbox
            note_numbers: List of note numbers referenced (e.g., ["1", "2"])

        Returns:
            Note content text, or empty string
        """
        try:
            page_idx = zone.page - 1
            if page_idx >= len(self.doc):
                return ""

            page = self.doc[page_idx]
            page_height = float(page.rect.height)

            # Convert bbox
            x0, y0, x1, y1 = zone.bbox
            y0_flip = page_height - y0
            y1_flip = page_height - y1
            table_bottom = max(y0_flip, y1_flip)

            # Extended search zone for notes (can be further below for tables with note markers)
            note_zone_top = table_bottom
            note_zone_bottom = min(table_bottom + 400, page_height)  # Extended to 400px

            # Extract text blocks
            blocks = page.get_text("dict")["blocks"]

            note_lines = []
            found_note_start = False

            for block in blocks:
                if "lines" not in block:
                    continue

                block_y = block["bbox"][1]

                if note_zone_top <= block_y <= note_zone_bottom:
                    block_text = ""
                    for line in block["lines"]:
                        for span in line["spans"]:
                            block_text += span["text"]
                        block_text += " "

                    block_text = block_text.strip()

                    # Look for numbered notes matching references
                    if note_numbers:
                        # Pattern: "1." or "Note 1:" or "1)"
                        for num in note_numbers:
                            note_start_patterns = [
                                f'^{num}[\\.:)]\\s',
                                f'^Note\\s*{num}\\s*[\\.:)]',
                                f'^\\({num}\\)\\s'
                            ]
                            if any(re.match(pat, block_text, re.IGNORECASE) for pat in note_start_patterns):
                                found_note_start = True
                                break

                    # Also look for generic "Note:" patterns
                    if not found_note_start:
                        generic_patterns = [
                            r'^Note\s*\d*\s*[:.]',
                            r'^Notes?\s*[:.]',
                            r'^\d+\.\s'
                        ]
                        if any(re.match(pat, block_text, re.IGNORECASE) for pat in generic_patterns):
                            found_note_start = True

                    if found_note_start:
                        note_lines.append(block_text)

                        # Stop at next table/figure
                        if re.match(r'^(Table|Figure|Fig\.)\s+\d+', block_text, re.IGNORECASE):
                            note_lines.pop()
                            break

                elif block_y > note_zone_bottom:
                    break

            if note_lines:
                return " ".join(note_lines)

            return ""

        except Exception as e:
            print(f"    ⚠️  Note content search failed: {e}")
            return ""

    def _extract_notes_below_table(self, zone: Zone) -> str:
        """
        PART 2: Extract notes from below table bbox (original method).

        Searches the region below the table bbox for note patterns:
        - "Note:", "Note 1:", "Note 2:", etc.
        - Asterisk footnotes (*, **, etc.)
        - "Where:" definitions

        Algorithm:
        ----------
        1. Identify search zone (50-250px below table bbox)
        2. Extract text blocks in that zone
        3. Look for note patterns
        4. Collect note text until next table or end of zone
        5. Return concatenated note text

        Args:
            zone: Zone with page and bbox

        Returns:
            Note text string, or empty if no notes found
        """
        try:
            # Get page
            page_idx = zone.page - 1
            if page_idx >= len(self.doc):
                return ""

            page = self.doc[page_idx]
            page_height = float(page.rect.height)

            # Convert bbox (Docling uses bottom-left origin)
            x0, y0, x1, y1 = zone.bbox
            y0_flip = page_height - y0
            y1_flip = page_height - y1
            table_bottom = max(y0_flip, y1_flip)

            # Define note search zone: 50-250px below table
            note_zone_top = table_bottom
            note_zone_bottom = min(table_bottom + 250, page_height)

            # Extract text blocks with position info
            blocks = page.get_text("dict")["blocks"]

            note_lines = []
            in_note_region = False

            for block in blocks:
                # Skip non-text blocks
                if "lines" not in block:
                    continue

                block_y = block["bbox"][1]  # Top of block

                # Check if block is in note zone
                if note_zone_top <= block_y <= note_zone_bottom:
                    # Extract text from block
                    block_text = ""
                    for line in block["lines"]:
                        for span in line["spans"]:
                            block_text += span["text"]
                        block_text += " "

                    block_text = block_text.strip()

                    # Check for note patterns
                    note_patterns = [
                        r'^Note\s*\d*\s*[:.]',  # Note: or Note 1: or Note 2:
                        r'^\*+\s',  # Asterisk footnotes (*, **, ***)
                        r'^Where\s*:',  # Variable definitions
                        r'^\(?\d+\)\s*Note',  # (1) Note or 1) Note
                    ]

                    is_note_start = any(re.match(pat, block_text, re.IGNORECASE) for pat in note_patterns)

                    if is_note_start:
                        in_note_region = True

                    # If we're in a note region, collect text
                    if in_note_region:
                        note_lines.append(block_text)

                        # Stop if we hit another table or figure
                        if re.match(r'^(Table|Figure|Fig\.)\s+\d+', block_text, re.IGNORECASE):
                            # This is the start of next object, don't include it
                            note_lines.pop()
                            break

                # If we've passed the note zone, stop
                elif block_y > note_zone_bottom:
                    break

            # Combine note lines
            if note_lines:
                note_text = " ".join(note_lines)
                # Clean up: normalize whitespace
                note_text = re.sub(r'\s+', ' ', note_text)
                return note_text.strip()

            return ""

        except Exception as e:
            print(f"    ⚠️  Below-table note extraction failed: {e}")
            return ""

    def __del__(self):
        """Clean up PDF document on deletion."""
        if hasattr(self, 'doc'):
            self.doc.close()
