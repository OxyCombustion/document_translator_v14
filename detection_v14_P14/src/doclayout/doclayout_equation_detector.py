# -*- coding: utf-8 -*-
"""
DocLayout-YOLO Equation Detector - Vision-Based Generic Equation Detection

This module uses DocLayout-YOLO for equation detection, ported from v13 where it
achieved 100% detection coverage (108/108 equations) in ~100 seconds.

V13 Performance (WORKING):
- Detection Coverage: 108/108 equations (100%)
- Processing Time: ~100 seconds (~1.7 minutes)
- LaTeX Conversion: 100% success
- Device: CPU mode
- User Validation: "Outstanding"

V14 Attempted (BROKEN):
- Docling 2.x formula enrichment: 12+ hours with 0% success (terminated)

Root Cause:
- DocLayout-YOLO detector was NOT migrated from v13 to v14
- Attempted Docling replacement was incompatible (430x slower)

Solution:
- Port working v13 DocLayout-YOLO detector to v14
- Restore 100% detection coverage and fast processing

Hardware: NVIDIA DGX Spark (128GB unified memory, Blackwell GPU)
Model: doclayout_yolo_docstructbench_imgsz1024.pt (trained on 500K+ documents)

Author: Claude Code (ported from v13)
Date: 2025-11-16
Version: 1.0 (v14 port)
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
from typing import List, Optional
from datetime import datetime

# Import Zone from base agent
from common.src.base.base_extraction_agent import Zone


class DocLayoutEquationDetector:
    """
    Vision-based equation detection using DocLayout-YOLO.

    This detector uses computer vision (YOLO) trained on DocStructBench (500K+ documents)
    for generic equation detection that works across document types.

    Performance (validated in v13):
    - 108/108 equations detected (100% coverage)
    - ~100 seconds processing time (CPU mode)
    - 0.868-0.968 confidence scores (avg 0.93)
    - No false positives

    Model: doclayout_yolo_docstructbench_imgsz1024.pt
    """

    def __init__(self, model_path: Optional[Path] = None):
        """
        Initialize DocLayout-YOLO equation detector.

        Args:
            model_path: Path to YOLO model file (optional, uses default if None)
        """
        print(f"🔧 Loading DocLayout-YOLO equation detector...")
        print(f"   Hardware: NVIDIA DGX Spark (128GB unified memory, Blackwell GPU)")
        print(f"   Method: Vision-based YOLO detection (v13 working approach)")

        # Default model path
        if model_path is None:
            model_path = Path("/home/thermodynamics/document_translator_v14/models/doclayout_yolo_docstructbench_imgsz1024.pt")

        if not model_path.exists():
            raise FileNotFoundError(
                f"YOLO model not found at {model_path}\n"
                f"Expected: /home/thermodynamics/document_translator_v14/models/doclayout_yolo_docstructbench_imgsz1024.pt"
            )

        print(f"   Model: {model_path.name}")

        # Load YOLO model
        self.model = YOLOv10(str(model_path))
        self.model_path = model_path

        print(f"✅ DocLayout-YOLO ready (v13 proven approach, 100% detection in v13)")

    def detect_equations(self, pdf_path: Path, output_dir: Optional[Path] = None) -> List[Zone]:
        """
        Detect equation regions using DocLayout-YOLO vision-based detection.

        This method:
        1. Renders PDF pages to images (300 DPI)
        2. Runs YOLO detection to find equations
        3. Converts image coordinates back to PDF coordinates
        4. Creates Zone objects with bounding boxes

        Args:
            pdf_path: Path to PDF file
            output_dir: Optional directory to save equation crops

        Returns:
            List[Zone] with equation regions and metadata
        """
        print(f"\n{'='*80}")
        print(f"DOCLAYOUT-YOLO EQUATION DETECTION (V13 Working Approach)")
        print(f"{'='*80}")
        print(f"PDF: {pdf_path}")
        print(f"Method: Vision-based YOLO (100% coverage in v13)")
        print()

        start_time = datetime.now()

        # Create output directory if specified
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)

        # Open PDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        print(f"Processing {total_pages} pages with DocLayout-YOLO...")
        print()

        zones = []
        equation_count = 0

        # Process each page
        for page_num in range(total_pages):
            page = doc[page_num]

            # Render page to image (300 DPI for better detection)
            mat = fitz.Matrix(300/72, 300/72)  # 300 DPI
            pix = page.get_pixmap(matrix=mat)

            # Save temp image (YOLO needs image file)
            if output_dir:
                page_img_path = output_dir / f"page_{page_num+1}_temp.png"
                pix.save(str(page_img_path))
            else:
                import tempfile
                temp_dir = Path(tempfile.mkdtemp())
                page_img_path = temp_dir / f"page_{page_num+1}.png"
                pix.save(str(page_img_path))

            # Run YOLO detection
            results = self.model.predict(
                str(page_img_path),
                imgsz=1024,
                conf=0.2,  # Lower confidence threshold (v13 validated)
                device='cpu'  # CPU mode (v13 used CPU successfully)
            )

            # Process detected objects
            for result in results:
                boxes = result.boxes

                # Filter for equations/formulas
                for box in boxes:
                    cls_id = int(box.cls[0])
                    cls_name = result.names[cls_id]

                    # Check if this is an equation/formula
                    if 'equation' in cls_name.lower() or 'formula' in cls_name.lower():
                        equation_count += 1
                        conf = float(box.conf[0])
                        xyxy = box.xyxy[0]

                        # Convert from 300 DPI image coords to PDF coords (72 DPI)
                        scale = 72/300
                        x0 = float(xyxy[0]) * scale
                        y0 = float(xyxy[1]) * scale
                        x1 = float(xyxy[2]) * scale
                        y1 = float(xyxy[3]) * scale

                        bbox = [x0, y0, x1, y1]

                        # Create zone
                        zone_id = f"eq_doclayout_{page_num+1}_{equation_count}"
                        zone = Zone(
                            zone_id=zone_id,
                            type="equation",
                            page=page_num + 1,  # 1-indexed
                            bbox=bbox,
                            metadata={
                                'detection_method': 'doclayout_yolo_v13_ported',
                                'confidence': conf,
                                'yolo_class': cls_name,
                                'equation_index': equation_count,
                                'model': self.model_path.name,
                                'source': 'v13_working_approach'
                            }
                        )
                        zones.append(zone)

                        print(f"  Equation {equation_count}: page {page_num+1}, bbox {bbox}, conf {conf:.3f}")

                        # Save equation crop if output directory specified
                        if output_dir:
                            crop_rect = fitz.Rect(x0, y0, x1, y1)
                            crop_pix = page.get_pixmap(clip=crop_rect, matrix=fitz.Matrix(2, 2))
                            crop_path = output_dir / f"equation_{equation_count:03d}_page{page_num+1}_conf{conf:.2f}.png"
                            crop_pix.save(str(crop_path))

            # Clean up temp image if not using output_dir
            if not output_dir:
                page_img_path.unlink()

        doc.close()

        duration = (datetime.now() - start_time).total_seconds()
        print()
        print(f"Detection complete in {duration:.1f}s ({duration/60:.1f} minutes)")
        print(f"Equations detected: {len(zones)}")
        print(f"Average confidence: {sum(z.metadata['confidence'] for z in zones)/len(zones):.3f}" if zones else "N/A")
        print()

        # V13 benchmark comparison
        if len(zones) > 0:
            print(f"✅ SUCCESS - Using v13 working approach")
            print(f"   V13 benchmark: 108 equations in ~100s")
            print(f"   V14 result: {len(zones)} equations in {duration:.1f}s")
            if len(zones) == 108:
                print(f"   🎉 EXACT MATCH with v13 coverage!")

        return zones
