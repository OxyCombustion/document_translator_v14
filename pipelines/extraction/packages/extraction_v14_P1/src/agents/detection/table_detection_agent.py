#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Table Detection Agent - Hybrid Docling + YOLO Detection

This agent combines two complementary table detection strategies:
1. Docling: Accurate text-based table detection (works for text-only tables)
2. DocLayout-YOLO: Vision-based detection (catches image-embedded tables)

Design Rationale:
-----------------
- **Hybrid Strategy**: Neither Docling nor YOLO alone catches all tables
  - Docling misses tables with embedded diagrams (Tables 4, 6, 9)
  - YOLO may have false positives on equation arrays
  - Combining both with IoU-based deduplication gives best coverage

- **Generic & Reusable**: Works on ANY PDF with tables, not just Chapter 4
- **Single Responsibility**: Only detects tables, doesn't extract content
- **Composable**: Produces standard Zone objects for extraction pipeline

Alternatives Considered:
------------------------
1. Docling only: Fast but misses 25% of tables (image-embedded)
2. YOLO only: Catches all but has false positives requiring filtering
3. Manual detection: Not scalable, defeats automation purpose

Usage:
------
>>> detector = TableDetectionAgent(pdf_path="document.pdf")
>>> zones = detector.detect_tables()
>>> # zones is List[Zone] ready for TableExtractionAgent
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
import time

# MANDATORY UTF-8 SETUP
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')

# Import detection libraries
from docling.document_converter import DocumentConverter

try:
    from doclayout_yolo import YOLOv10
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

# Import Zone data structure
# Import using proper v14 package structure (no sys.path manipulation)
from pipelines.shared.packages.common.src.base.base_extraction_agent import Zone


class TableDetectionAgent:
    """
    Hybrid table detection using Docling + YOLO with intelligent merging.

    This agent is NOT a BaseExtractionAgent because it produces Zones
    (detection results) rather than ExtractedObjects (extracted content).

    Architecture:
    ------------
    Detection Layer (this agent):
        PDF → TableDetectionAgent → List[Zone]

    Extraction Layer (separate agents):
        List[Zone] → TableExtractionAgent → List[ExtractedObject]

    This separation ensures:
    - Detection logic can be swapped without changing extraction
    - Detection can be cached/reused across multiple extraction runs
    - Clear separation of concerns (detect vs extract)
    """

    def __init__(
        self,
        pdf_path: Path,
        yolo_model_path: Optional[Path] = None,
        docling_enabled: bool = True,
        yolo_enabled: bool = True,
        iou_threshold: float = 0.5,
        yolo_conf_threshold: float = 0.3
    ):
        """
        Initialize hybrid table detection agent.

        Args:
            pdf_path: Path to PDF document
            yolo_model_path: Path to YOLO model file (auto-detected if None)
            docling_enabled: Enable Docling detection
            yolo_enabled: Enable YOLO detection
            iou_threshold: IoU threshold for duplicate removal (0.0-1.0)
            yolo_conf_threshold: YOLO confidence threshold (0.0-1.0)
        """
        self.pdf_path = Path(pdf_path)
        self.docling_enabled = docling_enabled
        self.yolo_enabled = yolo_enabled
        self.iou_threshold = iou_threshold
        self.yolo_conf_threshold = yolo_conf_threshold

        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

        # Auto-detect YOLO model if not specified
        if yolo_model_path is None:
            yolo_model_path = Path("models/models/Layout/YOLO/doclayout_yolo_docstructbench_imgsz1280_2501.pt")

        self.yolo_model_path = yolo_model_path

        # Validate YOLO availability
        if self.yolo_enabled and not YOLO_AVAILABLE:
            print("⚠️  WARNING: YOLO requested but doclayout_yolo not installed")
            print("           Falling back to Docling-only detection")
            self.yolo_enabled = False

        if self.yolo_enabled and not self.yolo_model_path.exists():
            print(f"⚠️  WARNING: YOLO model not found: {self.yolo_model_path}")
            print("           Falling back to Docling-only detection")
            self.yolo_enabled = False

        # Statistics
        self.stats = {
            "docling_tables": 0,
            "yolo_tables": 0,
            "duplicates_removed": 0,
            "total_unique": 0,
            "docling_time": 0.0,
            "yolo_time": 0.0,
            "merge_time": 0.0
        }

    def detect_tables(self, pages_to_scan: Optional[List[int]] = None) -> List[Zone]:
        """
        Detect all tables in document using hybrid strategy.

        Args:
            pages_to_scan: List of page numbers (1-indexed), or None for all pages

        Returns:
            List of Zones representing detected tables
        """
        print("\n" + "="*80)
        print("TABLE DETECTION (HYBRID STRATEGY)")
        print("="*80)
        print(f"PDF: {self.pdf_path.name}")
        print(f"Strategy: ", end="")
        strategies = []
        if self.docling_enabled:
            strategies.append("Docling")
        if self.yolo_enabled:
            strategies.append("YOLO")
        print(" + ".join(strategies))
        print()

        # Run detection strategies
        docling_detections = []
        yolo_detections = []

        if self.docling_enabled:
            docling_detections = self._detect_with_docling()

        if self.yolo_enabled:
            yolo_detections = self._detect_with_yolo(pages_to_scan)

        # Merge and deduplicate
        start = time.time()
        zones = self._merge_detections(docling_detections, yolo_detections)
        self.stats["merge_time"] = time.time() - start

        # Update statistics
        self.stats["docling_tables"] = len(docling_detections)
        self.stats["yolo_tables"] = len(yolo_detections)
        self.stats["duplicates_removed"] = len(docling_detections) + len(yolo_detections) - len(zones)
        self.stats["total_unique"] = len(zones)

        self._print_statistics()

        return zones

    def _detect_with_docling(self) -> List[Dict[str, Any]]:
        """
        Detect tables using Docling (text-based detection).

        Returns:
            List of detection dictionaries with keys:
            - page: int (1-indexed)
            - bbox: List[float] [x0, y0, x1, y1]
            - confidence: float
            - markdown: str (optional)
            - source: str = "docling"
        """
        print("DOCLING DETECTION")
        print("-" * 60)

        start = time.time()
        converter = DocumentConverter()
        result = converter.convert(str(self.pdf_path))
        self.stats["docling_time"] = time.time() - start

        detections = []

        if hasattr(result, 'document') and result.document:
            doc = result.document

            if hasattr(doc, 'tables') and doc.tables:
                print(f"✓ Found {len(doc.tables)} table(s)")

                for i, table in enumerate(doc.tables):
                    # Extract page number
                    page = None
                    if hasattr(table, 'prov') and table.prov:
                        for prov_item in table.prov:
                            if hasattr(prov_item, 'page_no'):
                                page = prov_item.page_no
                                break

                    # Extract bbox
                    bbox = None
                    if hasattr(table, 'prov') and table.prov:
                        for prov_item in table.prov:
                            if hasattr(prov_item, 'bbox'):
                                b = prov_item.bbox
                                bbox = [b.l, b.b, b.r, b.t]
                                break

                    # Get markdown
                    markdown = None
                    if hasattr(table, 'export_to_markdown'):
                        try:
                            markdown = table.export_to_markdown()
                        except:
                            markdown = ""

                    if page and bbox:
                        detections.append({
                            'page': page,
                            'bbox': bbox,
                            'confidence': 1.0,
                            'markdown': markdown or "",
                            'source': 'docling'
                        })
                        print(f"  Page {page}: Table {i+1}")
            else:
                print("⚠️  No tables found")

        print(f"⏱️  Detection time: {self.stats['docling_time']:.1f}s")
        print()

        return detections

    def _detect_with_yolo(self, pages_to_scan: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Detect tables using DocLayout-YOLO (vision-based detection).

        Args:
            pages_to_scan: List of page numbers (1-indexed), or None for all pages

        Returns:
            List of detection dictionaries (same format as Docling)
        """
        print("YOLO DETECTION")
        print("-" * 60)

        start = time.time()

        # Load YOLO model
        print(f"Loading model: {self.yolo_model_path.name}")
        model = YOLOv10(str(self.yolo_model_path))

        # Open PDF
        doc = fitz.open(str(self.pdf_path))
        total_pages = len(doc)

        if pages_to_scan is None:
            pages_to_scan = list(range(1, total_pages + 1))

        print(f"Scanning {len(pages_to_scan)} pages...")

        detections = []

        for page_num in pages_to_scan:
            if page_num > total_pages:
                continue

            page = doc[page_num - 1]  # 0-indexed in PyMuPDF

            # Render page to image (300 DPI for good detection)
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat)

            # Save to temp image
            temp_img = Path(f"temp_page_{page_num}.png")
            pix.save(str(temp_img))

            try:
                # Run YOLO detection
                results = model.predict(
                    str(temp_img),
                    imgsz=1024,
                    conf=self.yolo_conf_threshold,
                    device='cpu'
                )

                # Parse detections
                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        class_id = int(box.cls[0])
                        class_name = result.names[class_id]

                        # Only interested in "table" class
                        if class_name == "table":
                            # Get bbox (in image coordinates, scale back to PDF)
                            x0, y0, x1, y1 = box.xyxy[0].tolist()

                            # Scale from image (300 DPI) back to PDF (72 DPI)
                            scale = 72/300
                            pdf_bbox = [
                                x0 * scale,
                                y0 * scale,
                                x1 * scale,
                                y1 * scale
                            ]

                            confidence = float(box.conf[0])

                            detections.append({
                                'page': page_num,
                                'bbox': pdf_bbox,
                                'confidence': confidence,
                                'source': 'yolo'
                            })

                            print(f"  Page {page_num}: Table (conf={confidence:.3f})")

            finally:
                # Clean up temp image
                if temp_img.exists():
                    temp_img.unlink()

        doc.close()

        self.stats["yolo_time"] = time.time() - start
        print(f"✓ Found {len(detections)} table(s)")
        print(f"⏱️  Detection time: {self.stats['yolo_time']:.1f}s")
        print()

        return detections

    def _merge_detections(
        self,
        docling_detections: List[Dict[str, Any]],
        yolo_detections: List[Dict[str, Any]]
    ) -> List[Zone]:
        """
        Merge detections from both sources and remove duplicates.

        Strategy:
        ---------
        1. Keep ALL Docling detections (they have markdown data)
        2. Add YOLO detections that don't overlap significantly with Docling
        3. Use Intersection over Union (IoU) to detect duplicates

        Args:
            docling_detections: Detections from Docling
            yolo_detections: Detections from YOLO

        Returns:
            List of Zone objects representing unique tables
        """
        print("MERGING DETECTIONS")
        print("-" * 60)

        def compute_iou(bbox1: List[float], bbox2: List[float]) -> float:
            """Compute Intersection over Union for two bounding boxes."""
            x0_1, y0_1, x1_1, y1_1 = bbox1
            x0_2, y0_2, x1_2, y1_2 = bbox2

            # Intersection
            x0_i = max(x0_1, x0_2)
            y0_i = max(y0_1, y0_2)
            x1_i = min(x1_1, x1_2)
            y1_i = min(y1_1, y1_2)

            if x1_i <= x0_i or y1_i <= y0_i:
                return 0.0

            intersection = (x1_i - x0_i) * (y1_i - y0_i)

            # Union
            area1 = (x1_1 - x0_1) * (y1_1 - y0_1)
            area2 = (x1_2 - x0_2) * (y1_2 - y0_2)
            union = area1 + area2 - intersection

            return intersection / union if union > 0 else 0.0

        # Start with all Docling detections (they have markdown)
        merged = list(docling_detections)

        # Add non-duplicate YOLO detections
        for yolo_det in yolo_detections:
            is_duplicate = False

            for docling_det in docling_detections:
                # Only compare on same page
                if yolo_det['page'] != docling_det['page']:
                    continue

                iou = compute_iou(yolo_det['bbox'], docling_det['bbox'])
                if iou > self.iou_threshold:
                    is_duplicate = True
                    print(f"  Page {yolo_det['page']}: YOLO duplicate removed (IoU={iou:.2f})")
                    break

            if not is_duplicate:
                merged.append(yolo_det)
                print(f"  Page {yolo_det['page']}: YOLO table added (unique)")

        # Convert to Zone objects
        zones = []
        for i, det in enumerate(merged):
            zone_id = f"table_{det['page']}_{i}"

            # Preserve markdown for Docling detections
            metadata = {
                'source': det['source'],
                'confidence': det['confidence']
            }
            if 'markdown' in det:
                metadata['markdown'] = det['markdown']

            zone = Zone(
                zone_id=zone_id,
                type='table',
                page=det['page'],
                bbox=det['bbox'],
                metadata=metadata
            )
            zones.append(zone)

        print(f"✓ Merged total: {len(zones)} unique table(s)")
        print(f"  From Docling: {len(docling_detections)}")
        print(f"  From YOLO (unique): {len(merged) - len(docling_detections)}")
        print()

        return zones

    def _print_statistics(self):
        """Print detection statistics."""
        print("=" * 80)
        print("DETECTION SUMMARY")
        print("=" * 80)
        print(f"  Docling tables: {self.stats['docling_tables']}")
        print(f"  YOLO tables: {self.stats['yolo_tables']}")
        print(f"  Duplicates removed: {self.stats['duplicates_removed']}")
        print(f"  Total unique: {self.stats['total_unique']}")
        print()
        print(f"  Docling time: {self.stats['docling_time']:.1f}s")
        print(f"  YOLO time: {self.stats['yolo_time']:.1f}s")
        print(f"  Merge time: {self.stats['merge_time']:.3f}s")
        print(f"  Total time: {self.stats['docling_time'] + self.stats['yolo_time'] + self.stats['merge_time']:.1f}s")
        print("=" * 80)
        print()


if __name__ == "__main__":
    # Test on Chapter 4
    pdf_path = Path("tests/test_data/Ch-04_Heat_Transfer.pdf")

    if not pdf_path.exists():
        print(f"ERROR: Test PDF not found: {pdf_path}")
        sys.exit(1)

    # Run hybrid detection
    detector = TableDetectionAgent(pdf_path)
    zones = detector.detect_tables()

    # Show results
    print(f"Detected {len(zones)} table zones:")
    for zone in zones:
        source = zone.metadata.get('source', 'unknown')
        conf = zone.metadata.get('confidence', 0.0)
        has_markdown = 'markdown' in zone.metadata
        print(f"  {zone.zone_id} (page {zone.page}) - {source} (conf={conf:.3f}) [markdown: {has_markdown}]")
