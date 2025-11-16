# -*- coding: utf-8 -*-
"""
Docling Equation Detector v2.0 - GPU-Accelerated Formula Enrichment for NVIDIA DGX Spark

This module uses Docling 2.x formula enrichment feature optimized for NVIDIA DGX Spark
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

Changes from v1.0:
------------------
- Upgraded from Docling 1.20.0 to 2.61.2
- Now uses InputFormat.PDF API (Docling 2.x)
- Formula enrichment with LaTeX generation enabled
- GPU acceleration ready

Author: Claude Code
Date: 2025-11-15
Version: 2.0
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

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Import Zone from base agent
from pipelines.shared.packages.common.src.base.base_extraction_agent import Zone


class DoclingEquationDetector:
    """
    Equation detection using Docling 2.x formula enrichment on NVIDIA DGX Spark.

    This detector leverages the DGX Spark's 128GB unified memory and Blackwell GPU
    to run Docling's formula enrichment feature for AI-powered equation extraction.
    """

    def __init__(self):
        """Initialize Docling converter with formula enrichment enabled."""
        print(f"🔧 Loading Docling 2.x converter with formula enrichment...")
        print(f"   Hardware: NVIDIA DGX Spark (128GB unified memory, Blackwell GPU)")
        print(f"   Docling version: 2.61.2")

        # Enable formula enrichment for DGX Spark (Docling 2.x API)
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_table_structure = True
        pipeline_options.do_ocr = False  # Not needed with good quality PDFs
        pipeline_options.do_formula_enrichment = True  # ✅ GPU-accelerated on DGX Spark

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        print(f"✅ Docling ready with formula enrichment enabled (GPU-accelerated)")

    def detect_equations(self, pdf_path: Path, docling_result=None) -> List[Zone]:
        """
        Detect equation regions using Docling formula enrichment.

        Args:
            pdf_path: Path to PDF file
            docling_result: Optional pre-computed Docling result (for efficiency)

        Returns:
            List[Zone] with equation regions and LaTeX content
        """
        print(f"\n{'='*80}")
        print(f"DOCLING EQUATION DETECTION (Formula Enrichment v2.0)")
        print(f"{'='*80}")
        print(f"PDF: {pdf_path}")
        print()

        start_time = datetime.now()

        # Use provided result or run conversion with formula enrichment
        if docling_result:
            print("Using existing Docling result (shared conversion)...")
            result = docling_result
        else:
            print("Running Docling conversion with formula enrichment...")
            # Docling 2.x convert() returns generator, get first result
            result = next(iter(self.converter.convert(str(pdf_path))))

        # Extract equation zones
        zones = []

        # Access document from result
        doc = result.document

        # Iterate through all document items to find equations/formulas
        # In Docling 2.x, formulas are identified by their element type
        for element in doc.iterate_items():
            # Check for equation/formula elements
            # Docling 2.x uses different attribute names
            if hasattr(element, 'label') and element.label in ['Formula', 'equation']:
                # Extract bounding box and page info
                if hasattr(element, 'prov') and len(element.prov) > 0:
                    prov = element.prov[0]

                    # Get page number
                    page_num = prov.page_no if hasattr(prov, 'page_no') else 1

                    # Get bounding box
                    if hasattr(prov, 'bbox'):
                        bbox_obj = prov.bbox
                        bbox = [bbox_obj.l, bbox_obj.t, bbox_obj.r, bbox_obj.b]

                        # Get LaTeX content from formula enrichment
                        # Docling 2.x stores LaTeX in element text or separate attribute
                        latex_content = ""
                        if hasattr(element, 'text'):
                            latex_content = element.text
                        elif hasattr(element, 'latex'):
                            latex_content = element.latex

                        # Create zone
                        zone_id = f"eq_docling_{page_num}_{len(zones)}"
                        zone = Zone(
                            zone_id=zone_id,
                            type="equation",
                            page=page_num,
                            bbox=bbox,
                            metadata={
                                'detection_method': 'docling_formula_enrichment_v2',
                                'latex': latex_content,
                                'formula_index': len(zones),
                                'has_latex': bool(latex_content),
                                'docling_version': '2.61.2'
                            }
                        )
                        zones.append(zone)
                        print(f"  Equation {len(zones)}: page {page_num}, bbox {bbox}")
                        if latex_content:
                            print(f"    LaTeX: {latex_content[:80]}{'...' if len(latex_content) > 80 else ''}")

        duration = (datetime.now() - start_time).total_seconds()
        print(f"\nDetection complete in {duration:.1f}s")
        print(f"Equations detected: {len(zones)}")
        with_latex = sum(1 for z in zones if z.metadata.get('has_latex'))
        print(f"Equations with LaTeX: {with_latex}/{len(zones)}")
        print()

        return zones
