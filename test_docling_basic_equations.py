#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Docling Basic Equation Detection on NVIDIA DGX Spark

This script tests Docling 1.20.0's basic formula detection capability.
Note: This version does NOT include LaTeX generation - it only detects
formula regions. LaTeX conversion would require a separate OCR step.

Expected Results:
- ✅ CUDA/GPU detected (if available)
- ✅ Formulas detected as regions
- ⚠️  No LaTeX content (API limitation in Docling 1.20.0)

Author: Claude Code
Date: 2025-11-15
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("="*80)
print("DOCLING BASIC EQUATION DETECTION TEST - NVIDIA DGX SPARK")
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

# Import equation detector
print("Importing Docling equation detector...")
try:
    from detection_v14_P14.src.docling.docling_equation_detector import DoclingEquationDetector
    print("✅ DoclingEquationDetector imported")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)
print()

# Initialize detector
print("Initializing equation detector...")
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
print("Running equation detection...")
print(f"(This may take 2-3 minutes, Docling is processing the full document)")
print()

try:
    start_time = datetime.now()
    zones = detector.detect_equations(pdf_path)
    duration = (datetime.now() - start_time).total_seconds()

    print()
    print("="*80)
    print("RESULTS")
    print("="*80)
    print(f"Processing time: {duration:.1f}s")
    print(f"Formulas detected: {len(zones)}")
    print()

    if len(zones) > 0:
        print(f"✅ Formula detection SUCCESS - {len(zones)} formula regions found")
        print()

        # Show first 5 formulas
        print("Sample formulas (first 5):")
        for i, zone in enumerate(zones[:5]):
            text = zone.metadata.get('text', 'N/A')
            page = zone.page
            bbox = zone.bbox
            print(f"  {i+1}. Page {page}, bbox {bbox}")
            print(f"      Text: {text[:100]}{'...' if len(text) > 100 else ''}")
            print()

        print(f"⚠️  Note: LaTeX conversion not available in Docling 1.20.0")
        print(f"💡 Suggestion: Use pix2tex or LaTeX-OCR for LaTeX conversion from detected regions")

    else:
        print("⚠️  No formulas detected")
        print()
        print("Possible reasons:")
        print("1. Docling may not classify mathematical content as 'Formula' in this PDF")
        print("2. Formula detection may require different document format")
        print("3. Try using YOLO-based detection as alternative")

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
