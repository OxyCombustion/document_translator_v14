#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Table Test Using 4-Page Subset (pages 2, 7, 8, 32)

Tests table markdown fix on subset PDF for faster validation.

Author: Claude
Date: 2025-11-16
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# UTF-8 setup
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

print("=" * 80)
print("TABLE MARKDOWN FIX - SUBSET TEST (4 pages)")
print("=" * 80)
print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Configuration
PDF_PATH = Path("test_data/Ch-04_Heat_Transfer_subset.pdf")
MODEL_PATH = Path("/home/thermodynamics/document_translator_v12/models/models/Layout/YOLO/doclayout_yolo_docstructbench_imgsz1280_2501.pt")
OUTPUT_DIR = Path("test_output_subset")

# Verify files exist
print("Checking prerequisites...")
if not PDF_PATH.exists():
    print(f"❌ PDF not found: {PDF_PATH}")
    sys.exit(1)
print(f"✅ PDF found: {PDF_PATH} (4 pages: 2, 7, 8, 32)")

if not MODEL_PATH.exists():
    print(f"❌ Model not found: {MODEL_PATH}")
    sys.exit(1)
print(f"✅ Model found: {MODEL_PATH}")

# Import the orchestrator
print("\nImporting UnifiedPipelineOrchestrator...")
try:
    from pipelines.rag_ingestion.packages.rag_v14_P2.src.orchestrators.unified_pipeline_orchestrator import UnifiedPipelineOrchestrator
    print("✅ UnifiedPipelineOrchestrator imported")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Initialize orchestrator
print("\nInitializing orchestrator...")
try:
    orchestrator = UnifiedPipelineOrchestrator(
        model_path=str(MODEL_PATH),
        output_dir=OUTPUT_DIR,
        clean_before_run=True
    )
    print("✅ Orchestrator initialized")
except Exception as e:
    print(f"❌ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Run extraction
print("\nRunning extraction on 4-page subset...")
print("This will test table extraction on pages with known tables")
print()

try:
    start_time = datetime.now()

    results = orchestrator.process_document(
        pdf_path=PDF_PATH,
        num_workers=4  # Reduced workers for smaller PDF
    )

    duration = (datetime.now() - start_time).total_seconds()

    print("\n" + "=" * 80)
    print("SUBSET TEST COMPLETE")
    print("=" * 80)
    print(f"Duration: {duration:.1f}s")
    print()

    # Summary
    if 'tables' in results:
        tables = results['tables']
        print(f"✅ Tables extracted: {tables.get('extracted', 0)}/{tables.get('detected', 0)}")
        success_rate = tables.get('success_rate', 0) * 100
        print(f"   Success rate: {success_rate:.1f}%")

        if success_rate > 0:
            print("\n✅ TABLE MARKDOWN FIX WORKING - Tables extracted successfully!")
        else:
            print("\n❌ TABLE MARKDOWN FIX FAILED - No tables extracted")

    print(f"\n📁 Output directory: {OUTPUT_DIR}")
    print(f"   Check: {OUTPUT_DIR}/tables/ for extracted tables")

except Exception as e:
    print(f"\n❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
