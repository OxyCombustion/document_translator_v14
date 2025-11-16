#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Table Diagram Extractor - Extract Embedded Diagrams from Tables

This helper class extracts diagrams, circuit drawings, and other visual
content that may be embedded within table cells. It's used by TableExtractionAgent
to preserve visual content that would otherwise be lost.

Design Rationale:
-----------------
- **Visual Content Preservation**: Tables often contain:
  - Circuit diagrams (Table 5 - Network Equivalents)
  - Thermal resistance diagrams (Table 4)
  - Schematic drawings embedded in cells

- **Separate Extraction**: Diagrams are extracted as separate images
  - Stored alongside table data
  - Linked back to specific table rows/cells
  - Can be re-embedded in Excel during export

- **Generic Detection**: Uses image detection within table bbox
  - Finds all images in table region
  - Extracts and saves each image
  - Returns metadata for linking

Alternatives Considered:
------------------------
1. Ignore diagrams: Loses critical information
2. OCR diagrams as text: Destroys visual structure
3. Always extract full table as image: Loses structured data

Usage:
------
>>> from table_diagram_extractor import TableDiagramExtractor
>>> extractor = TableDiagramExtractor(pdf_path, pdf_doc, output_dir)
>>> diagrams = extractor.extract_diagrams(table_zone)
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any
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


class TableDiagramExtractor:
    """
    Extract diagrams embedded within tables.

    This is NOT an agent - it's a helper class used by TableExtractionAgent.
    """

    def __init__(self, pdf_path: Path, pdf_doc: fitz.Document, output_dir: Path):
        """
        Initialize diagram extractor.

        Args:
            pdf_path: Path to PDF
            pdf_doc: Open PyMuPDF document object
            output_dir: Directory to save extracted diagram images
        """
        self.pdf_path = pdf_path
        self.pdf_doc = pdf_doc
        self.output_dir = output_dir / "diagrams"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_diagrams(self, zone: Zone) -> List[Dict[str, Any]]:
        """
        Extract all diagrams/images from table zone.

        Args:
            zone: Table zone to extract diagrams from

        Returns:
            List of diagram metadata dictionaries:
            [{
                "diagram_id": "table_5_diagram_0",
                "image_path": "diagrams/table_5_diagram_0.png",
                "bbox": [x0, y0, x1, y1],
                "width": 120,
                "height": 80
            }, ...]
        """
        try:
            page = self.pdf_doc[zone.page - 1]  # 0-indexed
            x0, y0, x1, y1 = zone.bbox

            # Get all images in table region
            images = page.get_images(full=True)

            if not images:
                return []

            diagrams = []

            for img_index, img_info in enumerate(images):
                xref = img_info[0]  # Image xref number

                # Get image bbox
                img_rects = page.get_image_rects(xref)

                # Check if image is within table bbox
                for rect in img_rects:
                    img_x0, img_y0, img_x1, img_y1 = rect

                    # Check overlap with table
                    if self._bbox_intersects(
                        (x0, y0, x1, y1),
                        (img_x0, img_y0, img_x1, img_y1)
                    ):
                        # Extract and save image
                        diagram_id = f"{zone.zone_id}_diagram_{img_index}"
                        image_path = self._extract_image(page, xref, diagram_id)

                        if image_path:
                            diagrams.append({
                                "diagram_id": diagram_id,
                                "image_path": str(image_path.relative_to(self.output_dir.parent)),
                                "bbox": [img_x0, img_y0, img_x1, img_y1],
                                "width": img_x1 - img_x0,
                                "height": img_y1 - img_y0
                            })

            return diagrams

        except Exception as e:
            print(f"      Diagram extraction failed: {e}")
            return []

    def _bbox_intersects(self, bbox1, bbox2) -> bool:
        """
        Check if two bounding boxes intersect.

        Args:
            bbox1: First bbox [x0, y0, x1, y1]
            bbox2: Second bbox [x0, y0, x1, y1]

        Returns:
            True if boxes intersect
        """
        x0_1, y0_1, x1_1, y1_1 = bbox1
        x0_2, y0_2, x1_2, y1_2 = bbox2

        # Check if boxes don't intersect
        if x1_1 <= x0_2 or x1_2 <= x0_1:
            return False
        if y1_1 <= y0_2 or y1_2 <= y0_1:
            return False

        return True

    def _extract_image(self, page: fitz.Page, xref: int, diagram_id: str) -> Path:
        """
        Extract image from PDF and save to file.

        Args:
            page: PDF page
            xref: Image xref number
            diagram_id: Unique identifier for diagram

        Returns:
            Path to saved image file
        """
        try:
            # Extract image bytes
            base_image = self.pdf_doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]  # png, jpg, etc.

            # Save to file
            image_path = self.output_dir / f"{diagram_id}.{image_ext}"

            with open(image_path, "wb") as f:
                f.write(image_bytes)

            return image_path

        except Exception as e:
            print(f"      Image extraction failed for {diagram_id}: {e}")
            return None

    def has_diagrams(self, zone: Zone) -> bool:
        """
        Quick check if table contains any diagrams.

        Args:
            zone: Table zone

        Returns:
            True if diagrams detected
        """
        try:
            page = self.pdf_doc[zone.page - 1]
            x0, y0, x1, y1 = zone.bbox

            images = page.get_images(full=True)

            for img_info in images:
                xref = img_info[0]
                img_rects = page.get_image_rects(xref)

                for rect in img_rects:
                    if self._bbox_intersects((x0, y0, x1, y1), rect):
                        return True

            return False

        except:
            return False


if __name__ == "__main__":
    # Simple test
    pdf_path = Path("tests/test_data/Ch-04_Heat_Transfer.pdf")

    if not pdf_path.exists():
        print(f"ERROR: Test PDF not found: {pdf_path}")
        sys.exit(1)

    doc = fitz.open(str(pdf_path))
    output_dir = Path("test_diagram_extraction")
    extractor = TableDiagramExtractor(pdf_path, doc, output_dir)

    # Test on Table 5 (page 9) - known to have circuit diagrams
    test_zone = Zone(
        zone_id="table_9_test",
        type="table",
        page=9,
        bbox=[34.74, 510.93, 287.68, 747.10],  # Approximate Table 5 bbox
        metadata={}
    )

    print("Testing Table 5 (page 9) diagram extraction...")

    has_diagrams = extractor.has_diagrams(test_zone)
    print(f"Has diagrams: {has_diagrams}")

    if has_diagrams:
        diagrams = extractor.extract_diagrams(test_zone)
        print(f"✓ Extracted {len(diagrams)} diagram(s):")
        for diag in diagrams:
            print(f"  - {diag['diagram_id']}: {diag['width']:.0f}x{diag['height']:.0f}px")
            print(f"    Saved to: {diag['image_path']}")
    else:
        print("✗ No diagrams found")

    doc.close()
