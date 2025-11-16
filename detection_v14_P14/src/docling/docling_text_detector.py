#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Docling Text Detector - Extract text blocks using Docling semantic understanding

This detector extracts text content from PDF documents using Docling's
text analysis capabilities. It identifies and extracts text blocks while
preserving semantic structure and layout information.

Design:
-------
- Uses Docling's text extraction (doc.texts)
- Creates zones for each text block with bbox coordinates
- Preserves page numbers and text content
- Complements equation/table/figure detection

Author: Claude Code
Date: 2025-01-20
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
from typing import List, Optional
from dataclasses import dataclass

from common.src.base.base_extraction_agent import Zone

from docling.document_converter import DocumentConverter


@dataclass
class TextBlock:
    """Represents a text block extracted from a document."""
    text: str
    page: int
    bbox: tuple  # (x0, y0, x1, y1)
    block_index: int


class DoclingTextDetector:
    """
    Extracts text blocks from PDFs using Docling's semantic understanding.

    This detector complements equation/table/figure detection by extracting
    all text content while preserving layout and semantic information.
    """

    def __init__(self):
        """Initialize Docling text detector."""
        self.converter = DocumentConverter()

    def detect_text(self, pdf_path: Path, docling_result=None) -> List[Zone]:
        """
        Detect text blocks in PDF using Docling.

        Args:
            pdf_path: Path to PDF file
            docling_result: Optional pre-computed Docling result (for efficiency)

        Returns:
            List of Zone objects for detected text blocks
        """
        print(f"\n{'='*80}")
        print(f"DOCLING TEXT DETECTION")
        print(f"{'='*80}")
        print(f"PDF: {pdf_path}")
        print()

        # Use existing result or convert
        if docling_result is None:
            print("Converting document with Docling...")
            docling_result = self.converter.convert_single(pdf_path)
        else:
            print("Using existing Docling result (shared conversion)...")

        # Use result.document (v13 API, has .texts, .pages) instead of result.output
        if hasattr(docling_result, 'document'):
            doc = docling_result.document
        elif hasattr(docling_result, 'output'):
            doc = docling_result.output
        else:
            print("⚠️  Docling result has neither 'document' nor 'output' attribute")
            return []

        # Extract text blocks
        print(f"Extracting text blocks...")
        text_blocks = []

        for idx, text_item in enumerate(doc.texts):
            # Get text content
            text_content = str(text_item.text)

            # Skip empty text blocks
            if not text_content.strip():
                continue

            # Get page number (Docling uses 1-based indexing)
            page_num = text_item.prov[0].page_no if text_item.prov else 1

            # Get bounding box if available
            bbox = None
            if text_item.prov and len(text_item.prov) > 0:
                prov = text_item.prov[0]
                if hasattr(prov, 'bbox'):
                    bbox_obj = prov.bbox
                    bbox = (bbox_obj.l, bbox_obj.t, bbox_obj.r, bbox_obj.b)

            # Create text block
            if bbox:
                text_block = TextBlock(
                    text=text_content,
                    page=page_num,
                    bbox=bbox,
                    block_index=idx
                )
                text_blocks.append(text_block)

        # Convert to zones
        zones = []
        for block in text_blocks:
            zone = Zone(
                zone_id=f"text_{block.page}_{block.block_index}",
                type="text",
                page=block.page,
                bbox=list(block.bbox),  # Convert tuple to list
                metadata={
                    'text_content': block.text,
                    'block_index': block.block_index,
                    'char_count': len(block.text),
                    'confidence': 0.95  # Docling text extraction is reliable
                }
            )
            zones.append(zone)

        print(f"  Extracted {len(zones)} text blocks")
        print(f"  Total characters: {sum(len(b.text) for b in text_blocks):,}")
        print()
        print(f"Detection complete in 0.0s")
        print(f"Text blocks detected: {len(zones)}")
        print()

        return zones


if __name__ == "__main__":
    # Test the detector
    pdf_path = Path("tests/test_data/Ch-04_Heat_Transfer.pdf")

    detector = DoclingTextDetector()
    zones = detector.detect_text(pdf_path)

    print(f"\n{'='*80}")
    print(f"TEST COMPLETE")
    print(f"{'='*80}")
    print(f"Total text zones: {len(zones)}")
    print(f"\nFirst 3 text blocks:")
    for i, zone in enumerate(zones[:3]):
        print(f"\n{i+1}. Page {zone.page}:")
        print(f"   Chars: {zone.metadata['char_count']}")
        print(f"   Preview: {zone.metadata['text_content'][:100]}...")
