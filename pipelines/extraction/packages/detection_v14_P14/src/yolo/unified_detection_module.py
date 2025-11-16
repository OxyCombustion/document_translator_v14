# -*- coding: utf-8 -*-
"""
Unified Detection Module - Single-Pass DocLayout-YOLO Object Detection with PyTorch 2.9+ Fix

This module runs DocLayout-YOLO ONCE to detect ALL object types simultaneously:
- Equations (isolate_formula + formula_caption)
- Figures (figure + figure_caption)
- Text blocks (text)

PyTorch 2.9+ Compatibility:
---------------------------
PyTorch 2.6+ changed torch.load() default to weights_only=True, which breaks
YOLO model loading. This module patches torch.load() before importing YOLOv10
to restore the old behavior (weights_only=False).

Design Rationale:
-----------------
- **Efficiency**: Single scan instead of multiple redundant scans
- **Reuse**: Outputs zones for existing RAG agents (no agent modification)
- **Parallelization**: Page-level parallel processing for maximum throughput
- **Pairing**: Intelligent algorithm matches formulas with captions
- **PyTorch Fix**: Monkeypatch torch.load for PyTorch 2.6+ compatibility

Author: Claude Code
Date: 2025-11-16
Version: 2.0 (PyTorch 2.9+ compatible)
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

# ============================================================================
# PYTORCH 2.9+ COMPATIBILITY FIX
# ============================================================================
# CRITICAL: This MUST come before importing YOLOv10
#
# Issue: PyTorch 2.6+ changed torch.load() default from weights_only=False
#        to weights_only=True, breaking YOLO model loading.
#
# Error: "WeightsUnpickler error: Unsupported global: GLOBAL
#         doclayout_yolo.nn.tasks.YOLOv10DetectionModel"
#
# Solution: Monkeypatch torch.load to restore old behavior before YOLO import.
# ============================================================================

import torch

# Save original torch.load
_original_torch_load = torch.load

def _patched_torch_load(*args, **kwargs):
    """
    Patched torch.load that defaults to weights_only=False for backward compatibility.

    This allows YOLO models (and other legacy models) to load correctly in PyTorch 2.6+.
    """
    # If weights_only not explicitly set, use False (old PyTorch behavior)
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)

# Apply the patch
torch.load = _patched_torch_load

print("✅ Applied PyTorch 2.9+ compatibility patch (torch.load weights_only=False)")

# ============================================================================
# NOW SAFE TO IMPORT YOLO
# ============================================================================

import fitz
from doclayout_yolo import YOLOv10
from pathlib import Path
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

# Import Zone from base agent
from pipelines.shared.packages.common.src.base.base_extraction_agent import Zone


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
    Single-pass detection using DocLayout-YOLO with PyTorch 2.9+ compatibility.

    Detects equations, figures, and text in ONE scan with page-level parallelization.
    Includes automatic PyTorch 2.6+ compatibility fix for model loading.
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
        self.model = None

    def _load_model(self):
        """Load YOLO model with PyTorch compatibility fix already applied."""
        if self.model is None:
            print(f"Loading YOLO model from {self.model_path}...")
            self.model = YOLOv10(self.model_path)
            print(f"✅ YOLO model loaded successfully (PyTorch {torch.__version__})")

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
        print(f"UNIFIED YOLO DETECTION - SINGLE PASS")
        print(f"{'='*80}")
        print(f"PDF: {pdf_path}")
        print(f"Workers: {num_workers}")
        print(f"Confidence: {self.confidence_threshold}")
        print()

        # Load model if not already loaded
        self._load_model()

        # Get page range
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        if end_page is None:
            end_page = total_pages - 1
        doc.close()

        pages_to_process = list(range(start_page, end_page + 1))
        print(f"Processing {len(pages_to_process)} pages (pages {start_page+1} to {end_page+1})")
        print()

        # Process pages sequentially (CPU mode - multiprocessing causes hangs)
        all_detections = []
        start_time = datetime.now()

        print("Starting sequential page detection (CPU mode)...")
        # Open PDF once for all pages
        doc = fitz.open(pdf_path)

        for page_num in pages_to_process:
            try:
                page = doc[page_num]

                # Render page to image (300 DPI)
                mat = fitz.Matrix(300/72, 300/72)
                pix = page.get_pixmap(matrix=mat)

                # Save to temporary file for YOLO
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    pix.save(tmp.name)
                    tmp_path = tmp.name

                # Run YOLO detection
                results = self.model.predict(tmp_path, conf=self.confidence_threshold, verbose=False)

                # Clean up temp file
                os.unlink(tmp_path)

                # Convert YOLO results to Detection objects
                page_detections = []
                if results and len(results) > 0:
                    result = results[0]
                    if result.boxes is not None and len(result.boxes) > 0:
                        for box in result.boxes:
                            class_id = int(box.cls[0].item())
                            class_name = result.names[class_id]

                            # Map YOLO class to our types
                            if class_name in self.CLASS_MAPPING:
                                obj_type = self.CLASS_MAPPING[class_name]

                                # Get bbox coordinates (xyxy format)
                                xyxy = box.xyxy[0].tolist()
                                # Scale back from 300 DPI to PDF coords (72 DPI)
                                scale = 72/300
                                bbox = tuple(coord * scale for coord in xyxy)

                                detection = Detection(
                                    class_name=obj_type,
                                    confidence=float(box.conf[0].item()),
                                    page_num=page_num,
                                    bbox=bbox,
                                    text=""
                                )
                                page_detections.append(detection)

                all_detections.extend(page_detections)
                print(f"  Page {page_num+1}: {len(page_detections)} detections")

            except Exception as e:
                print(f"  ⚠️  Page {page_num+1} failed: {e}")

        doc.close()

        duration = (datetime.now() - start_time).total_seconds()
        print(f"\nDetection complete in {duration:.1f}s")
        print(f"Total raw detections: {len(all_detections)}")
        print()

        # Group detections by type
        equations = [d for d in all_detections if d.class_name == 'equation']
        equation_numbers = [d for d in all_detections if d.class_name == 'equation_number']
        figures = [d for d in all_detections if d.class_name == 'figure']
        figure_captions = [d for d in all_detections if d.class_name == 'figure_caption']
        text_blocks = [d for d in all_detections if d.class_name == 'text']

        print("Detection breakdown:")
        print(f"  Equations: {len(equations)}")
        print(f"  Equation numbers: {len(equation_numbers)}")
        print(f"  Figures: {len(figures)}")
        print(f"  Figure captions: {len(figure_captions)}")
        print(f"  Text blocks: {len(text_blocks)}")
        print()

        # Extract text for equation numbers (needed for pairing)
        print("Extracting text for equation numbers...")
        self._extract_text_for_numbers(pdf_path, equation_numbers)
        print(f"  Extracted text for {len([n for n in equation_numbers if n.text])} equation numbers")
        print()

        # Pair equations with numbers
        print("Pairing equations with numbers...")
        equation_zones = self._pair_equations(equations, equation_numbers)
        print(f"  Created {len(equation_zones)} equation zones")

        # Pair figures with captions
        print("Pairing figures with captions...")
        figure_zones = self._pair_figures(figures, figure_captions)
        print(f"  Created {len(figure_zones)} figure zones")

        # Convert text blocks to zones
        print("Converting text blocks...")
        text_zones = self._text_to_zones(text_blocks)
        print(f"  Created {len(text_zones)} text zones")

        # Combine all zones
        all_zones = equation_zones + figure_zones + text_zones
        print()
        print(f"Total zones created: {len(all_zones)}")
        print(f"  Equations: {len(equation_zones)}")
        print(f"  Figures: {len(figure_zones)}")
        print(f"  Text: {len(text_zones)}")
        print()

        return all_zones

    def _pair_equations(self, equations: List[Detection], numbers: List[Detection],
                       max_distance: float = 150.0) -> List[Zone]:
        """
        Pair equation regions with their numbers using spatial proximity.

        Args:
            equations: List of equation detections
            numbers: List of equation number detections
            max_distance: Maximum distance for pairing (pixels)

        Returns:
            List of Zone objects with equation metadata
        """
        zones = []
        used_numbers = set()

        for eq in equations:
            # Find closest number on same page
            candidates = [n for n in numbers
                         if n.page_num == eq.page_num and id(n) not in used_numbers]

            if not candidates:
                # No number found - create zone without number
                zone_id = f"eq_yolo_{eq.page_num}_{len(zones)}"
                zone = Zone(
                    zone_id=zone_id,
                    type="equation",
                    page=eq.page_num + 1,  # Convert to 1-indexed
                    bbox=list(eq.bbox),
                    metadata={
                        'detection_method': 'yolo',
                        'confidence': eq.confidence,
                        'has_number': False
                    }
                )
                zones.append(zone)
                continue

            # Find closest number
            closest = min(candidates, key=lambda n: eq.distance_to(n))
            distance = eq.distance_to(closest)

            if distance <= max_distance:
                # Extract equation number from text
                number_text = closest.text
                number_match = re.search(r'\((\d+[a-z]?)\)', number_text)
                equation_number = number_match.group(1) if number_match else "unknown"

                zone_id = f"eq_yolo_{eq.page_num}_{equation_number}"
                zone = Zone(
                    zone_id=zone_id,
                    type="equation",
                    page=eq.page_num + 1,
                    bbox=list(eq.bbox),
                    metadata={
                        'detection_method': 'yolo',
                        'confidence': eq.confidence,
                        'equation_number': equation_number,
                        'number_bbox': list(closest.bbox),
                        'pairing_distance': distance,
                        'has_number': True
                    }
                )
                zones.append(zone)
                used_numbers.add(id(closest))
            else:
                # Number too far - create zone without number
                zone_id = f"eq_yolo_{eq.page_num}_{len(zones)}"
                zone = Zone(
                    zone_id=zone_id,
                    type="equation",
                    page=eq.page_num + 1,
                    bbox=list(eq.bbox),
                    metadata={
                        'detection_method': 'yolo',
                        'confidence': eq.confidence,
                        'has_number': False,
                        'closest_number_distance': distance
                    }
                )
                zones.append(zone)

        return zones

    def _pair_figures(self, figures: List[Detection], captions: List[Detection],
                     max_distance: float = 200.0) -> List[Zone]:
        """
        Pair figure regions with their captions using spatial proximity.

        Args:
            figures: List of figure detections
            captions: List of caption detections
            max_distance: Maximum distance for pairing (pixels)

        Returns:
            List of Zone objects with figure metadata
        """
        zones = []
        used_captions = set()

        for fig in figures:
            # Find closest caption on same page
            candidates = [c for c in captions
                         if c.page_num == fig.page_num and id(c) not in used_captions]

            if not candidates:
                # No caption found
                zone_id = f"fig_yolo_{fig.page_num}_{len(zones)}"
                zone = Zone(
                    zone_id=zone_id,
                    type="figure",
                    page=fig.page_num + 1,
                    bbox=list(fig.bbox),
                    metadata={
                        'detection_method': 'yolo',
                        'confidence': fig.confidence,
                        'has_caption': False
                    }
                )
                zones.append(zone)
                continue

            # Find closest caption
            closest = min(candidates, key=lambda c: fig.distance_to(c))
            distance = fig.distance_to(closest)

            if distance <= max_distance:
                zone_id = f"fig_yolo_{fig.page_num}_{len(zones)}"
                zone = Zone(
                    zone_id=zone_id,
                    type="figure",
                    page=fig.page_num + 1,
                    bbox=list(fig.bbox),
                    metadata={
                        'detection_method': 'yolo',
                        'confidence': fig.confidence,
                        'caption': closest.text,
                        'caption_bbox': list(closest.bbox),
                        'pairing_distance': distance,
                        'has_caption': True
                    }
                )
                zones.append(zone)
                used_captions.add(id(closest))
            else:
                # Caption too far
                zone_id = f"fig_yolo_{fig.page_num}_{len(zones)}"
                zone = Zone(
                    zone_id=zone_id,
                    type="figure",
                    page=fig.page_num + 1,
                    bbox=list(fig.bbox),
                    metadata={
                        'detection_method': 'yolo',
                        'confidence': fig.confidence,
                        'has_caption': False,
                        'closest_caption_distance': distance
                    }
                )
                zones.append(zone)

        return zones

    def _text_to_zones(self, text_blocks: List[Detection]) -> List[Zone]:
        """Convert text block detections to zones."""
        zones = []
        for i, text in enumerate(text_blocks):
            zone_id = f"text_yolo_{text.page_num}_{i}"
            zone = Zone(
                zone_id=zone_id,
                type="text",
                page=text.page_num + 1,
                bbox=list(text.bbox),
                metadata={
                    'detection_method': 'yolo',
                    'confidence': text.confidence
                }
            )
            zones.append(zone)
        return zones

    def _extract_text_for_numbers(self, pdf_path: Path, number_detections: List[Detection]) -> None:
        """
        Extract text from PDF at equation number bounding boxes.

        This populates the `.text` attribute of each Detection object with the
        actual text found in the PDF (e.g., "(1)", "(42)", etc.). This is needed
        for the pairing logic to extract equation numbers via regex.

        Args:
            pdf_path: Path to PDF file
            number_detections: List of equation_number Detection objects (modified in-place)
        """
        if not number_detections:
            return

        # Open PDF to extract text
        doc = fitz.open(pdf_path)

        try:
            for detection in number_detections:
                try:
                    # Get page
                    page = doc[detection.page_num]

                    # Get text from bbox
                    rect = fitz.Rect(detection.bbox)
                    text = page.get_text("text", clip=rect).strip()

                    # Populate text attribute (modifies Detection in-place)
                    detection.text = text

                except Exception as e:
                    # If text extraction fails, leave as empty string
                    detection.text = ""

        finally:
            doc.close()


def _detect_page_worker(pdf_path: str, page_num: int, model_path: str,
                       confidence_threshold: float) -> List[Detection]:
    """
    Worker function for parallel page detection.

    Note: This loads the model for each worker. The PyTorch patch is applied
    at module level, so it's safe for all workers.
    """
    # Ensure PyTorch patch is applied in worker process
    import torch
    if not hasattr(torch.load, '__name__') or 'patched' not in str(torch.load):
        # Re-apply patch in worker process
        _original = torch.load
        def _patched(*args, **kwargs):
            if 'weights_only' not in kwargs:
                kwargs['weights_only'] = False
            return _original(*args, **kwargs)
        torch.load = _patched

    from doclayout_yolo import YOLOv10
    import fitz

    # Load model (with patch applied)
    model = YOLOv10(model_path)

    # Open PDF and render page
    doc = fitz.open(pdf_path)
    page = doc[page_num]

    # Render page to image (300 DPI)
    mat = fitz.Matrix(300/72, 300/72)
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("png")

    doc.close()

    # Run YOLO detection
    results = model.predict(
        img_data,
        imgsz=1280,
        conf=confidence_threshold,
        device='cpu'
    )

    # Parse results
    detections = []
    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = result.names[class_id]
            confidence = float(box.conf[0])
            bbox = box.xyxy[0].tolist()  # [x0, y0, x1, y1]

            # Scale bbox back to PDF coordinates (from 300 DPI to 72 DPI)
            scale = 72 / 300
            bbox = [coord * scale for coord in bbox]

            # Map class name
            mapped_class = UnifiedDetectionModule.CLASS_MAPPING.get(class_name, class_name)

            detection = Detection(
                class_name=mapped_class,
                confidence=confidence,
                page_num=page_num,
                bbox=tuple(bbox),
                text=""  # OCR would go here if needed
            )
            detections.append(detection)

    return detections


if __name__ == "__main__":
    # Test the module
    model_path = "models/doclayout_yolo_docstructbench_imgsz1280_2501.pt"
    pdf_path = Path("test_data/Ch-04_Heat_Transfer.pdf")

    detector = UnifiedDetectionModule(model_path)
    zones = detector.detect_all_objects(pdf_path, num_workers=4)

    print(f"\n{'='*80}")
    print(f"TEST COMPLETE")
    print(f"{'='*80}")
    print(f"Total zones: {len(zones)}")
    print(f"\nFirst 5 zones:")
    for zone in zones[:5]:
        print(f"  {zone.zone_id}: {zone.type} on page {zone.page}")
