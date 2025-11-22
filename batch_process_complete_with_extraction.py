#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete Batch Processing with FULL Extraction Output Preservation

IMPORTANT: This script preserves ALL extraction outputs including:
- Equations (images + metadata)
- Tables (CSV, Excel, images + metadata)
- Figures (images + metadata)
- Text content
- Bibliography
- Completeness reports

Storage is NOT optimized - we keep everything for future reference.

Author: Claude Code
Date: 2025-11-21
"""

import sys
import os
import json
import time
import csv
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# UTF-8 setup
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

# ============================================================================
# Configuration
# ============================================================================

ZOTERO_BASE = Path.home() / "windows_zotero" / "storage"
TEST_DATA_DIR = Path("test_data")
BATCH_RESULTS_DIR = Path("batch_results")
MODEL_PATH = Path("weights/doclayout_yolo_docstructbench_imgsz1024.pt")

# Batch 1 - MICRO (smallest chapters)
BATCH_1_CHAPTERS = [
    ("Ch-53", "Nuclear_Waste_Management", "UNMJIZT3"),
    ("Ch-44", "Boiler_Operations", "CZ5R6KY4"),
    ("Ch-48", "Nuclear_Fuels", "62IBFRKL"),
    ("Ch-49", "Principles_of_Nuclear_Reactions", "B3STPXVQ"),
    ("Ch-08", "Structural", "8ZZ2YGRA"),
    ("Ch-11", "Oil_and_Gas", "6LVFMQNR"),
    ("Ch-46", "Condition_Assessment", "8LL8VREJ"),
    ("Ch-18", "Coal_Gasification", "VTT7N5JX"),
    ("Ch-52", "Nuclear_Services_Life_Ext", "W3E58GFD"),
    ("Ch-30", "Biomass", "QKSVHECM"),
]

# Results tracking
all_metrics = []

# ============================================================================
# Phase 1: Extraction with FULL Output Preservation
# ============================================================================

def run_extraction_full(chapter_id: str, pdf_path: Path) -> tuple[bool, float, Dict[str, int]]:
    """
    Run extraction pipeline with FULL structured output preservation.

    Saves:
    - All equation images
    - All table images, CSV, Excel files
    - All figure images
    - All metadata JSON files
    - Bibliography
    - Completeness reports
    """
    output_dir = BATCH_RESULTS_DIR / chapter_id / "extraction"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  PHASE 1: EXTRACTION (FULL OUTPUT PRESERVATION)")
    print(f"  Output: {output_dir}")

    start_time = time.time()

    try:
        from pipelines.extraction.packages.extraction_v14_P1.src.orchestrators.unified_pipeline_orchestrator import UnifiedPipelineOrchestrator

        orchestrator = UnifiedPipelineOrchestrator(
            model_path=str(MODEL_PATH),
            output_dir=output_dir,
            clean_before_run=True,
            enable_structured_output=True  # CRITICAL: Enables hierarchical output
        )

        results = orchestrator.process_document(
            pdf_path=pdf_path,
            num_workers=8
        )

        duration = time.time() - start_time

        # Count extracted objects
        counts = {
            'equations': len(list(output_dir.glob("equations/*.png"))),
            'tables': len(list(output_dir.glob("tables/*.png"))),
            'figures': len(list(output_dir.glob("*.png"))) if (output_dir / "figures").exists() else 0,
        }

        print(f"  ✓ Extraction complete in {duration:.1f}s")
        print(f"    - Equations: {counts['equations']}")
        print(f"    - Tables: {counts['tables']}")
        print(f"    - Figures: {counts['figures']}")

        return True, duration, counts

    except Exception as e:
        duration = time.time() - start_time
        print(f"  ✗ Extraction FAILED after {duration:.1f}s: {e}")
        return False, duration, {}

# ============================================================================
# Phase 2: RAG Ingestion
# ============================================================================

def run_rag_ingestion(chapter_id: str, pdf_path: Path) -> tuple[bool, float, int]:
    """Run RAG ingestion pipeline."""
    output_dir = BATCH_RESULTS_DIR / chapter_id / "rag"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  PHASE 2: RAG INGESTION")
    print(f"  Output: {output_dir}")

    start_time = time.time()
    chunks_created = 0

    try:
        from pipelines.rag_ingestion.packages.semantic_processing_v14_P4.src.chunking.semantic_structure_detector import SemanticStructureDetector
        from pipelines.rag_ingestion.packages.semantic_processing_v14_P4.src.chunking.hierarchical_processing_planner import HierarchicalProcessingPlanner
        from pipelines.rag_ingestion.packages.semantic_processing_v14_P4.src.chunking.semantic_hierarchical_processor import SemanticHierarchicalProcessor

        detector = SemanticStructureDetector()
        structure = detector.detect(pdf_path)

        planner = HierarchicalProcessingPlanner()
        plan = planner.create_plan(structure, {})

        processor = SemanticHierarchicalProcessor()
        results = processor.process(plan, {}, pdf_path)

        duration = time.time() - start_time

        # Convert to JSONL
        chunk_files = sorted(output_dir.glob("*/chunks.json"))
        all_chunks = []

        for chunk_file in chunk_files:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
                all_chunks.extend(chunks)

        chunks_created = len(all_chunks)

        # Write JSONL
        jsonl_file = output_dir / "rag_bundles.jsonl"
        with open(jsonl_file, 'w', encoding='utf-8') as f:
            for chunk in all_chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

        # Create citation graph stub
        citation_graph = {
            "document_name": chapter_id,
            "citation_stats": {
                "total_citations": 0,
                "by_type": {"figure": 0, "table": 0, "equation": 0, "chapter": 0, "reference": 0}
            },
            "citations_by_chunk": {}
        }

        graph_file = output_dir / "citation_graph.json"
        with open(graph_file, 'w', encoding='utf-8') as f:
            json.dump(citation_graph, f, indent=2)

        print(f"  ✓ RAG complete in {duration:.1f}s ({chunks_created} chunks)")

        return True, duration, chunks_created

    except Exception as e:
        duration = time.time() - start_time
        print(f"  ✗ RAG FAILED after {duration:.1f}s: {e}")
        return False, duration, 0

# ============================================================================
# Phase 3: Database Ingestion
# ============================================================================

def run_database_ingestion(chapter_id: str, title: str) -> tuple[bool, float, float]:
    """Run ChromaDB ingestion."""
    rag_dir = BATCH_RESULTS_DIR / chapter_id / "rag"
    db_dir = BATCH_RESULTS_DIR / chapter_id / "database" / "chromadb"
    db_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  PHASE 3: DATABASE INGESTION")
    print(f"  Database: {db_dir}")

    start_time = time.time()

    try:
        # Initialize ChromaDB
        client = chromadb.PersistentClient(
            path=str(db_dir),
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )

        collection_name = f"{chapter_id.lower()}_{title.lower().replace(' ', '_')}"

        try:
            client.delete_collection(name=collection_name)
        except:
            pass

        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        collection = client.create_collection(
            name=collection_name,
            embedding_function=embedding_fn
        )

        # Load chunks
        jsonl_file = rag_dir / "rag_bundles.jsonl"
        chunks = []
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                chunks.append(json.loads(line))

        # Insert
        ids = [c['chunk_id'] for c in chunks]
        documents = [c['text'] for c in chunks]
        metadatas = [{'chunk_id': c['chunk_id'], 'page_number': str(c['page_number'])} for c in chunks]

        collection.add(ids=ids, documents=documents, metadatas=metadatas)

        duration = time.time() - start_time

        # Get DB size
        db_size = sum(f.stat().st_size for f in db_dir.rglob('*') if f.is_file())
        db_size_mb = db_size / 1024 / 1024

        print(f"  ✓ Database complete in {duration:.1f}s ({db_size_mb:.2f} MB)")

        return True, duration, db_size_mb

    except Exception as e:
        duration = time.time() - start_time
        print(f"  ✗ Database FAILED after {duration:.1f}s: {e}")
        return False, duration, 0.0

# ============================================================================
# Main Processing Loop
# ============================================================================

def process_chapter(chapter_id: str, title: str, zotero_hash: str) -> Dict[str, Any]:
    """Process single chapter through all 3 phases."""
    print(f"\n{'='*80}")
    print(f"PROCESSING: {chapter_id} - {title.replace('_', ' ')}")
    print(f"{'='*80}")

    # Find PDF
    pdf_candidates = list(ZOTERO_BASE.glob(f"{zotero_hash}/*{chapter_id}*.pdf"))
    if not pdf_candidates:
        print(f"✗ PDF not found in {ZOTERO_BASE}/{zotero_hash}/")
        return None

    pdf_path = pdf_candidates[0]
    pdf_size_mb = pdf_path.stat().st_size / 1024 / 1024

    print(f"PDF: {pdf_path.name} ({pdf_size_mb:.2f} MB)")

    # Phase 1: Extraction (FULL preservation)
    extract_success, extract_time, extract_counts = run_extraction_full(chapter_id, pdf_path)
    if not extract_success:
        return {"chapter": chapter_id, "status": "FAILED_EXTRACTION"}

    # Phase 2: RAG
    rag_success, rag_time, chunks_created = run_rag_ingestion(chapter_id, pdf_path)
    if not rag_success:
        return {"chapter": chapter_id, "status": "FAILED_RAG"}

    # Phase 3: Database
    db_success, db_time, db_size_mb = run_database_ingestion(chapter_id, title)
    if not db_success:
        return {"chapter": chapter_id, "status": "FAILED_DATABASE"}

    total_time = extract_time + rag_time + db_time

    print(f"\n{'='*80}")
    print(f"✓ COMPLETE: {chapter_id} in {total_time:.1f}s")
    print(f"{'='*80}")

    return {
        "chapter": chapter_id,
        "pdf_size_mb": round(pdf_size_mb, 2),
        "extraction_s": round(extract_time, 1),
        "rag_s": round(rag_time, 1),
        "database_s": round(db_time, 1),
        "total_s": round(total_time, 1),
        "equations": extract_counts.get('equations', 0),
        "tables": extract_counts.get('tables', 0),
        "figures": extract_counts.get('figures', 0),
        "chunks_created": chunks_created,
        "db_size_mb": round(db_size_mb, 2),
        "status": "SUCCESS"
    }

# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    print(f"\n{'#'*80}")
    print("# BATCH PROCESSING WITH FULL EXTRACTION OUTPUT PRESERVATION")
    print(f"# Batch 1 (MICRO): {len(BATCH_1_CHAPTERS)} chapters")
    print(f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*80}\n")

    TEST_DATA_DIR.mkdir(exist_ok=True)
    BATCH_RESULTS_DIR.mkdir(exist_ok=True)

    start_time_total = time.time()

    for chapter_id, title, zotero_hash in BATCH_1_CHAPTERS:
        metrics = process_chapter(chapter_id, title, zotero_hash)
        if metrics:
            all_metrics.append(metrics)

    total_duration = time.time() - start_time_total

    # ========================================================================
    # Save Results
    # ========================================================================

    # CSV
    csv_file = BATCH_RESULTS_DIR / "batch_1_full_extraction_metrics.csv"
    if all_metrics:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_metrics[0].keys())
            writer.writeheader()
            writer.writerows(all_metrics)

    # JSON Summary
    summary = {
        "batch_name": "Batch 1 - MICRO (Full Extraction)",
        "total_chapters": len(BATCH_1_CHAPTERS),
        "successful": len([m for m in all_metrics if m['status'] == 'SUCCESS']),
        "failed": len([m for m in all_metrics if m['status'] != 'SUCCESS']),
        "total_time_seconds": round(total_duration, 1),
        "total_equations": sum(m.get('equations', 0) for m in all_metrics),
        "total_tables": sum(m.get('tables', 0) for m in all_metrics),
        "total_figures": sum(m.get('figures', 0) for m in all_metrics),
        "total_chunks": sum(m.get('chunks_created', 0) for m in all_metrics),
        "total_db_size_mb": round(sum(m.get('db_size_mb', 0) for m in all_metrics), 2),
        "completed_at": datetime.now().isoformat()
    }

    json_file = BATCH_RESULTS_DIR / "batch_1_full_extraction_summary.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    # ========================================================================
    # Final Report
    # ========================================================================

    print(f"\n{'#'*80}")
    print("# BATCH 1 PROCESSING COMPLETE (FULL EXTRACTION)")
    print(f"{'#'*80}\n")
    print(f"Total Chapters: {len(BATCH_1_CHAPTERS)}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Total Time: {total_duration:.1f}s ({total_duration/60:.1f} min)")
    print(f"\nExtraction Outputs Preserved:")
    print(f"  - Equations: {summary['total_equations']}")
    print(f"  - Tables: {summary['total_tables']}")
    print(f"  - Figures: {summary['total_figures']}")
    print(f"  - Semantic Chunks: {summary['total_chunks']}")
    print(f"  - Database Size: {summary['total_db_size_mb']} MB")
    print(f"\nResults saved:")
    print(f"  - {csv_file}")
    print(f"  - {json_file}")
    print(f"\nAll extraction outputs preserved in:")
    print(f"  - {BATCH_RESULTS_DIR}/Ch-*/extraction/")
    print(f"    ├── equations/  (all equation images)")
    print(f"    ├── tables/     (CSV, Excel, images)")
    print(f"    ├── figures/    (all figure images)")
    print(f"    └── *.json      (metadata, bibliography, reports)")
