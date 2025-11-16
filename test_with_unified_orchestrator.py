#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete End-to-End Test Using Existing UnifiedPipelineOrchestrator

Uses the orchestrator that's already in v14 to run complete extraction pipeline.

Author: Claude (using existing v14 orchestrator)
Date: 2025-11-15
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
print("COMPLETE END-TO-END TEST - Using Existing UnifiedPipelineOrchestrator")
print("=" * 80)
print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Configuration
PDF_PATH = Path("test_data/Ch-04_Heat_Transfer.pdf")
MODEL_PATH = Path("/home/thermodynamics/document_translator_v12/models/models/Layout/YOLO/doclayout_yolo_docstructbench_imgsz1280_2501.pt")
OUTPUT_DIR = Path("test_output_orchestrator")

# Verify files exist
print("Checking prerequisites...")
if not PDF_PATH.exists():
    print(f"❌ PDF not found: {PDF_PATH}")
    sys.exit(1)
print(f"✅ PDF found: {PDF_PATH}")

if not MODEL_PATH.exists():
    print(f"❌ Model not found: {MODEL_PATH}")
    sys.exit(1)
print(f"✅ Model found: {MODEL_PATH}")

# Import the orchestrator
print("\nImporting UnifiedPipelineOrchestrator...")
try:
    from rag_v14_P2.src.orchestrators.unified_pipeline_orchestrator import UnifiedPipelineOrchestrator
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
print("\nRunning complete extraction pipeline...")
print("This will:")
print("  1. Detect all objects (equations, tables, figures, text)")
print("  2. Extract content using specialized agents")
print("  3. Save organized outputs")
print()

try:
    start_time = datetime.now()

    results = orchestrator.process_document(
        pdf_path=PDF_PATH,
        num_workers=8
    )

    duration = (datetime.now() - start_time).total_seconds()

    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"Duration: {duration:.1f}s")
    print()

    # Display results
    print("Extraction Results:")
    for content_type, items in results.items():
        if isinstance(items, list):
            print(f"  {content_type.capitalize()}: {len(items)} items")
        elif isinstance(items, dict):
            print(f"  {content_type.capitalize()}: {items}")

    print(f"\nOutputs saved to: {OUTPUT_DIR}")

    # List created files
    print("\nCreated files:")
    for subdir in ['equations', 'tables', 'figures', 'text']:
        dir_path = OUTPUT_DIR / subdir
        if dir_path.exists():
            files = list(dir_path.glob('*'))
            print(f"  {subdir}/: {len(files)} files")

    print("\n✅ END-TO-END TEST SUCCESSFUL")

except Exception as e:
    print(f"\n❌ Extraction failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
