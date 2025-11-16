# -*- coding: utf-8 -*-
"""
Docling Figure Detector - Figure Detection Using Docling's Document Understanding

This module uses Docling's semantic document model to detect actual figures,
avoiding false positives from text blocks that YOLO incorrectly classifies.

Design Rationale:
-----------------
- **Semantic Understanding**: Docling knows the difference between text and figures
- **No False Positives**: Won't detect text blocks as figures
- **Parallel Execution**: Runs alongside table detection (same Docling pass)
- **Proven Technology**: Uses same Docling converter as working table detection

Author: Claude Code
Date: 2025-10-17
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
from common.src.base.base_extraction_agent import Zone


class DoclingFigureDetector:
    """
    Figure detection using Docling's semantic document understanding.

    Advantages over YOLO:
    --------------------
    - Understands document structure (text vs figures)
    - No false positives from text blocks
    - Detects actual figure elements from PDF
    - Works with same Docling pass as tables (efficient)
    """

    def __init__(self, docling_result=None):
        """
        Initialize Docling converter or reuse existing result.

        Args:
            docling_result: Optional pre-existing Docling conversion result
                           (to avoid re-running Docling if already done for tables)
        """
        self.docling_result = docling_result
        self.converter = None if docling_result else DocumentConverter()

    def detect_figures(self, pdf_path: Path, docling_result=None) -> List[Zone]:
        """
        Detect figure regions using Docling's document model.

        Args:
            pdf_path: Path to PDF file
            docling_result: Optional pre-computed Docling result (from table detection)

        Returns:
            List[Zone] with figure regions
        """
        print(f"\n{'='*80}")
        print(f"DOCLING FIGURE DETECTION")
        print(f"{'='*80}")
        print(f"PDF: {pdf_path}")
        print()

        start_time = datetime.now()

        # Use provided result or run conversion
        if docling_result:
            print("Using existing Docling result (from table detection)...")
            result = docling_result
        else:
            print("Running Docling conversion...")
            result = self.converter.convert_single(pdf_path)

        # Extract figure zones from Docling's document model
        zones = []

        # Use result.document (v13 API, has .pages) instead of result.output
        if hasattr(result, 'document'):
            doc = result.document
        elif hasattr(result, 'output'):
            doc = result.output

        # Method 1: Check for pictures collection
        if hasattr(doc, 'pictures') and doc.pictures:
            print(f"Found {len(doc.pictures)} pictures in document.pictures")
            for i, picture in enumerate(doc.pictures):
                zone = self._picture_to_zone(picture, i)
                if zone:
                    zones.append(zone)
                    print(f"  Picture {i+1}: page {zone.page}, bbox {zone.bbox}")

        # Method 2: Scan page elements for picture items
        elif hasattr(doc, 'pages'):
            print("Scanning page elements for pictures...")
            picture_count = 0
            for page_num, page in enumerate(doc.pages, 1):
                if hasattr(page, 'children'):
                    for item in page.children:
                        # Check if this is a picture element
                        item_type = type(item).__name__
                        if 'Picture' in item_type or 'Figure' in item_type or 'Image' in item_type:
                            zone = self._element_to_zone(item, page_num, picture_count)
                            if zone:
                                zones.append(zone)
                                print(f"  Picture {picture_count+1}: page {page_num}, bbox {zone.bbox}")
                                picture_count += 1
        else:
            print("⚠️  No .pictures or .pages found on document object")

        duration = (datetime.now() - start_time).total_seconds()

        print()
        print(f"Detection complete in {duration:.1f}s")
        print(f"Figures detected: {len(zones)}")
        print()

        return zones

    def _picture_to_zone(self, picture, index: int) -> Zone:
        """Convert Docling picture object to Zone."""
        try:
            # Get picture location
            page_num = 1  # Default
            bbox = [0, 0, 100, 100]  # Default

            # Try to extract page and bbox from picture metadata
            if hasattr(picture, 'prov') and picture.prov:
                for prov in picture.prov:
                    if hasattr(prov, 'page_no'):
                        page_num = prov.page_no
                    if hasattr(prov, 'bbox'):
                        bbox_obj = prov.bbox
                        bbox = [
                            bbox_obj.l,
                            bbox_obj.t,
                            bbox_obj.r,
                            bbox_obj.b
                        ]

            # Create zone
            zone_id = f"fig_docling_{page_num}_{index}"
            zone = Zone(
                zone_id=zone_id,
                type="figure",
                page=page_num,
                bbox=bbox,
                metadata={
                    'docling_picture_index': index,
                    'detection_method': 'docling',
                    'caption': getattr(picture, 'caption', '') if hasattr(picture, 'caption') else ''
                }
            )
            return zone

        except Exception as e:
            print(f"    ⚠️  Failed to convert picture {index}: {e}")
            return None

    def _element_to_zone(self, element, page_num: int, index: int) -> Zone:
        """Convert page element to Zone."""
        try:
            # Extract bbox if available
            bbox = [0, 0, 100, 100]  # Default

            if hasattr(element, 'prov') and element.prov:
                for prov in element.prov:
                    if hasattr(prov, 'bbox'):
                        bbox_obj = prov.bbox
                        bbox = [
                            bbox_obj.l,
                            bbox_obj.t,
                            bbox_obj.r,
                            bbox_obj.b
                        ]
                        break

            # Create zone
            zone_id = f"fig_docling_{page_num}_{index}"
            zone = Zone(
                zone_id=zone_id,
                type="figure",
                page=page_num,
                bbox=bbox,
                metadata={
                    'docling_element_type': type(element).__name__,
                    'detection_method': 'docling',
                    'caption': getattr(element, 'caption', '') if hasattr(element, 'caption') else ''
                }
            )
            return zone

        except Exception as e:
            print(f"    ⚠️  Failed to convert element on page {page_num}: {e}")
            return None
