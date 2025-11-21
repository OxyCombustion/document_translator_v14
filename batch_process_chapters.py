#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Process Steam Book Chapters - Complete Pipeline

Processes multiple Steam book chapters through the complete pipeline:
1. Extraction (PDF → JSON)
2. RAG Ingestion (JSON → JSONL + semantic chunks)
3. Vector Database (JSONL → ChromaDB)

Tracks detailed timing metrics for each phase and chapter.

Author: Claude Code
Date: 2025-11-20
"""

import sys
import os
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import subprocess

# Add project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

# UTF-8 setup
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')

# ============================================================================
# Configuration
# ============================================================================

# Base paths
ZOTERO_DIR = Path.home() / "windows_zotero" / "storage"
TEST_DATA_DIR = Path("test_data")
MODEL_PATH = Path("models/doclayout_yolo_docstructbench_imgsz1024.pt")
BATCH_OUTPUT_DIR = Path("batch_processing_results")

# Timing CSV output
TIMING_CSV = BATCH_OUTPUT_DIR / "batch_timing_metrics.csv"
SUMMARY_JSON = BATCH_OUTPUT_DIR / "batch_summary.json"

# Chapter definitions (corrected Zotero hashes from agent search)
BATCH_1_CHAPTERS = [
    ("Ch-53", "Nuclear Waste Management", "UNMJIZT3"),
    ("Ch-44", "Boiler Operations", "CZ5R6KY4"),
    ("Ch-48", "Nuclear Fuels", "62IBFRKL"),
    ("Ch-49", "Principles of Nuclear Reactions", "B3STPXVQ"),
    ("Ch-08", "Structural", "8ZZ2YGRA"),
    ("Ch-11", "Oil and Gas", "6LVFMQNR"),  # Corrected
    ("Ch-46", "Condition Assessment", "8LL8VREJ"),  # Corrected
    ("Ch-18", "Coal Gasification", "VTT7N5JX"),  # Corrected
    ("Ch-52", "Nuclear Services Life Ext", "W3E58GFD"),  # Corrected
    ("Ch-30", "Biomass", "QKSVHECM"),  # Corrected
]

# ============================================================================
# Timing Utilities
# ============================================================================

class TimingTracker:
    """Track timing metrics for batch processing."""

    def __init__(self):
        self.metrics = []

    def add_metric(self, chapter: str, phase: str, duration: float,
                   success: bool, details: Dict[str, Any] = None):
        """Add timing metric for a processing phase."""
        metric = {
            'timestamp': datetime.now().isoformat(),
            'chapter': chapter,
            'phase': phase,
            'duration_seconds': round(duration, 2),
            'success': success,
            'details': details or {}
        }
        self.metrics.append(metric)

    def save_csv(self, filepath: Path):
        """Save metrics to CSV file."""
        if not self.metrics:
            return

        headers = ['timestamp', 'chapter', 'phase', 'duration_seconds', 'success']

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(','.join(headers) + '\n')
            for m in self.metrics:
                row = [
                    m['timestamp'],
                    m['chapter'],
                    m['phase'],
                    str(m['duration_seconds']),
                    str(m['success'])
                ]
                f.write(','.join(row) + '\n')

    def get_summary(self) -> Dict[str, Any]:
        """Generate summary statistics."""
        if not self.metrics:
            return {}

        # Group by phase
        by_phase = {}
        for m in self.metrics:
            phase = m['phase']
            if phase not in by_phase:
                by_phase[phase] = []
            by_phase[phase].append(m['duration_seconds'])

        summary = {
            'total_chapters_processed': len(set(m['chapter'] for m in self.metrics)),
            'total_time_seconds': sum(m['duration_seconds'] for m in self.metrics),
            'by_phase': {}
        }

        for phase, durations in by_phase.items():
            summary['by_phase'][phase] = {
                'total_seconds': round(sum(durations), 2),
                'avg_seconds': round(sum(durations) / len(durations), 2),
                'min_seconds': round(min(durations), 2),
                'max_seconds': round(max(durations), 2),
                'count': len(durations)
            }

        return summary


# ============================================================================
# Pipeline Processing Functions
# ============================================================================

def copy_chapter_from_zotero(chapter_id: str, chapter_title: str,
                              zotero_hash: str) -> Optional[Path]:
    """
    Copy chapter PDF from Zotero to test_data directory.

    Args:
        chapter_id: Chapter identifier (e.g., "Ch-53")
        chapter_title: Chapter title
        zotero_hash: Zotero storage hash

    Returns:
        Path to copied PDF, or None if failed
    """
    source = ZOTERO_DIR / zotero_hash / f"{chapter_id} {chapter_title}.pdf"
    dest = TEST_DATA_DIR / f"{chapter_id}_{chapter_title.replace(' ', '_')}.pdf"

    if not source.exists():
        print(f"  ✗ Source not found: {source}")
        return None

    TEST_DATA_DIR.mkdir(exist_ok=True)
    shutil.copy2(source, dest)
    print(f"  ✓ Copied to: {dest}")
    return dest


def run_extraction(pdf_path: Path, chapter_id: str) -> tuple[bool, float, Dict[str, Any]]:
    """
    Run extraction pipeline (Phase 1).

    Returns:
        (success, duration, details)
    """
    output_dir = BATCH_OUTPUT_DIR / chapter_id / "extraction"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  PHASE 1: EXTRACTION")
    print(f"  Output: {output_dir}")

    start_time = time.time()

    try:
        # Import and run extraction orchestrator
        from pipelines.rag_ingestion.packages.rag_v14_P2.src.orchestrators.unified_pipeline_orchestrator import UnifiedPipelineOrchestrator

        orchestrator = UnifiedPipelineOrchestrator(
            model_path=str(MODEL_PATH),
            output_dir=output_dir,
            clean_before_run=True,
            enable_structured_output=False  # Disable for batch speed
        )

        results = orchestrator.process_document(
            pdf_path=pdf_path,
            num_workers=8
        )

        duration = time.time() - start_time

        # Read summary for details
        summary_file = output_dir / "unified_pipeline_summary.json"
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                summary = json.load(f)
                details = {
                    'zones_detected': summary.get('zones_detected', {}),
                    'objects_extracted': summary.get('objects_extracted', {})
                }
        else:
            details = {}

        print(f"  ✓ Extraction complete ({duration:.1f}s)")
        return True, duration, details

    except Exception as e:
        duration = time.time() - start_time
        print(f"  ✗ Extraction failed: {e}")
        return False, duration, {'error': str(e)}


def run_rag_ingestion(chapter_id: str, pdf_path: Path) -> tuple[bool, float, Dict[str, Any]]:
    """
    Run RAG ingestion pipeline (Phase 2).

    Returns:
        (success, duration, details)
    """
    output_dir = BATCH_OUTPUT_DIR / chapter_id / "rag"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  PHASE 2: RAG INGESTION")
    print(f"  Output: {output_dir}")

    start_time = time.time()

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

        # Save chunks
        chunk_count = 0
        for section_dir in output_dir.iterdir():
            if section_dir.is_dir():
                chunks_file = section_dir / "chunks.json"
                if chunks_file.exists():
                    with open(chunks_file, 'r') as f:
                        chunks = json.load(f)
                        chunk_count += len(chunks)

        details = {
            'chunks_created': chunk_count,
            'sections': len(structure.sections)
        }

        print(f"  ✓ RAG ingestion complete ({duration:.1f}s, {chunk_count} chunks)")
        return True, duration, details

    except Exception as e:
        duration = time.time() - start_time
        print(f"  ✗ RAG ingestion failed: {e}")
        return False, duration, {'error': str(e)}


def convert_to_jsonl(chapter_id: str) -> tuple[bool, float, Dict[str, Any]]:
    """
    Convert RAG JSON arrays to JSONL format (Phase 3).

    Returns:
        (success, duration, details)
    """
    rag_dir = BATCH_OUTPUT_DIR / chapter_id / "rag"

    print(f"\n  PHASE 3: CONVERT TO JSONL")

    start_time = time.time()

    try:
        # Find all chunks.json files
        chunk_files = list(rag_dir.glob("*/chunks.json"))

        all_chunks = []
        for chunk_file in chunk_files:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
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
                "by_type": {"figure": 0, "table": 0, "equation": 0, "chapter": 0, "reference": 0}
            },
            "citations_by_chunk": {}
        }

        graph_file = rag_dir / "citation_graph.json"
        with open(graph_file, 'w', encoding='utf-8') as f:
            json.dump(citation_graph, f, indent=2)

        duration = time.time() - start_time

        details = {
            'chunks_written': len(all_chunks),
            'jsonl_size_kb': jsonl_file.stat().st_size / 1024
        }

        print(f"  ✓ Conversion complete ({duration:.1f}s, {len(all_chunks)} chunks)")
        return True, duration, details

    except Exception as e:
        duration = time.time() - start_time
        print(f"  ✗ Conversion failed: {e}")
        return False, duration, {'error': str(e)}


def run_database_ingestion(chapter_id: str) -> tuple[bool, float, Dict[str, Any]]:
    """
    Run database ingestion pipeline (Phase 4).

    Returns:
        (success, duration, details)
    """
    rag_dir = BATCH_OUTPUT_DIR / chapter_id / "rag"
    db_dir = BATCH_OUTPUT_DIR / chapter_id / "database"
    db_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  PHASE 4: DATABASE INGESTION")
    print(f"  Output: {db_dir}")

    start_time = time.time()

    try:
        import chromadb
        from chromadb.config import Settings
        from chromadb.utils import embedding_functions

        # Initialize ChromaDB
        client = chromadb.PersistentClient(
            path=str(db_dir / "chromadb"),
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
            embedding_function=embedding_fn
        )

        # Load chunks
        jsonl_file = rag_dir / "rag_bundles.jsonl"
        chunks = []
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                chunks.append(json.loads(line))

        # Prepare for insertion
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

        # Insert
        collection.add(ids=ids, documents=documents, metadatas=metadatas)

        duration = time.time() - start_time

        # Get database size
        db_size = sum(f.stat().st_size for f in (db_dir / "chromadb").rglob('*') if f.is_file())

        details = {
            'chunks_inserted': len(chunks),
            'database_size_mb': round(db_size / 1024 / 1024, 2)
        }

        print(f"  ✓ Database ingestion complete ({duration:.1f}s, {len(chunks)} chunks)")
        return True, duration, details

    except Exception as e:
        duration = time.time() - start_time
        print(f"  ✗ Database ingestion failed: {e}")
        return False, duration, {'error': str(e)}


# ============================================================================
# Main Batch Processing
# ============================================================================

def process_chapter(chapter_id: str, chapter_title: str, zotero_hash: str,
                    tracker: TimingTracker) -> bool:
    """
    Process a single chapter through all pipelines.

    Returns:
        True if all phases succeeded, False otherwise
    """
    print(f"\n{'='*80}")
    print(f"PROCESSING: {chapter_id} - {chapter_title}")
    print(f"{'='*80}")

    # Copy from Zotero
    pdf_path = copy_chapter_from_zotero(chapter_id, chapter_title, zotero_hash)
    if not pdf_path:
        return False

    # Phase 1: Extraction
    success, duration, details = run_extraction(pdf_path, chapter_id)
    tracker.add_metric(chapter_id, "extraction", duration, success, details)
    if not success:
        return False

    # Phase 2: RAG Ingestion
    success, duration, details = run_rag_ingestion(chapter_id, pdf_path)
    tracker.add_metric(chapter_id, "rag_ingestion", duration, success, details)
    if not success:
        return False

    # Phase 3: Convert to JSONL
    success, duration, details = convert_to_jsonl(chapter_id)
    tracker.add_metric(chapter_id, "jsonl_conversion", duration, success, details)
    if not success:
        return False

    # Phase 4: Database Ingestion
    success, duration, details = run_database_ingestion(chapter_id)
    tracker.add_metric(chapter_id, "database_ingestion", duration, success, details)
    if not success:
        return False

    print(f"\n✓ {chapter_id} COMPLETE - All phases succeeded")
    return True


def main():
    """Main batch processing entry point."""
    print(f"\n{'#'*80}")
    print(f"# BATCH PROCESSING: STEAM BOOK CHAPTERS")
    print(f"{'#'*80}")
    print(f"\nStart time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nProcessing Batch 1: {len(BATCH_1_CHAPTERS)} chapters (MICRO)")
    print()

    # Create output directory
    BATCH_OUTPUT_DIR.mkdir(exist_ok=True)

    # Initialize timing tracker
    tracker = TimingTracker()

    # Process each chapter
    batch_start = time.time()
    successful = []
    failed = []

    for chapter_id, chapter_title, zotero_hash in BATCH_1_CHAPTERS:
        try:
            if process_chapter(chapter_id, chapter_title, zotero_hash, tracker):
                successful.append(chapter_id)
            else:
                failed.append(chapter_id)
        except Exception as e:
            print(f"\n✗ {chapter_id} FAILED with exception: {e}")
            failed.append(chapter_id)

    batch_duration = time.time() - batch_start

    # Save metrics
    tracker.save_csv(TIMING_CSV)

    summary = tracker.get_summary()
    summary['batch_duration_seconds'] = round(batch_duration, 2)
    summary['successful_chapters'] = successful
    summary['failed_chapters'] = failed

    with open(SUMMARY_JSON, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    # Print final summary
    print(f"\n{'='*80}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"\nTotal time: {batch_duration / 60:.1f} minutes")
    print(f"Successful: {len(successful)}/{len(BATCH_1_CHAPTERS)}")
    print(f"Failed: {len(failed)}/{len(BATCH_1_CHAPTERS)}")

    if successful:
        print(f"\n✓ Successful chapters:")
        for ch in successful:
            print(f"  - {ch}")

    if failed:
        print(f"\n✗ Failed chapters:")
        for ch in failed:
            print(f"  - {ch}")

    print(f"\nMetrics saved to:")
    print(f"  - {TIMING_CSV}")
    print(f"  - {SUMMARY_JSON}")
    print()

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
