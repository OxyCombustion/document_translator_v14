#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG Pipeline Test - Chapter 4
Tests semantic chunking and JSONL generation for RAG ingestion.

Author: Claude Code
Date: 2025-11-19
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
print("RAG PIPELINE TEST - Chapter 4 Heat Transfer")
print("=" * 80)
print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Configuration
PDF_PATH = Path("test_data/Ch-04_Heat_Transfer.pdf")
OUTPUT_DIR = Path("test_output_rag")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Verify PDF exists
print("Checking prerequisites...")
if not PDF_PATH.exists():
    print(f"❌ PDF not found: {PDF_PATH}")
    sys.exit(1)
print(f"✅ PDF found: {PDF_PATH}")
print()

# Import RAG components
print("Importing RAG pipeline components...")
try:
    from pipelines.rag_ingestion.packages.semantic_processing_v14_P4.src.chunking.semantic_structure_detector import SemanticStructureDetector
    from pipelines.rag_ingestion.packages.semantic_processing_v14_P4.src.chunking.hierarchical_processing_planner import HierarchicalProcessingPlanner
    from pipelines.rag_ingestion.packages.semantic_processing_v14_P4.src.chunking.semantic_hierarchical_processor import SemanticHierarchicalProcessor
    print("✅ RAG components imported successfully")
except Exception as e:
    print(f"❌ Failed to import RAG components: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 80)
print("PHASE 1: SEMANTIC STRUCTURE DETECTION")
print("=" * 80)
print()

# Step 1: Detect semantic structure
print("Detecting semantic structure...")
try:
    config_path = Path("pipelines/rag_ingestion/config/semantic_chunking.yaml")
    if not config_path.exists():
        print(f"⚠️  Config not found: {config_path}, using defaults")
        config_path = None

    detector = SemanticStructureDetector(config_path)
    structure = detector.detect(PDF_PATH)

    print(f"✅ Structure detected:")
    print(f"   Sections: {len(structure.sections)}")
    print(f"   Total pages: {structure.total_pages}")
    print(f"   Source: {structure.document_path}")
    print()

except Exception as e:
    print(f"❌ Structure detection failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 80)
print("PHASE 2: PROCESSING PLAN CREATION")
print("=" * 80)
print()

# Step 2: Create processing plan
print("Creating hierarchical processing plan...")
try:
    planner = HierarchicalProcessingPlanner(config_path)
    plan = planner.create_plan(structure, OUTPUT_DIR)

    print(f"✅ Processing plan created:")
    print(f"   Processing units: {len(plan.processing_units)}")
    print(f"   Output directory: {OUTPUT_DIR}")
    print()

except Exception as e:
    print(f"❌ Plan creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 80)
print("PHASE 3: SEMANTIC PROCESSING & CHUNKING")
print("=" * 80)
print()

# Step 3: Execute semantic processing
print("Executing semantic hierarchical processing...")
print("This will:")
print("  1. Extract text from PDF")
print("  2. Create semantic chunks")
print("  3. Generate JSONL for vector database")
print("  4. Build cross-reference metadata")
print()

try:
    start_time = datetime.now()

    processor = SemanticHierarchicalProcessor(planner.config)
    result = processor.process_plan(plan, PDF_PATH)

    duration = (datetime.now() - start_time).total_seconds()

    print()
    print("=" * 80)
    print("PROCESSING COMPLETE")
    print("=" * 80)
    print(f"Duration: {duration:.1f}s")
    print()

    # Display results
    stats = result.get('statistics', {})
    print("Processing Results:")
    print(f"  Chunks created: {stats.get('total_chunks', 0)}")
    print(f"  Total characters: {stats.get('total_chars', 0):,}")
    print(f"  Avg chars/chunk: {stats.get('avg_chars_per_chunk', 0):.0f}")
    print()

    # List output files
    print("Output files:")
    if OUTPUT_DIR.exists():
        jsonl_files = list(OUTPUT_DIR.glob('**/*.jsonl'))
        json_files = list(OUTPUT_DIR.glob('**/*.json'))
        print(f"  JSONL files: {len(jsonl_files)}")
        print(f"  JSON metadata files: {len(json_files)}")

        if jsonl_files:
            print()
            print("  JSONL outputs:")
            for f in jsonl_files[:5]:
                size_kb = f.stat().st_size / 1024
                print(f"    - {f.relative_to(OUTPUT_DIR)} ({size_kb:.1f} KB)")

    print()
    print("✅ RAG PIPELINE TEST SUCCESSFUL")

except Exception as e:
    print(f"\n❌ Processing failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 80)
print("Test completed successfully!")
print("=" * 80)
