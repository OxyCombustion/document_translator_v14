# -*- coding: utf-8 -*-
"""
Docling Table Detector - Parallel Table Detection Using Proven Docling

This module wraps the existing working Docling table extraction to provide
table zones for the unified pipeline.

Design Rationale:
-----------------
- **Proven Technology**: Docling table extraction is 100% validated
- **Parallel Execution**: Runs in parallel with DocLayout-YOLO
- **Wrapper Pattern**: Thin wrapper around existing working code
- **Zone Output**: Converts Docling results to Zone objects

Author: Claude Code
Date: 2025-01-16
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

from docling.document_converter import DocumentConverter
from pathlib import Path
from typing import List
from datetime import datetime

# Import Zone from base agent (proper relative import)
from pipelines.shared.packages.common.src.base.base_extraction_agent import Zone


class DoclingTableDetector:
    """
    Table detection using proven Docling technology.

    This is a thin wrapper that runs Docling and converts results to zones.
    """

    def __init__(self):
        """Initialize Docling converter."""
        print(f"🔧 Loading Docling converter...")
        self.converter = DocumentConverter()
        print(f"✅ Docling ready")

    def detect_tables(self, pdf_path: Path, docling_result=None) -> List[Zone]:
        """
        Detect table regions using Docling.

        Args:
            pdf_path: Path to PDF file
            docling_result: Optional pre-computed Docling result (for efficiency)

        Returns:
            List[Zone] with table regions
        """
        print(f"\n{'='*80}")
        print(f"DOCLING TABLE DETECTION")
        print(f"{'='*80}")
        print(f"PDF: {pdf_path}")
        print()

        start_time = datetime.now()

        # Use provided result or run conversion
        if docling_result:
            print("Using existing Docling result (shared with figures)...")
            result = docling_result
        else:
            print("Running Docling conversion...")
            result = self.converter.convert(pdf_path)

        # Extract table zones
        zones = []

        # Use result.document (v13 API) or result.output (newer API) - both have .tables
        tables_source = None
        if hasattr(result, 'document') and hasattr(result.document, 'tables'):
            tables_source = result.document.tables
        elif hasattr(result, 'output') and hasattr(result.output, 'tables'):
            tables_source = result.output.tables

        if tables_source:
            for i, table in enumerate(tables_source):
                # Get table location
                page_num = 1  # Default
                bbox = [0, 0, 100, 100]  # Default

                # Try to extract page and bbox from table metadata
                if hasattr(table, 'prov') and table.prov:
                    for prov in table.prov:
                        if hasattr(prov, 'page_no'):
                            page_num = prov.page_no
                        if hasattr(prov, 'bbox'):
                            bbox_data = prov.bbox
                            # New Docling API: bbox is a list [l, t, r, b]
                            if isinstance(bbox_data, list) and len(bbox_data) == 4:
                                bbox = bbox_data
                            # Old API fallback: bbox is an object with .l, .t, .r, .b
                            elif hasattr(bbox_data, 'l'):
                                bbox = [bbox_data.l, bbox_data.t, bbox_data.r, bbox_data.b]

                # Create zone
                zone_id = f"table_{i+1}"
                zone = Zone(
                    zone_id=zone_id,
                    type="table",
                    page=page_num,
                    bbox=bbox,
                    metadata={
                        'docling_table_index': i,
                        'detection_method': 'docling',
                        'html': table.export_to_html()  # Add HTML for extraction (new Docling API)
                    }
                )
                zones.append(zone)

                print(f"  Table {i+1}: page {page_num}, bbox {bbox}")

        duration = (datetime.now() - start_time).total_seconds()

        print()
        print(f"Detection complete in {duration:.1f}s")
        print(f"Tables detected: {len(zones)}")
        print()

        return zones
