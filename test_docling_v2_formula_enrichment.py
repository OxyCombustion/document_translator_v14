#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Docling 2.x Formula Enrichment on NVIDIA DGX Spark

This script tests whether Docling 2.61.2's formula enrichment feature works on the
DGX Spark hardware with 128GB unified memory and Blackwell GPU.

Expected Results:
- ✅ CUDA/GPU detected (or CPU fallback)
- ✅ Formula enrichment enabled
- ✅ Equations extracted from PDF
- ✅ LaTeX content available

Author: Claude Code
Date: 2025-11-15
Version: 2.0 (Docling 2.x)
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("="*80)
print("DOCLING 2.X FORMULA ENRICHMENT TEST - NVIDIA DGX SPARK")
print("="*80)
print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Check CUDA availability
print("Checking CUDA/GPU availability...")
try:
    import torch
    cuda_available = torch.cuda.is_available()
    if cuda_available:
        print(f"✅ CUDA available: {torch.cuda.get_device_name(0)}")
        print(f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB")
    else:
        print(f"⚠️  CUDA not available (will use CPU)")
        print(f"   Note: Formula enrichment may be slower on CPU")
except ImportError:
    print("⚠️  PyTorch not available for GPU check")
print()

# Test PDF
pdf_path = Path("test_data/Ch-04_Heat_Transfer.pdf")
if not pdf_path.exists():
    print(f"❌ Test PDF not found: {pdf_path}")
    sys.exit(1)

print(f"✅ PDF found: {pdf_path}")
print()

# Import equation detector v2
print("Importing Docling 2.x equation detector...")
try:
    from detection_v14_P14.src.docling.docling_equation_detector_v2 import DoclingEquationDetector
    print("✅ DoclingEquationDetector v2.0 imported")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print()

# Initialize detector with formula enrichment
print("Initializing equation detector with formula enrichment...")
try:
    detector = DoclingEquationDetector()
    print("✅ Detector initialized")
except Exception as e:
    print(f"❌ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print()

# Run detection
print("Running equation detection with formula enrichment...")
print(f"(This may take 2-4 minutes with GPU, longer on CPU)")
print()

try:
    start_time = datetime.now()
    zones = detector.detect_equations(pdf_path)
    duration = (datetime.now() - start_time).total_seconds()

    print()
    print("="*80)
    print("RESULTS")
    print("="*80)
    print(f"Processing time: {duration:.1f}s ({duration/60:.1f} minutes)")
    print(f"Equations detected: {len(zones)}")
    print()

    if len(zones) > 0:
        print(f"✅ Formula enrichment SUCCESS - {len(zones)} equations extracted")
        print()

        # Count equations with LaTeX
        with_latex = sum(1 for z in zones if z.metadata.get('has_latex'))
        print(f"Equations with LaTeX: {with_latex}/{len(zones)} ({100*with_latex/len(zones):.1f}%)")
        print()

        # Show first 5 equations
        print("Sample equations (first 5):")
        for i, zone in enumerate(zones[:5]):
            latex = zone.metadata.get('latex', 'N/A')
            page = zone.page
            bbox = zone.bbox
            print(f"  {i+1}. Page {page}, bbox {bbox}")
            print(f"      LaTeX: {latex[:100]}{'...' if len(latex) > 100 else ''}")
            print()

        # Performance info
        print("Performance:")
        print(f"  Total time: {duration:.1f}s")
        print(f"  Per equation: {duration/len(zones):.2f}s")
        print(f"  Per page: {duration/34:.2f}s (34 pages)")

    else:
        print("⚠️  No equations detected")
        print()
        print("Possible reasons:")
        print("1. Formula enrichment may not have detected equations in this PDF")
        print("2. Docling 2.x API may have changed - check element attributes")
        print("3. GPU/memory issues preventing enrichment")

except Exception as e:
    print(f"❌ Detection failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("="*80)
print("TEST COMPLETE")
print("="*80)
print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
