#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Structured Output Organization

Tests the StructuredOutputManager on existing extraction outputs from Chapter 4.
This creates a hierarchical view for human verification without affecting pipeline compatibility.

Author: Claude Code
Date: 2025-11-20
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

from pathlib import Path
from datetime import datetime
import json

print("=" * 80)
print("STRUCTURED OUTPUT ORGANIZATION TEST")
print("=" * 80)
print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Import StructuredOutputManager
print("Importing StructuredOutputManager...")
try:
    from pipelines.extraction.packages.extraction_v14_P1.src.output.structured_output_manager import StructuredOutputManager
    print("✅ Import successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Configuration
FLAT_OUTPUT_DIR = Path("test_output_orchestrator")
STRUCTURED_OUTPUT_DIR = Path("test_output_orchestrator_structured")
PDF_PATH = Path("test_data/Ch-04_Heat_Transfer.pdf")

# Verify inputs exist
print("Checking prerequisites...")
if not FLAT_OUTPUT_DIR.exists():
    print(f"❌ Flat output directory not found: {FLAT_OUTPUT_DIR}")
    print("   Run test_with_unified_orchestrator.py first to generate outputs")
    sys.exit(1)
print(f"✅ Flat outputs found: {FLAT_OUTPUT_DIR}")

if not PDF_PATH.exists():
    print(f"❌ PDF not found: {PDF_PATH}")
    sys.exit(1)
print(f"✅ PDF found: {PDF_PATH}")

# Count existing files
equations = list((FLAT_OUTPUT_DIR / "equations").glob("*")) if (FLAT_OUTPUT_DIR / "equations").exists() else []
tables = list((FLAT_OUTPUT_DIR / "tables").glob("*")) if (FLAT_OUTPUT_DIR / "tables").exists() else []
print(f"   Equations: {len(equations)} files")
print(f"   Tables: {len(tables)} files")
print()

# Create StructuredOutputManager
print("Initializing StructuredOutputManager...")
try:
    manager = StructuredOutputManager(
        flat_output_dir=FLAT_OUTPUT_DIR,
        structured_output_dir=STRUCTURED_OUTPUT_DIR,
        pdf_path=PDF_PATH,
        enable_structure_detection=True
    )
    print("✅ Manager initialized")
except Exception as e:
    print(f"❌ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Organize outputs
print("Organizing outputs into hierarchical structure...")
print()

try:
    start_time = datetime.now()
    stats = manager.organize_outputs()
    duration = (datetime.now() - start_time).total_seconds()

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print()
    print(f"Duration: {duration:.2f}s")
    print()
    print("Statistics:")
    print(json.dumps(stats, indent=2))
    print()

    # Verify structured output
    print("Verifying structured output...")
    if STRUCTURED_OUTPUT_DIR.exists():
        doc_dir = STRUCTURED_OUTPUT_DIR / PDF_PATH.stem
        if doc_dir.exists():
            print(f"✅ Document directory created: {doc_dir}")

            # Check for metadata
            metadata_file = doc_dir / "metadata.json"
            if metadata_file.exists():
                print(f"✅ Document metadata created")
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    print(f"   Sections: {len(metadata.get('sections', []))}")
            else:
                print(f"⚠️  Document metadata not found")

            # List subdirectories
            subdirs = [d for d in doc_dir.iterdir() if d.is_dir()]
            print(f"   Subdirectories: {len(subdirs)}")
            for subdir in sorted(subdirs)[:5]:  # Show first 5
                print(f"      - {subdir.name}")
            if len(subdirs) > 5:
                print(f"      ... and {len(subdirs) - 5} more")

        else:
            print(f"❌ Document directory not found: {doc_dir}")
    else:
        print(f"❌ Structured output directory not found: {STRUCTURED_OUTPUT_DIR}")

    print()
    print("You can now browse the hierarchical structure at:")
    print(f"  {STRUCTURED_OUTPUT_DIR}")
    print()
    print("To view structure:")
    print(f"  find {STRUCTURED_OUTPUT_DIR} -type d | head -30")
    print()

except Exception as e:
    print(f"❌ Organization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
