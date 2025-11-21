#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete Batch Processing - RAG and Database Phases Only

Since extraction completed successfully for all 10 chapters,
this script processes only the RAG ingestion, JSONL conversion,
and database loading phases.

Author: Claude Code
Date: 2025-11-21
"""

import sys
import os
import json
import time
import csv
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

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

# ============================================================================
# Configuration
# ============================================================================

TEST_DATA_DIR = Path("test_data")
BATCH_OUTPUT_DIR = Path("batch_processing_results")
BATCH_RESULTS_DIR = Path("batch_results")

# Chapters that completed extraction
CHAPTERS = [
    ("Ch-53", "Nuclear Waste Management", 0.4),
    ("Ch-44", "Boiler Operations", 1.0),
    ("Ch-48", "Nuclear Fuels", 1.1),
    ("Ch-49", "Principles of Nuclear Reactions", 1.1),
    ("Ch-08", "Structural", 1.2),
    ("Ch-11", "Oil and Gas", 1.3),
    ("Ch-46", "Condition Assessment", 1.3),
    ("Ch-18", "Coal Gasification", 1.5),
    ("Ch-52", "Nuclear Services Life Ext", 1.6),
    ("Ch-30", "Biomass", 1.6),
]

# Results tracking
all_metrics = []

# ============================================================================
# RAG Ingestion
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

        # Check for config file
        config_path = Path("pipelines/rag_ingestion/config/semantic_chunking.yaml")
        if not config_path.exists():
            config_path = None

        # Structure detection
        detector = SemanticStructureDetector(config_path)
        structure = detector.detect(pdf_path)

        # Processing plan
        planner = HierarchicalProcessingPlanner(config_path)
        plan = planner.create_plan(structure, output_dir)

        # Semantic processing
        processor = SemanticHierarchicalProcessor(planner.config)
        results = processor.process_plan(plan, pdf_path)

        duration = time.time() - start_time

        # Count chunks
        for section_dir in output_dir.iterdir():
            if section_dir.is_dir():
                chunks_file = section_dir / "chunks.json"
                if chunks_file.exists():
                    with open(chunks_file, 'r', encoding='utf-8') as f:
                        chunks = json.load(f)
                        chunks_created += len(chunks)

        print(f"  ✓ RAG ingestion complete ({duration:.1f}s, {chunks_created} chunks)")
        return True, duration, chunks_created

    except Exception as e:
        duration = time.time() - start_time
        print(f"  ✗ RAG ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return False, duration, 0


# ============================================================================
# JSONL Conversion
# ============================================================================

def convert_to_jsonl(chapter_id: str) -> tuple[bool, float]:
    """Convert RAG JSON arrays to JSONL format."""
    rag_dir = BATCH_RESULTS_DIR / chapter_id / "rag"

    print(f"\n  PHASE 3: CONVERT TO JSONL")

    start_time = time.time()

    try:
        # Find all chunks.json files
        chunk_files = list(rag_dir.glob("*/chunks.json"))
        all_chunks = []

        for chunk_file in chunk_files:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
                if isinstance(chunks, list):
                    all_chunks.extend(chunks)

        # Write JSONL
        jsonl_file = rag_dir / "rag_bundles.jsonl"
        with open(jsonl_file, 'w', encoding='utf-8') as f:
            for chunk in all_chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

        # Create stub citation graph
        citation_graph = {
            "document_name": chapter_id,
            "citation_stats": {
                "total_citations": 0,
                "by_type": {"figure": 0, "table": 0, "equation": 0, "chapter": 0, "reference": 0},
                "chunks_with_citations": 0,
                "chunks_without_citations": len(all_chunks)
            },
            "citations_by_chunk": {}
        }

        graph_file = rag_dir / "citation_graph.json"
        with open(graph_file, 'w', encoding='utf-8') as f:
            json.dump(citation_graph, f, indent=2)

        duration = time.time() - start_time

        print(f"  ✓ Conversion complete ({duration:.1f}s, {len(all_chunks)} chunks)")
        return True, duration

    except Exception as e:
        duration = time.time() - start_time
        print(f"  ✗ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False, duration


# ============================================================================
# Database Ingestion
# ============================================================================

def run_database_ingestion(chapter_id: str, chapter_title: str) -> tuple[bool, float, float]:
    """Load chunks into ChromaDB."""
    rag_dir = BATCH_RESULTS_DIR / chapter_id / "rag"
    db_dir = BATCH_RESULTS_DIR / chapter_id / "database" / "chromadb"

    print(f"\n  PHASE 4: DATABASE INGESTION")
    print(f"  Output: {db_dir}")

    start_time = time.time()
    db_size_mb = 0.0

    try:
        # Load chunks
        jsonl_file = rag_dir / "rag_bundles.jsonl"
        chunks = []
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line.strip()))

        # Setup ChromaDB
        db_dir.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(
            path=str(db_dir),
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )

        # Create collection
        collection_name = f"{chapter_id.lower().replace('-', '_')}"

        try:
            client.delete_collection(name=collection_name)
        except:
            pass

        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        collection = client.create_collection(
            name=collection_name,
            embedding_function=embedding_fn,
            metadata={
                "description": f"{chapter_id}: {chapter_title}",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        )

        # Prepare data
        ids = [c['chunk_id'] for c in chunks]
        documents = [c['text'] for c in chunks]
        metadatas = []
        for c in chunks:
            meta = {
                'chunk_id': c['chunk_id'],
                'page_number': str(c['page_number']),
                'char_count': str(c['char_count']),
                'section_title': c['metadata'].get('section_title', '')
            }
            metadatas.append(meta)

        # Insert in batches
        BATCH_SIZE = 10
        for i in range(0, len(chunks), BATCH_SIZE):
            batch_end = min(i + BATCH_SIZE, len(chunks))
            collection.add(
                ids=ids[i:batch_end],
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end]
            )

        # Get database size
        db_size_mb = sum(f.stat().st_size for f in db_dir.rglob('*') if f.is_file()) / (1024 * 1024)

        duration = time.time() - start_time

        print(f"  ✓ Database ingestion complete ({duration:.1f}s, {len(chunks)} chunks)")
        print(f"     DB size: {db_size_mb:.2f} MB")

        return True, duration, db_size_mb

    except Exception as e:
        duration = time.time() - start_time
        print(f"  ✗ Database ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return False, duration, 0.0


# ============================================================================
# Process Chapter
# ============================================================================

def process_chapter(chapter_id: str, chapter_title: str, pdf_size_mb: float) -> Dict[str, Any]:
    """Process a single chapter through RAG and database phases."""
    print(f"\n{'='*80}")
    print(f"PROCESSING: {chapter_id} - {chapter_title}")
    print(f"{'='*80}")

    # Find PDF file
    pdf_files = list(TEST_DATA_DIR.glob(f"{chapter_id}_*.pdf"))
    if not pdf_files:
        print(f"  ✗ PDF not found in {TEST_DATA_DIR}")
        return None

    pdf_path = pdf_files[0]

    metrics = {
        'chapter': chapter_id,
        'title': chapter_title,
        'pdf_size_mb': pdf_size_mb,
        'status': 'pending',
        'extraction_s': 'N/A',  # Already completed
        'rag_s': 0,
        'database_s': 0,
        'total_s': 0,
        'chunks_created': 0,
        'db_size_mb': 0.0
    }

    start_time = time.time()

    # Phase 2: RAG Ingestion
    success, rag_duration, chunks_created = run_rag_ingestion(chapter_id, pdf_path)
    metrics['rag_s'] = rag_duration
    metrics['chunks_created'] = chunks_created

    if not success:
        metrics['status'] = 'FAILED (rag)'
        return metrics

    # Phase 3: JSONL Conversion
    success, jsonl_duration = convert_to_jsonl(chapter_id)
    if not success:
        metrics['status'] = 'FAILED (jsonl)'
        return metrics

    # Phase 4: Database Ingestion
    success, db_duration, db_size_mb = run_database_ingestion(chapter_id, chapter_title)
    metrics['database_s'] = db_duration
    metrics['db_size_mb'] = db_size_mb

    if not success:
        metrics['status'] = 'FAILED (database)'
        return metrics

    # Success
    metrics['total_s'] = time.time() - start_time
    metrics['status'] = 'SUCCESS'

    print(f"\n  ✓ {chapter_id} COMPLETE")
    print(f"     Total: {metrics['total_s']:.1f}s")

    return metrics


# ============================================================================
# Main
# ============================================================================

def main():
    """Main processing function."""
    print(f"\n{'#'*80}")
    print(f"# COMPLETE BATCH PROCESSING: RAG + DATABASE PHASES")
    print(f"{'#'*80}")
    print(f"\nStart time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Create output directory
    BATCH_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    batch_start = time.time()

    # Process each chapter
    for chapter_id, chapter_title, pdf_size_mb in CHAPTERS:
        metrics = process_chapter(chapter_id, chapter_title, pdf_size_mb)
        if metrics:
            all_metrics.append(metrics)

    batch_duration = time.time() - batch_start

    # Generate reports
    print(f"\n{'#'*80}")
    print(f"# GENERATING REPORTS")
    print(f"{'#'*80}\n")

    # CSV report
    csv_file = BATCH_RESULTS_DIR / "batch_1_metrics.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['chapter', 'title', 'pdf_size_mb', 'extraction_s', 'rag_s',
                      'database_s', 'total_s', 'chunks_created', 'db_size_mb', 'status']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for m in all_metrics:
            writer.writerow(m)

    # JSON summary
    successful = [m for m in all_metrics if m['status'] == 'SUCCESS']
    json_file = BATCH_RESULTS_DIR / "batch_1_summary.json"

    summary = {
        "batch_name": "Batch 1 - MICRO Chapters",
        "processing_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "total_chapters": len(all_metrics),
        "successful_count": len(successful),
        "failed_count": len(all_metrics) - len(successful),
        "success_rate_pct": (len(successful) / len(all_metrics) * 100) if all_metrics else 0,
        "total_processing_time_s": batch_duration,
        "total_processing_time_min": batch_duration / 60,
    }

    if successful:
        summary.update({
            "average_time_per_chapter_s": sum(m['total_s'] for m in successful) / len(successful),
            "total_chunks_created": sum(m['chunks_created'] for m in successful),
            "total_database_size_mb": sum(m['db_size_mb'] for m in successful),
            "performance_by_phase": {
                "rag_avg_s": sum(m['rag_s'] for m in successful) / len(successful),
                "database_avg_s": sum(m['database_s'] for m in successful) / len(successful),
            }
        })

    summary["chapters"] = all_metrics

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Markdown report
    md_file = BATCH_RESULTS_DIR / "BATCH_1_TIMING_REPORT.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write("# Batch 1 Processing Timing Report\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Executive Summary\n\n")
        f.write(f"- **Total chapters**: {len(all_metrics)}\n")
        f.write(f"- **Successful**: {len(successful)}\n")
        f.write(f"- **Failed**: {len(all_metrics) - len(successful)}\n")
        f.write(f"- **Success rate**: {len(successful)/len(all_metrics)*100:.1f}%\n\n")

        if successful:
            total_chunks = sum(m['chunks_created'] for m in successful)
            total_db = sum(m['db_size_mb'] for m in successful)
            avg_time = sum(m['total_s'] for m in successful) / len(successful)

            f.write(f"- **Total processing time**: {batch_duration:.1f}s ({batch_duration/60:.1f} min)\n")
            f.write(f"- **Average time per chapter**: {avg_time:.1f}s\n")
            f.write(f"- **Total chunks created**: {total_chunks}\n")
            f.write(f"- **Total database size**: {total_db:.2f} MB\n\n")

        f.write("## Per-Chapter Results\n\n")
        f.write("| Chapter | Status | RAG (s) | DB (s) | Total (s) | Chunks | DB Size (MB) |\n")
        f.write("|---------|--------|---------|--------|-----------|--------|---------------|\n")

        for m in all_metrics:
            status_icon = "✓" if m['status'] == 'SUCCESS' else "✗"
            f.write(f"| {m['chapter']} | {status_icon} {m['status']} | "
                    f"{m['rag_s']:.1f} | {m['database_s']:.1f} | {m['total_s']:.1f} | "
                    f"{m['chunks_created']} | {m['db_size_mb']:.2f} |\n")

    # Final summary
    print(f"\n{'='*80}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"{'='*80}\n")
    print(f"Total time: {batch_duration/60:.1f} minutes")
    print(f"Successful: {len(successful)}/{len(all_metrics)}")
    print(f"Failed: {len(all_metrics) - len(successful)}/{len(all_metrics)}\n")

    if successful:
        print(f"✓ Successful chapters:")
        for m in successful:
            print(f"  - {m['chapter']}: {m['chunks_created']} chunks, {m['db_size_mb']:.2f} MB")

    print(f"\nOutput files:")
    print(f"  - {csv_file}")
    print(f"  - {json_file}")
    print(f"  - {md_file}\n")

    return 0 if len(successful) == len(all_metrics) else 1


if __name__ == "__main__":
    sys.exit(main())
