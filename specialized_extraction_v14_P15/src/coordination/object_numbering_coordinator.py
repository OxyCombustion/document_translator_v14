#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Object Numbering Coordinator Agent

Coordinates extraction of ACTUAL object numbers from captions using existing agents.
Returns objects with TRUE numbers (not sequential detection order).

Purpose:
    - Extract actual table numbers: "Table 4" → object_number="4"
    - Extract actual figure numbers: "Figure 11" → object_number="11"
    - Extract actual equation numbers: "(23)" → object_number="23"
    - Handle unnumbered objects: "Unnumbered table from Chapter 4 Page 15"
    - Handle letter suffixes: "79a", "79b", "8a", "8b"

Architecture:
    - Wraps existing caption extraction agents
    - Does NOT re-implement caption extraction
    - Coordinates between multiple existing agents
    - Returns standardized numbering metadata

Existing Agents Used:
    - TableCaptionExtractor (src/agents/caption_extraction/table_caption_extractor.py)
    - FigureDetectionAgent (src/agents/figure_extraction/figure_detection_agent.py)
    - Equation zones already have equation_number from YOLO pairing

Author: V12 Development Team
Created: 2025-10-20
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import re

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

# Import existing caption extractors (v14 package imports)
from specialized_extraction_v14_P15.src.captions.table_caption_extractor import TableCaptionExtractor
from common.src.base.base_extraction_agent import Zone


class ObjectNumberingCoordinator:
    """
    Coordinates extraction of actual object numbers from captions.

    This agent does NOT extract captions - it uses existing agents.
    It coordinates numbering across all object types for consistency.

    Example:
        >>> coordinator = ObjectNumberingCoordinator(pdf_path)
        >>> # For tables
        >>> table_zones = [...] # from detection
        >>> numbered_zones = coordinator.assign_table_numbers(table_zones)
        >>> print(numbered_zones[0].metadata['object_number'])  # "1" not "0"
    """

    def __init__(self, pdf_path: Path, document_title: str = "Chapter 4"):
        """
        Initialize numbering coordinator.

        Args:
            pdf_path: Path to PDF document
            document_title: Document title for unnumbered object labeling
        """
        self.pdf_path = Path(pdf_path)
        self.document_title = document_title

        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Initialize caption extractor
        self.table_caption_extractor = TableCaptionExtractor(pdf_path)

        print("================================================================================")
        print("OBJECT NUMBERING COORDINATOR")
        print("================================================================================")
        print(f"PDF: {self.pdf_path.name}")
        print()

    def assign_table_numbers(self, table_zones: List[Zone]) -> List[Zone]:
        """
        Assign actual table numbers from captions.

        Args:
            table_zones: List of detected table zones

        Returns:
            Table zones with metadata['object_number'] populated with actual numbers
        """
        print(f"Assigning table numbers to {len(table_zones)} zones...")

        # Build metadata list for TableCaptionExtractor
        table_metadata = []
        for i, zone in enumerate(table_zones):
            table_metadata.append({
                "table_number": str(i + 1),  # Temporary sequential number for extractor
                "page": zone.page,
                "bbox": zone.bbox
            })

        # Extract captions using existing agent
        captions = self.table_caption_extractor.extract_all_captions(table_metadata)

        # Assign actual numbers from captions
        for i, zone in enumerate(table_zones):
            temp_number = str(i + 1)

            # Check if we found a caption
            if temp_number in captions:
                caption_data = captions[temp_number]
                actual_number = self._parse_table_number_from_caption(caption_data['caption'])

                if actual_number:
                    zone.metadata['object_number'] = actual_number
                    zone.metadata['caption'] = caption_data['caption']
                    zone.metadata['caption_confidence'] = caption_data['confidence']
                    print(f"  ✅ Table zone {i+1} → Table {actual_number}")
                else:
                    # Caption found but couldn't parse number
                    zone.metadata['object_number'] = self._generate_unnumbered_label('table', zone.page)
                    zone.metadata['caption'] = caption_data['caption']
                    zone.metadata['caption_confidence'] = caption_data['confidence']
                    print(f"  ⚠️  Table zone {i+1} → {zone.metadata['object_number']} (caption: {caption_data['caption'][:50]}...)")
            else:
                # No caption found
                zone.metadata['object_number'] = self._generate_unnumbered_label('table', zone.page)
                print(f"  ⚠️  Table zone {i+1} → {zone.metadata['object_number']} (no caption)")

        print()
        return table_zones

    def assign_figure_numbers(self, figure_zones: List[Zone]) -> List[Zone]:
        """
        Assign actual figure numbers from captions.

        Args:
            figure_zones: List of detected figure zones

        Returns:
            Figure zones with metadata['object_number'] populated
        """
        print(f"Assigning figure numbers to {len(figure_zones)} zones...")

        for i, zone in enumerate(figure_zones):
            # Check if Docling already extracted figure number in metadata
            if 'figure_number' in zone.metadata and zone.metadata['figure_number']:
                actual_number = zone.metadata['figure_number']
                zone.metadata['object_number'] = actual_number
                print(f"  ✅ Figure zone {i+1} → Figure {actual_number}")
            else:
                # Try to extract from caption if present
                if 'caption' in zone.metadata and zone.metadata['caption']:
                    actual_number = self._parse_figure_number_from_caption(zone.metadata['caption'])
                    if actual_number:
                        zone.metadata['object_number'] = actual_number
                        print(f"  ✅ Figure zone {i+1} → Figure {actual_number} (from caption)")
                    else:
                        zone.metadata['object_number'] = self._generate_unnumbered_label('figure', zone.page)
                        print(f"  ⚠️  Figure zone {i+1} → {zone.metadata['object_number']}")
                else:
                    zone.metadata['object_number'] = self._generate_unnumbered_label('figure', zone.page)
                    print(f"  ⚠️  Figure zone {i+1} → {zone.metadata['object_number']} (no caption)")

        print()
        return figure_zones

    def assign_equation_numbers(self, equation_zones: List[Zone]) -> List[Zone]:
        """
        Assign actual equation numbers.

        Equations already have 'equation_number' from YOLO pairing.
        This method just standardizes the metadata key to 'object_number'.

        Args:
            equation_zones: List of detected equation zones

        Returns:
            Equation zones with metadata['object_number'] populated
        """
        print(f"Assigning equation numbers to {len(equation_zones)} zones...")

        for i, zone in enumerate(equation_zones):
            # Equations already have equation_number from YOLO pairing
            if 'equation_number' in zone.metadata and zone.metadata['equation_number']:
                actual_number = zone.metadata['equation_number']
                zone.metadata['object_number'] = actual_number
                print(f"  ✅ Equation zone {i+1} → Equation {actual_number}")
            else:
                # Rare case: equation without number
                zone.metadata['object_number'] = self._generate_unnumbered_label('equation', zone.page)
                print(f"  ⚠️  Equation zone {i+1} → {zone.metadata['object_number']}")

        print()
        return equation_zones

    def _parse_table_number_from_caption(self, caption: str) -> Optional[str]:
        """
        Parse actual table number from caption text.

        Args:
            caption: Caption text (e.g., "Table 4. Thermal Resistances")

        Returns:
            Table number as string (e.g., "4", "8a") or None
        """
        # Try multiple patterns
        patterns = [
            r'Table\s+(\d+[a-z]?)',
            r'TABLE\s+(\d+[a-z]?)',
            r'Tab\.\s+(\d+[a-z]?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, caption, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _parse_figure_number_from_caption(self, caption: str) -> Optional[str]:
        """
        Parse actual figure number from caption text.

        Args:
            caption: Caption text (e.g., "Figure 11. Temperature Distribution")

        Returns:
            Figure number as string (e.g., "11", "8a") or None
        """
        # Try multiple patterns
        patterns = [
            r'Figure\s+(\d+[a-z]?)',
            r'FIGURE\s+(\d+[a-z]?)',
            r'Fig\.\s+(\d+[a-z]?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, caption, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _generate_unnumbered_label(self, obj_type: str, page: int) -> str:
        """
        Generate label for unnumbered objects.

        Args:
            obj_type: 'table', 'figure', or 'equation'
            page: Page number where object appears

        Returns:
            Descriptive label: "unnumbered_table_ch4_page15"
        """
        # Sanitize document title for filename safety
        doc_safe = self.document_title.lower().replace(' ', '_')
        return f"unnumbered_{obj_type}_{doc_safe}_page{page}"


if __name__ == "__main__":
    # Test on Chapter 4
    pdf_path = Path("tests/test_data/Ch-04_Heat_Transfer.pdf")

    if not pdf_path.exists():
        print(f"ERROR: Test PDF not found: {pdf_path}")
        sys.exit(1)

    coordinator = ObjectNumberingCoordinator(pdf_path)

    # Create test zones
    test_zones = [
        Zone(zone_id="table_1", type="table", page=2, bbox=[323.0, 53.7, 576.8, 219.0], metadata={}),
        Zone(zone_id="table_2", type="table", page=4, bbox=[323.3, 53.9, 576.2, 168.1], metadata={}),
        Zone(zone_id="table_3", type="table", page=15, bbox=[310.2, 92.9, 554.4, 170.6], metadata={}),  # Unnumbered
    ]

    # Test table numbering
    numbered_zones = coordinator.assign_table_numbers(test_zones)

    print("\n=== RESULTS ===")
    for zone in numbered_zones:
        print(f"Zone {zone.zone_id}: object_number = {zone.metadata.get('object_number')}")
        if 'caption' in zone.metadata:
            print(f"  Caption: {zone.metadata['caption'][:60]}...")
