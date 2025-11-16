# -*- coding: utf-8 -*-
"""
Unified Detection Module - Single-Pass DocLayout-YOLO Object Detection

This module runs DocLayout-YOLO ONCE to detect ALL object types simultaneously:
- Equations (isolate_formula + formula_caption)
- Figures (figure + figure_caption)
- Text blocks (text)

Design Rationale:
-----------------
- **Efficiency**: Single scan instead of multiple redundant scans
- **Reuse**: Outputs zones for existing RAG agents (no agent modification)
- **Parallelization**: Page-level parallel processing for maximum throughput
- **Pairing**: Intelligent algorithm matches formulas with captions

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

import fitz
from doclayout_yolo import YOLOv10
from pathlib import Path
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

# Import Zone from base agent (v14 package import)
from common.src.base.base_extraction_agent import Zone


@dataclass
class Detection:
    """Raw YOLO detection before conversion to Zone."""
    class_name: str
    confidence: float
    page_num: int
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    text: str = ""

    @property
    def center_x(self):
        return (self.bbox[0] + self.bbox[2]) / 2

    @property
    def center_y(self):
        return (self.bbox[1] + self.bbox[3]) / 2

    def distance_to(self, other: 'Detection') -> float:
        dx = self.center_x - other.center_x
        dy = self.center_y - other.center_y
        return (dx**2 + dy**2) ** 0.5


class UnifiedDetectionModule:
    """
    Single-pass detection using DocLayout-YOLO.

    Detects equations, figures, and text in ONE scan with page-level parallelization.
    """

    # Map YOLO classes to our object types
    CLASS_MAPPING = {
        'isolate_formula': 'equation',
        'formula_caption': 'equation_number',
        'figure': 'figure',
        'figure_caption': 'figure_caption',
        'text': 'text',
        'title': 'title'
    }

    def __init__(self, model_path: str, confidence_threshold: float = 0.2):
        """
        Initialize unified detector.

        Args:
            model_path: Path to DocLayout-YOLO model
            confidence_threshold: Minimum confidence (default: 0.2)
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold

    def detect_all_objects(self, pdf_path: Path, num_workers: int = 8,
                          start_page: int = 0, end_page: Optional[int] = None) -> List[Zone]:
        """
        Detect ALL object types in a single pass with parallel page processing.

        Args:
            pdf_path: Path to PDF file
            num_workers: Number of parallel workers
            start_page: Starting page (0-indexed)
            end_page: Ending page (None = all pages)

        Returns:
            List[Zone] ready for existing RAG agents
        """
        print(f"\n{'='*80}")
        print(f"UNIFIED DETECTION - SINGLE PASS")
        print(f"{'='*80}")
        print(f"PDF: {pdf_path}")
        print(f"Workers: {num_workers}")
        print(f"Confidence: {self.confidence_threshold}")
        print()

        # Get page range
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        if end_page is None:
            end_page = total_pages - 1
        doc.close()

        pages_to_process = list(range(start_page, end_page + 1))
        print(f"Processing {len(pages_to_process)} pages (pages {start_page+1} to {end_page+1})")
        print()

        # Process pages in parallel
        all_detections = []
        start_time = datetime.now()

        print("Starting parallel page detection...")
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            future_to_page = {
                executor.submit(
                    _detect_page_worker,
                    str(pdf_path),
                    page_num,
                    self.model_path,
                    self.confidence_threshold
                ): page_num
                for page_num in pages_to_process
            }

            completed = 0
            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    page_detections = future.result()
                    all_detections.extend(page_detections)
                    completed += 1
                    print(f"  Page {page_num+1}: {len(page_detections)} objects "
                          f"({completed}/{len(pages_to_process)} pages)")
                except Exception as e:
                    print(f"  Page {page_num+1}: ERROR - {e}")

        duration = (datetime.now() - start_time).total_seconds()
        print()
        print(f"Detection complete in {duration:.1f}s ({len(all_detections)} raw detections)")
        print()

        # Convert to zones
        zones = self._convert_to_zones(all_detections)

        # Print summary
        self._print_summary(zones, duration)

        return zones

    def _convert_to_zones(self, detections: List[Detection]) -> List[Zone]:
        """
        Convert raw detections to Zone objects.

        Process:
        1. Separate by type (equations, figures, text)
        2. Pair equations with equation numbers
        3. Pair figures with captions
        4. Create Zone objects with metadata
        """
        print("Converting detections to zones...")

        # Separate by type
        equations = [d for d in detections if d.class_name == 'isolate_formula']
        eq_numbers = [d for d in detections if d.class_name == 'formula_caption']
        figures = [d for d in detections if d.class_name == 'figure']
        fig_captions = [d for d in detections if d.class_name == 'figure_caption']
        text_blocks = [d for d in detections if d.class_name == 'text']

        zones = []

        # Create equation zones with paired numbers
        equation_zones = self._create_equation_zones(equations, eq_numbers)
        zones.extend(equation_zones)

        # Create figure zones with paired captions
        figure_zones = self._create_figure_zones(figures, fig_captions)
        zones.extend(figure_zones)

        # Create text zones
        text_zones = self._create_text_zones(text_blocks)
        zones.extend(text_zones)

        return zones

    def _create_equation_zones(self, equations: List[Detection],
                              equation_numbers: List[Detection]) -> List[Zone]:
        """Pair equations with numbers and create zones."""
        zones = []
        used_numbers = set()

        for i, eq in enumerate(equations):
            # Find nearest equation number to the right
            best_num = None
            best_distance = float('inf')

            for j, num in enumerate(equation_numbers):
                if j in used_numbers or num.page_num != eq.page_num:
                    continue

                # Check if number is to the right and aligned
                if num.center_x > eq.center_x:
                    y_diff = abs(num.center_y - eq.center_y)
                    if y_diff < 20:  # Within 20pts vertically
                        distance = eq.distance_to(num)
                        if distance < best_distance:
                            best_distance = distance
                            best_num = (j, num)

            # Create zone with or without number
            zone_id = f"eq_unknown_{eq.page_num}_{i}"
            metadata = {}

            if best_num:
                num_idx, num_det = best_num
                used_numbers.add(num_idx)

                # Extract equation number from text
                matches = re.findall(r'\((\d+[a-z]?)\)', num_det.text)
                if matches:
                    eq_num = matches[0]
                    zone_id = f"eq_{eq_num}"
                    metadata['equation_number'] = eq_num
                    metadata['number_bbox'] = list(num_det.bbox)
                    metadata['number_confidence'] = num_det.confidence

            zone = Zone(
                zone_id=zone_id,
                type="equation",
                page=eq.page_num + 1,  # 1-indexed
                bbox=list(eq.bbox),
                metadata=metadata
            )
            zones.append(zone)

        return zones

    def _create_figure_zones(self, figures: List[Detection],
                            captions: List[Detection]) -> List[Zone]:
        """Pair figures with captions and create zones."""
        zones = []
        used_captions = set()

        for i, fig in enumerate(figures):
            # Find nearest caption below figure
            best_cap = None
            best_distance = float('inf')

            for j, cap in enumerate(captions):
                if j in used_captions or cap.page_num != fig.page_num:
                    continue

                # Check if caption is below figure
                if cap.center_y > fig.center_y:
                    # Check horizontal overlap
                    fig_x0, _, fig_x1, _ = fig.bbox
                    cap_x0, _, cap_x1, _ = cap.bbox
                    overlap = (min(fig_x1, cap_x1) - max(fig_x0, cap_x0)) / min(fig_x1 - fig_x0, cap_x1 - cap_x0)

                    if overlap > 0.3:  # At least 30% overlap
                        distance = fig.distance_to(cap)
                        if distance < best_distance:
                            best_distance = distance
                            best_cap = (j, cap)

            # Create zone
            zone_id = f"fig_unknown_{fig.page_num}_{i}"
            metadata = {}

            if best_cap:
                cap_idx, cap_det = best_cap
                used_captions.add(cap_idx)
                metadata['caption'] = cap_det.text
                metadata['caption_bbox'] = list(cap_det.bbox)
                metadata['caption_confidence'] = cap_det.confidence

                # Try to extract figure number
                matches = re.findall(r'[Ff]igure\s*(\d+[a-z]?)', cap_det.text)
                if matches:
                    fig_num = matches[0]
                    zone_id = f"fig_{fig_num}"

            zone = Zone(
                zone_id=zone_id,
                type="figure",
                page=fig.page_num + 1,
                bbox=list(fig.bbox),
                metadata=metadata
            )
            zones.append(zone)

        return zones

    def _create_text_zones(self, text_blocks: List[Detection]) -> List[Zone]:
        """Create zones for text blocks."""
        zones = []

        for i, txt in enumerate(text_blocks):
            zone_id = f"text_{txt.page_num}_{i}"

            zone = Zone(
                zone_id=zone_id,
                type="text",
                page=txt.page_num + 1,
                bbox=list(txt.bbox),
                metadata={'text_preview': txt.text[:100] if txt.text else ""}
            )
            zones.append(zone)

        return zones

    def _print_summary(self, zones: List[Zone], processing_time: float):
        """Print detection summary."""
        print(f"{'='*80}")
        print(f"DETECTION SUMMARY")
        print(f"{'='*80}")

        by_type = {}
        for zone in zones:
            by_type[zone.type] = by_type.get(zone.type, 0) + 1

        print(f"Total zones: {len(zones)}")
        for zone_type, count in sorted(by_type.items()):
            print(f"  {zone_type}: {count}")

        print()
        print(f"Processing time: {processing_time:.1f}s")
        print(f"Speed: {len(zones) / processing_time:.1f} zones/second")
        print()


# Worker function for parallel processing
def _detect_page_worker(pdf_path: str, page_num: int,
                       model_path: str, confidence_threshold: float) -> List[Detection]:
    """
    Process single page with YOLO detection.

    Called by worker processes in the pool.
    """
    # Load model in worker
    model = YOLOv10(model_path)

    # Open PDF and extract page
    doc = fitz.open(pdf_path)
    page = doc[page_num]

    # Render at 300 DPI
    mat = fitz.Matrix(300/72, 300/72)
    pix = page.get_pixmap(matrix=mat)

    # Save temp image
    temp_dir = Path("temp_detection")
    temp_dir.mkdir(exist_ok=True)
    temp_img = temp_dir / f"page_{page_num}_pid{os.getpid()}.png"
    pix.save(str(temp_img))

    # Run YOLO
    results = model.predict(
        str(temp_img),
        imgsz=1024,
        conf=confidence_threshold,
        device='cpu',
        verbose=False
    )

    # Clean up
    temp_img.unlink()

    # Parse detections
    detections = []
    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            cls_name = result.names[cls_id]

            # Skip classes we don't care about
            if cls_name not in UnifiedDetectionModule.CLASS_MAPPING:
                continue

            conf = float(box.conf[0])
            xyxy = box.xyxy[0]

            # Convert to page coordinates
            scale = 72/300
            x0 = float(xyxy[0]) * scale
            y0 = float(xyxy[1]) * scale
            x1 = float(xyxy[2]) * scale
            y1 = float(xyxy[3]) * scale

            # Extract text
            bbox = fitz.Rect(x0, y0, x1, y1)
            text = page.get_text("text", clip=bbox).strip()

            detection = Detection(
                class_name=cls_name,
                confidence=conf,
                page_num=page_num,
                bbox=(x0, y0, x1, y1),
                text=text
            )
            detections.append(detection)

    doc.close()
    return detections
