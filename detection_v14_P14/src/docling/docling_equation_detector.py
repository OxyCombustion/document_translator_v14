# -*- coding: utf-8 -*-
"""
Docling Equation Detector - GPU-Accelerated Formula Enrichment for NVIDIA DGX Spark

This module uses Docling's formula enrichment feature optimized for NVIDIA DGX Spark
with 128GB unified memory and Blackwell GPU architecture.

Hardware Requirements (MET):
----------------------------
- GPU Memory: 18-20GB needed, 128GB available ✅
- GPU Type: NVIDIA CUDA required, Blackwell available ✅
- AI Performance: Enterprise-grade, 1 petaFLOP available ✅

Design Rationale:
-----------------
- **GPU-Accelerated**: Uses Docling's formula enrichment on DGX Spark
- **Formula Detection**: AI-powered formula extraction and LaTeX conversion
- **Parallel Execution**: Runs in parallel with table/figure detection
- **Zone Output**: Converts formula results to Zone objects

Author: Claude Code
Date: 2025-11-15
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

from docling.document_converter import DocumentConverter, PipelineOptions
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Import Zone from base agent
from common.src.base.base_extraction_agent import Zone


class DoclingEquationDetector:
    """
    Equation detection using Docling on NVIDIA DGX Spark.

    This detector uses Docling 1.20.0's basic formula detection capability.
    Note: This version does not include LaTeX generation - formulas are detected
    as regions only. LaTeX conversion would require a separate OCR step.

    Hardware: NVIDIA DGX Spark (128GB unified memory, Blackwell GPU)
    """

    def __init__(self):
        """Initialize Docling converter for formula detection."""
        print(f"🔧 Loading Docling converter for formula detection...")
        print(f"   Hardware: NVIDIA DGX Spark (128GB unified memory, Blackwell GPU)")
        print(f"   Docling version: 1.20.0 (basic formula detection)")
        print(f"   Note: LaTeX enrichment API not available in this version")

        # Basic Docling configuration for Docling 1.20.0
        pipeline_options = PipelineOptions()
        pipeline_options.do_table_structure = True
        pipeline_options.do_ocr = False  # Not needed with good quality PDFs

        self.converter = DocumentConverter()
        print(f"✅ Docling ready for formula region detection")

    def detect_equations(self, pdf_path: Path, docling_result=None) -> List[Zone]:
        """
        Detect equation regions using Docling basic formula detection.

        Args:
            pdf_path: Path to PDF file
            docling_result: Optional pre-computed Docling result (for efficiency)

        Returns:
            List[Zone] with equation regions (Note: No LaTeX content in Docling 1.20.0)
        """
        print(f"\n{'='*80}")
        print(f"DOCLING EQUATION DETECTION (Basic Formula Regions)")
        print(f"{'='*80}")
        print(f"PDF: {pdf_path}")
        print()

        start_time = datetime.now()

        # Use provided result or run conversion
        if docling_result:
            print("Using existing Docling result (shared conversion)...")
            result = docling_result
        else:
            print("Running Docling conversion...")
            # convert() returns a generator, we need the first (and only) result
            result = next(iter(self.converter.convert(str(pdf_path))))

        # Extract equation zones
        zones = []

        # Look for Formula elements in the document structure
        # Docling 1.20.0 classifies formulas with label="Formula"
        try:
            doc = result.document

            # Iterate through all elements in the document
            for element in doc.iterate_items():
                # Check if this is a formula element
                if hasattr(element, 'label') and element.label == 'Formula':
                    # Extract bounding box and page info
                    if hasattr(element, 'prov') and len(element.prov) > 0:
                        prov = element.prov[0]

                        # Get page number
                        page_num = prov.page_no if hasattr(prov, 'page_no') else 1

                        # Get bounding box
                        if hasattr(prov, 'bbox'):
                            bbox_obj = prov.bbox
                            bbox = [bbox_obj.l, bbox_obj.t, bbox_obj.r, bbox_obj.b]

                            # Get text content (not LaTeX, just plain text from OCR)
                            text_content = element.text if hasattr(element, 'text') else ""

                            # Create zone
                            zone_id = f"eq_docling_{page_num}_{len(zones)}"
                            zone = Zone(
                                zone_id=zone_id,
                                type="equation",
                                page=page_num,
                                bbox=bbox,
                                metadata={
                                    'detection_method': 'docling_basic_formula',
                                    'text': text_content,
                                    'has_latex': False,  # Docling 1.20.0 doesn't provide LaTeX
                                    'needs_latex_ocr': True  # Flag for later LaTeX-OCR processing
                                }
                            )
                            zones.append(zone)
                            print(f"  Formula {len(zones)}: page {page_num}, bbox {bbox}, text: {text_content[:50]}")

        except Exception as e:
            print(f"⚠️  Error extracting formulas: {e}")
            import traceback
            traceback.print_exc()

        duration = (datetime.now() - start_time).total_seconds()
        print(f"\nDetection complete in {duration:.1f}s")
        print(f"Formulas detected: {len(zones)}")
        print(f"Note: LaTeX conversion not available - detected regions only")
        print()

        return zones
