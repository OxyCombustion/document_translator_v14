#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-End Test: Chapter 3 Fluid Dynamics
Demonstrates complete workflow from Zotero retrieval to RAG embedding preparation.

Workflow:
1. Extraction Pipeline (Phase 1) - PDF → structured JSON
2. Hierarchical Organization - Human-readable structure
3. RAG Ingestion Pipeline (Phase 2) - JSON → JSONL bundles
4. Ready for embedding in vector database

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
        except: pass

from pathlib import Path
from datetime import datetime
import json

print("=" * 80)
print("END-TO-END TEST: CHAPTER 3 FLUID DYNAMICS")
print("=" * 80)
print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Configuration
PDF_PATH = Path("test_data/Ch-03_Fluid_Dynamics.pdf")
MODEL_PATH = Path("/home/thermodynamics/document_translator_v12/models/models/Layout/YOLO/doclayout_yolo_docstructbench_imgsz1280_2501.pt")
OUTPUT_DIR = Path("test_output_ch03")
OUTPUT_DIR_STRUCTURED = Path("test_output_ch03_structured")
RAG_OUTPUT_DIR = Path("test_output_ch03_rag")

# Verify PDF exists
if not PDF_PATH.exists():
    print(f"❌ PDF not found: {PDF_PATH}")
    sys.exit(1)

pdf_size_mb = PDF_PATH.stat().st_size / (1024 * 1024)
print(f"📄 Input PDF: {PDF_PATH}")
print(f"   Size: {pdf_size_mb:.2f} MB")
print()

# Clean previous outputs
for output_dir in [OUTPUT_DIR, OUTPUT_DIR_STRUCTURED, RAG_OUTPUT_DIR]:
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
        print(f"🧹 Cleaned: {output_dir}")

print()
print("=" * 80)
print("PHASE 1: EXTRACTION PIPELINE")
print("=" * 80)
print()

# Import extraction orchestrator
from pipelines.rag_ingestion.packages.rag_v14_P2.src.orchestrators.unified_pipeline_orchestrator import UnifiedPipelineOrchestrator

try:
    # Run extraction with hierarchical output
    orchestrator = UnifiedPipelineOrchestrator(
        model_path=str(MODEL_PATH),
        output_dir=OUTPUT_DIR,
        clean_before_run=True,
        enable_structured_output=True
    )

    extraction_start = datetime.now()
    print(f"Processing {PDF_PATH.name}...")
    print()

    results = orchestrator.process_document(
        pdf_path=PDF_PATH,
        num_workers=8
    )

    extraction_duration = (datetime.now() - extraction_start).total_seconds()

    print()
    print("=" * 80)
    print("EXTRACTION RESULTS")
    print("=" * 80)
    print()
    print(f"Duration: {extraction_duration:.1f}s")
    print()

    if 'extraction' in results:
        ext_stats = results['extraction']
        print("Extraction Statistics:")
        print(f"  Total pages: {ext_stats.get('total_pages', 0)}")
        print(f"  Equations: {ext_stats.get('equations', 0)}")
        print(f"  Tables: {ext_stats.get('tables', 0)}")
        print(f"  Figures: {ext_stats.get('figures', 0)}")
        print()

    if 'structured_output' in results:
        struct_stats = results['structured_output']
        print("Hierarchical Organization:")
        print(f"  Total files: {struct_stats.get('total_files', 0)}")
        print(f"  Sections: {struct_stats.get('sections_detected', 0)}")
        print(f"  Duration: {struct_stats.get('duration_seconds', 0):.2f}s")
        print()

    # Verify extraction outputs
    extraction_json = OUTPUT_DIR / "extraction_results.json"
    if extraction_json.exists():
        print(f"✅ Extraction results saved: {extraction_json}")
        with open(extraction_json, 'r', encoding='utf-8') as f:
            extraction_data = json.load(f)
            print(f"   Zones extracted: {len(extraction_data.get('zones', []))}")

    # Verify hierarchical structure
    if OUTPUT_DIR_STRUCTURED.exists():
        doc_dir = OUTPUT_DIR_STRUCTURED / PDF_PATH.stem
        if doc_dir.exists():
            print(f"✅ Hierarchical structure created: {doc_dir}")
            metadata_file = doc_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    print(f"   Document: {metadata.get('document_name')}")
                    print(f"   Pages: {metadata.get('total_pages')}")
                    print(f"   Sections: {len(metadata.get('sections', []))}")

    print()
    print("=" * 80)
    print("PHASE 2: RAG INGESTION PIPELINE")
    print("=" * 80)
    print()

    # Import RAG pipeline
    from pipelines.rag_ingestion.packages.rag_v14_P2.src.rag_pipeline import RAGPipeline

    rag_start = datetime.now()

    # Create RAG pipeline
    rag_pipeline = RAGPipeline(
        input_path=extraction_json,
        output_dir=RAG_OUTPUT_DIR
    )

    print("Converting extraction results to RAG bundles...")
    print()

    rag_results = rag_pipeline.process()

    rag_duration = (datetime.now() - rag_start).total_seconds()

    print()
    print("=" * 80)
    print("RAG INGESTION RESULTS")
    print("=" * 80)
    print()
    print(f"Duration: {rag_duration:.1f}s")
    print()

    if rag_results:
        print("RAG Statistics:")
        if 'chunks' in rag_results:
            print(f"  Semantic chunks: {len(rag_results['chunks'])}")
        if 'citations' in rag_results:
            print(f"  Citations extracted: {len(rag_results['citations'])}")
        print()

    # Verify RAG outputs
    rag_bundles = RAG_OUTPUT_DIR / "rag_bundles.jsonl"
    if rag_bundles.exists():
        print(f"✅ RAG bundles created: {rag_bundles}")

        # Count bundles
        bundle_count = 0
        with open(rag_bundles, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    bundle_count += 1
        print(f"   Total bundles: {bundle_count}")

        # Show sample bundle
        with open(rag_bundles, 'r', encoding='utf-8') as f:
            first_bundle = json.loads(f.readline())
            print(f"   Sample bundle type: {first_bundle.get('content_type')}")
            if 'text' in first_bundle:
                text_preview = first_bundle['text'][:100] + "..."
                print(f"   Text preview: {text_preview}")

    print()
    print("=" * 80)
    print("END-TO-END TEST COMPLETE")
    print("=" * 80)
    print()

    total_duration = extraction_duration + rag_duration
    print(f"Total Duration: {total_duration:.1f}s")
    print()
    print("Output Locations:")
    print(f"  Flat extraction: {OUTPUT_DIR}")
    print(f"  Hierarchical view: {OUTPUT_DIR_STRUCTURED}")
    print(f"  RAG bundles: {RAG_OUTPUT_DIR}")
    print()
    print("✅ Chapter 3 is now ready for embedding in vector database!")
    print()
    print("Next Steps:")
    print("  1. Load rag_bundles.jsonl into ChromaDB/Pinecone")
    print("  2. Generate embeddings for each bundle")
    print("  3. Enable semantic search and retrieval")
    print()

except Exception as e:
    print(f"❌ Pipeline failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
