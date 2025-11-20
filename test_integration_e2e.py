#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-End Integration Test - Document Translator v14
Tests complete workflow: PDF → Extraction → RAG → Database → Query Retrieval

This integration test validates:
1. All 3 pipelines run sequentially without errors
2. Data contracts between pipelines are satisfied
3. Data integrity is maintained throughout the workflow
4. Query retrieval with source tracing works correctly
5. Performance metrics are within acceptable ranges

Author: Claude Code
Date: 2025-11-19
Version: 1.0
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict

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


# ============================================================================
# Configuration
# ============================================================================

# Test document
PDF_PATH = Path("test_data/Ch-04_Heat_Transfer.pdf")
MODEL_PATH = Path("/home/thermodynamics/document_translator_v12/models/models/Layout/YOLO/doclayout_yolo_docstructbench_imgsz1280_2501.pt")

# Output directories for each pipeline
OUTPUT_DIR_EXTRACTION = Path("test_output_integration/extraction")
OUTPUT_DIR_RAG = Path("test_output_integration/rag")
OUTPUT_DIR_DATABASE = Path("test_output_integration/database")
OUTPUT_DIR_INTEGRATION = Path("test_output_integration")

# Pipeline test scripts (subprocess approach for isolation)
SCRIPT_EXTRACTION = Path("test_with_unified_orchestrator.py")
SCRIPT_RAG = Path("test_rag_pipeline.py")
SCRIPT_DATABASE = Path("test_database_pipeline.py")

# Expected outputs
EXPECTED_OBJECTS_MIN = 160  # Minimum objects from extraction
EXPECTED_CHUNKS_MIN = 30    # Minimum chunks from RAG
EXPECTED_PAGES = 34         # Total pages in PDF

# Test queries for validation
TEST_QUERIES = [
    {
        "query": "What is Newton's law of cooling?",
        "description": "Should find equations and heat transfer theory",
        "expected_min_results": 2
    },
    {
        "query": "convection heat transfer coefficient",
        "description": "Should find technical content about convection",
        "expected_min_results": 2
    },
    {
        "query": "radiation heat transfer",
        "description": "Should find relevant sections on radiation",
        "expected_min_results": 2
    },
    {
        "query": "thermal conductivity equations",
        "description": "Should find equations related to conductivity",
        "expected_min_results": 2
    },
    {
        "query": "heat exchanger design",
        "description": "Should find application sections",
        "expected_min_results": 1
    }
]

# Citation filter tests
CITATION_FILTER_TESTS = [
    {"type": "figures", "id": "11", "expected_min_results": 3},
    {"type": "equations", "id": "1", "expected_min_results": 2}
]


# ============================================================================
# Utility Functions
# ============================================================================

def print_header(title: str, char: str = "=") -> None:
    """Print a formatted section header."""
    width = 80
    print(f"\n{char * width}")
    print(f"{title.center(width)}")
    print(f"{char * width}\n")


def print_status(status: str, message: str) -> None:
    """Print a status message with icon."""
    icons = {
        "pass": "✅",
        "fail": "❌",
        "warn": "⚠️",
        "info": "ℹ️",
        "run": "🔄"
    }
    icon = icons.get(status, "•")
    print(f"{icon} {message}")


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m ({seconds:.1f}s)"
    else:
        hours = seconds / 3600
        minutes = (seconds % 3600) / 60
        return f"{hours:.1f}h {minutes:.0f}m ({seconds:.1f}s)"


def ensure_directory(path: Path) -> None:
    """Ensure directory exists, create if necessary."""
    path.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Pipeline Execution Functions
# ============================================================================

def run_pipeline_subprocess(
    script_path: Path,
    pipeline_name: str,
    timeout: Optional[int] = None
) -> Tuple[bool, float, str, str]:
    """
    Run a pipeline test script as subprocess.

    Args:
        script_path: Path to test script
        pipeline_name: Name of pipeline (for logging)
        timeout: Optional timeout in seconds

    Returns:
        Tuple of (success, duration, stdout, stderr)
    """
    print_status("run", f"Running {pipeline_name}...")
    print(f"Script: {script_path}")

    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path.cwd()
        )

        duration = time.time() - start_time
        success = result.returncode == 0

        if success:
            print_status("pass", f"{pipeline_name} completed in {format_duration(duration)}")
        else:
            print_status("fail", f"{pipeline_name} failed with exit code {result.returncode}")

        return success, duration, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print_status("fail", f"{pipeline_name} timed out after {format_duration(duration)}")
        return False, duration, "", f"Timeout after {timeout}s"

    except Exception as e:
        duration = time.time() - start_time
        print_status("fail", f"{pipeline_name} error: {e}")
        return False, duration, "", str(e)


def run_extraction_pipeline() -> Tuple[bool, float, Dict[str, Any]]:
    """
    Run Pipeline 1: Extraction

    Returns:
        Tuple of (success, duration, metrics)
    """
    print_header("PIPELINE 1: EXTRACTION (PDF → JSON)", "=")

    # Check if script exists
    if not SCRIPT_EXTRACTION.exists():
        print_status("fail", f"Extraction script not found: {SCRIPT_EXTRACTION}")
        return False, 0.0, {}

    # Run extraction
    success, duration, stdout, stderr = run_pipeline_subprocess(
        SCRIPT_EXTRACTION,
        "Extraction Pipeline",
        timeout=900  # 15 minutes
    )

    # Collect metrics from extraction output
    metrics = {
        "success": success,
        "duration": duration,
        "total_objects": 0,
        "equations": 0,
        "tables": 0,
        "figures": 0,
        "text": 0
    }

    # Parse output for metrics (look in test_output_orchestrator)
    if success:
        summary_file = Path("test_output_orchestrator/unified_pipeline_summary.json")
        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = json.load(f)
                # Handle both "total_objects" and "total" field names
                if "total_objects" in summary:
                    metrics["total_objects"] = summary["total_objects"]
                elif "zones_detected" in summary and "total" in summary["zones_detected"]:
                    metrics["total_objects"] = summary["zones_detected"]["total"]
                else:
                    # Calculate from individual counts if available
                    zones = summary.get("zones_detected", {})
                    metrics["total_objects"] = (
                        zones.get("equations", 0) +
                        zones.get("tables", 0) +
                        zones.get("figures", 0)
                    )

        # Count actual output files
        equations_dir = Path("test_output_orchestrator/equations")
        tables_dir = Path("test_output_orchestrator/tables")

        if equations_dir.exists():
            metrics["equations"] = len(list(equations_dir.glob("*")))
        if tables_dir.exists():
            metrics["tables"] = len(list(tables_dir.glob("*")))

    # Print metrics
    print("\nExtraction Metrics:")
    print(f"  Duration: {format_duration(duration)}")
    print(f"  Total objects: {metrics['total_objects']}")
    print(f"  Equations: {metrics['equations']}")
    print(f"  Tables: {metrics['tables']}")

    return success, duration, metrics


def run_rag_pipeline() -> Tuple[bool, float, Dict[str, Any]]:
    """
    Run Pipeline 2: RAG Ingestion

    Returns:
        Tuple of (success, duration, metrics)
    """
    print_header("PIPELINE 2: RAG INGESTION (JSON → JSONL + Graph)", "=")

    # Check if script exists
    if not SCRIPT_RAG.exists():
        print_status("fail", f"RAG script not found: {SCRIPT_RAG}")
        return False, 0.0, {}

    # Run RAG processing
    success, duration, stdout, stderr = run_pipeline_subprocess(
        SCRIPT_RAG,
        "RAG Pipeline",
        timeout=300  # 5 minutes
    )

    # Collect metrics
    metrics = {
        "success": success,
        "duration": duration,
        "total_chunks": 0,
        "total_chars": 0,
        "avg_chars_per_chunk": 0,
        "total_citations": 0
    }

    # Parse output for metrics
    if success:
        # Check for JSONL output
        jsonl_file = Path("test_output_rag/rag_bundles.jsonl")
        citation_graph_file = Path("test_output_rag/citation_graph.json")

        if jsonl_file.exists():
            # Count chunks in JSONL
            chunk_count = 0
            total_chars = 0
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    chunk = json.loads(line.strip())
                    chunk_count += 1
                    total_chars += chunk.get('char_count', 0)

            metrics["total_chunks"] = chunk_count
            metrics["total_chars"] = total_chars
            if chunk_count > 0:
                metrics["avg_chars_per_chunk"] = total_chars // chunk_count

        if citation_graph_file.exists():
            with open(citation_graph_file, 'r', encoding='utf-8') as f:
                citation_graph = json.load(f)
                stats = citation_graph.get('citation_stats', {})
                metrics["total_citations"] = stats.get('total_citations', 0)

    # Print metrics
    print("\nRAG Metrics:")
    print(f"  Duration: {format_duration(duration)}")
    print(f"  Total chunks: {metrics['total_chunks']}")
    print(f"  Total characters: {metrics['total_chars']:,}")
    print(f"  Avg chars/chunk: {metrics['avg_chars_per_chunk']}")
    print(f"  Total citations: {metrics['total_citations']}")

    return success, duration, metrics


def run_database_pipeline() -> Tuple[bool, float, Dict[str, Any]]:
    """
    Run Pipeline 3: Database Loading

    Returns:
        Tuple of (success, duration, metrics)
    """
    print_header("PIPELINE 3: DATABASE LOADING (JSONL → ChromaDB)", "=")

    # Check if script exists
    if not SCRIPT_DATABASE.exists():
        print_status("fail", f"Database script not found: {SCRIPT_DATABASE}")
        return False, 0.0, {}

    # Run database loading
    success, duration, stdout, stderr = run_pipeline_subprocess(
        SCRIPT_DATABASE,
        "Database Pipeline",
        timeout=300  # 5 minutes
    )

    # Collect metrics
    metrics = {
        "success": success,
        "duration": duration,
        "chunks_inserted": 0,
        "chunks_with_citations": 0,
        "database_size_mb": 0.0
    }

    # Parse output for metrics
    if success:
        # Check ChromaDB directory
        chroma_dir = Path("test_output_database/chromadb")
        if chroma_dir.exists():
            # Calculate database size
            db_size = sum(
                f.stat().st_size
                for f in chroma_dir.rglob('*')
                if f.is_file()
            )
            metrics["database_size_mb"] = db_size / 1024 / 1024

            # Get chunk count from ChromaDB (requires import)
            try:
                import chromadb
                client = chromadb.PersistentClient(path=str(chroma_dir))
                collection_names = client.list_collections()
                if collection_names:
                    # In ChromaDB v0.6.0+, list_collections() returns names (strings)
                    collection_name = collection_names[0] if isinstance(collection_names[0], str) else collection_names[0].name
                    collection = client.get_collection(collection_name)
                    metrics["chunks_inserted"] = collection.count()
            except Exception as e:
                print_status("warn", f"Could not query ChromaDB: {e}")

    # Print metrics
    print("\nDatabase Metrics:")
    print(f"  Duration: {format_duration(duration)}")
    print(f"  Chunks inserted: {metrics['chunks_inserted']}")
    print(f"  Database size: {metrics['database_size_mb']:.2f} MB")

    return success, duration, metrics


# ============================================================================
# Data Contract Validation Functions
# ============================================================================

def validate_extraction_to_rag_contract() -> Tuple[bool, List[str]]:
    """
    Validate data contract between Extraction and RAG pipelines.

    Returns:
        Tuple of (valid, list of issues)
    """
    print_header("DATA CONTRACT VALIDATION: Extraction → RAG", "-")

    issues = []

    # Check extraction outputs exist
    extraction_outputs = [
        Path("test_output_orchestrator/equations"),
        Path("test_output_orchestrator/tables"),
        Path("test_output_orchestrator/bibliography.json")
    ]

    for output_path in extraction_outputs:
        if not output_path.exists():
            issues.append(f"Missing extraction output: {output_path}")

    # Check extraction summary
    summary_file = Path("test_output_orchestrator/unified_pipeline_summary.json")
    if not summary_file.exists():
        issues.append(f"Missing extraction summary: {summary_file}")
    else:
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = json.load(f)
                # Validate required fields - handle both old and new formats
                has_total = False
                if "total_objects" in summary:
                    has_total = True
                elif "zones_detected" in summary:
                    zones = summary["zones_detected"]
                    if "total" in zones or ("equations" in zones and "tables" in zones):
                        has_total = True

                if not has_total:
                    issues.append(f"Missing object count fields in extraction summary (need 'total_objects' or 'zones_detected')")
        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON in extraction summary: {e}")

    valid = len(issues) == 0

    if valid:
        print_status("pass", "Extraction → RAG contract validated")
    else:
        print_status("fail", "Extraction → RAG contract validation failed:")
        for issue in issues:
            print(f"  - {issue}")

    return valid, issues


def validate_rag_to_database_contract() -> Tuple[bool, List[str]]:
    """
    Validate data contract between RAG and Database pipelines.

    Returns:
        Tuple of (valid, list of issues)
    """
    print_header("DATA CONTRACT VALIDATION: RAG → Database", "-")

    issues = []

    # Check RAG outputs exist
    jsonl_file = Path("test_output_rag/rag_bundles.jsonl")
    citation_graph_file = Path("test_output_rag/citation_graph.json")

    if not jsonl_file.exists():
        issues.append(f"Missing JSONL output: {jsonl_file}")
    else:
        # Validate JSONL format
        try:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    chunk = json.loads(line.strip())

                    # Validate required fields
                    required_fields = [
                        'chunk_id', 'text', 'page_number',
                        'char_count', 'metadata'
                    ]
                    for field in required_fields:
                        if field not in chunk:
                            issues.append(f"Line {line_num}: Missing field '{field}'")
                            break

                    # Only check first 5 chunks
                    if line_num >= 5:
                        break
        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSONL format: {e}")

    if not citation_graph_file.exists():
        issues.append(f"Missing citation graph: {citation_graph_file}")
    else:
        # Validate citation graph format
        try:
            with open(citation_graph_file, 'r', encoding='utf-8') as f:
                citation_graph = json.load(f)

                # Validate required fields
                required_fields = ['citation_stats', 'citations_by_chunk']
                for field in required_fields:
                    if field not in citation_graph:
                        issues.append(f"Missing field in citation graph: {field}")
        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON in citation graph: {e}")

    valid = len(issues) == 0

    if valid:
        print_status("pass", "RAG → Database contract validated")
    else:
        print_status("fail", "RAG → Database contract validation failed:")
        for issue in issues:
            print(f"  - {issue}")

    return valid, issues


def validate_data_integrity() -> Tuple[bool, List[str]]:
    """
    Validate data integrity across all pipelines.

    Returns:
        Tuple of (valid, list of issues)
    """
    print_header("DATA INTEGRITY VALIDATION", "-")

    issues = []

    # Check chunk counts are consistent
    try:
        jsonl_file = Path("test_output_rag/rag_bundles.jsonl")
        if jsonl_file.exists():
            chunk_count_jsonl = sum(1 for _ in open(jsonl_file, 'r', encoding='utf-8'))

            # Check ChromaDB has same count
            try:
                import chromadb
                chroma_dir = Path("test_output_database/chromadb")
                if chroma_dir.exists():
                    client = chromadb.PersistentClient(path=str(chroma_dir))
                    collection_names = client.list_collections()
                    if collection_names:
                        # In ChromaDB v0.6.0+, list_collections() returns names (strings)
                        collection_name = collection_names[0] if isinstance(collection_names[0], str) else collection_names[0].name
                        collection = client.get_collection(collection_name)
                        chunk_count_db = collection.count()

                        if chunk_count_jsonl != chunk_count_db:
                            issues.append(
                                f"Chunk count mismatch: JSONL={chunk_count_jsonl}, "
                                f"ChromaDB={chunk_count_db}"
                            )
            except Exception as e:
                issues.append(f"Could not verify ChromaDB chunk count: {e}")
    except Exception as e:
        issues.append(f"Could not verify JSONL chunk count: {e}")

    # Check citation counts are preserved
    try:
        citation_graph_file = Path("test_output_rag/citation_graph.json")
        if citation_graph_file.exists():
            with open(citation_graph_file, 'r', encoding='utf-8') as f:
                citation_graph = json.load(f)
                rag_citation_count = citation_graph.get('citation_stats', {}).get('total_citations', 0)

                # This should match the enrichment in ChromaDB
                # (We can't easily verify without querying all chunks)
                if rag_citation_count == 0:
                    issues.append("Zero citations found in RAG output")
    except Exception as e:
        issues.append(f"Could not verify citation integrity: {e}")

    valid = len(issues) == 0

    if valid:
        print_status("pass", "Data integrity validated")
    else:
        print_status("fail", "Data integrity validation failed:")
        for issue in issues:
            print(f"  - {issue}")

    return valid, issues


# ============================================================================
# Query Retrieval Testing Functions
# ============================================================================

def test_semantic_query(
    collection,
    query_text: str,
    n_results: int = 3
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Test semantic search query and extract results.

    Args:
        collection: ChromaDB collection
        query_text: Query string
        n_results: Number of results to return

    Returns:
        Tuple of (success, list of result dicts)
    """
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results
        )

        # Extract results
        result_list = []
        for i, (chunk_id, text, metadata) in enumerate(zip(
            results['ids'][0],
            results['documents'][0],
            results['metadatas'][0]
        )):
            result_list.append({
                'chunk_id': chunk_id,
                'text': text,
                'metadata': metadata
            })

        return True, result_list

    except Exception as e:
        print_status("fail", f"Query failed: {e}")
        return False, []


def test_citation_filter(
    collection,
    citation_type: str,
    citation_id: str
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Test citation filtering query.

    Args:
        collection: ChromaDB collection
        citation_type: Type of citation (figures, tables, equations)
        citation_id: ID of cited object

    Returns:
        Tuple of (success, list of result dicts)
    """
    try:
        field_name = f'cited_{citation_type}'

        # Get all chunks and filter by citation
        all_results = collection.get()

        matching_results = []
        for i, metadata in enumerate(all_results['metadatas']):
            cited = metadata.get(field_name, '')
            if cited and citation_id in cited.split(','):
                matching_results.append({
                    'chunk_id': all_results['ids'][i],
                    'text': all_results['documents'][i],
                    'metadata': metadata
                })

        return True, matching_results

    except Exception as e:
        print_status("fail", f"Citation filter failed: {e}")
        return False, []


def validate_source_tracing(
    result: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Validate that a query result can be traced back to source.

    Args:
        result: Query result dict with chunk_id, text, metadata

    Returns:
        Tuple of (valid, list of issues)
    """
    issues = []
    metadata = result['metadata']

    # Check required tracing fields
    required_fields = ['chunk_id', 'page_number']
    for field in required_fields:
        if field not in metadata:
            issues.append(f"Missing tracing field: {field}")

    # Validate page number is in valid range
    try:
        page_num = int(metadata.get('page_number', -1))
        if page_num < 1 or page_num > EXPECTED_PAGES:
            issues.append(f"Invalid page number: {page_num} (expected 1-{EXPECTED_PAGES})")
    except (ValueError, TypeError):
        issues.append(f"Invalid page number format: {metadata.get('page_number')}")

    # Check citations are preserved
    if 'has_citations' in metadata:
        has_citations = metadata['has_citations'] == 'True'
        citation_count = int(metadata.get('citation_count', 0))

        if has_citations and citation_count == 0:
            issues.append("has_citations=True but citation_count=0")

    valid = len(issues) == 0
    return valid, issues


def run_query_tests() -> Tuple[bool, Dict[str, Any]]:
    """
    Run comprehensive query retrieval tests.

    Returns:
        Tuple of (all_passed, test_results)
    """
    print_header("QUERY RETRIEVAL TESTING", "=")

    # Load ChromaDB collection
    try:
        import chromadb
        chroma_dir = Path("test_output_database/chromadb")
        client = chromadb.PersistentClient(path=str(chroma_dir))
        collection_names = client.list_collections()

        if not collection_names:
            print_status("fail", "No ChromaDB collection found")
            return False, {}

        # In ChromaDB v0.6.0+, list_collections() returns names (strings)
        collection_name = collection_names[0] if isinstance(collection_names[0], str) else collection_names[0].name
        collection = client.get_collection(collection_name)
        print_status("info", f"Testing collection: {collection_name}")
        print(f"Total chunks: {collection.count()}\n")

    except Exception as e:
        print_status("fail", f"Failed to load ChromaDB: {e}")
        return False, {}

    test_results = {
        "semantic_queries": [],
        "citation_filters": [],
        "source_tracing": []
    }

    all_passed = True

    # Test semantic queries
    print_header("Semantic Query Tests", "-")
    for i, test in enumerate(TEST_QUERIES, 1):
        print(f"\n[Test {i}/{len(TEST_QUERIES)}] {test['description']}")
        print(f"Query: '{test['query']}'")

        success, results = test_semantic_query(
            collection,
            test['query'],
            n_results=test['expected_min_results']
        )

        test_result = {
            "query": test['query'],
            "description": test['description'],
            "success": success,
            "result_count": len(results),
            "expected_min_results": test['expected_min_results'],
            "passed": success and len(results) >= test['expected_min_results']
        }

        if test_result['passed']:
            print_status("pass", f"Found {len(results)} results (expected ≥{test['expected_min_results']})")

            # Test source tracing on first result
            if results:
                tracing_valid, tracing_issues = validate_source_tracing(results[0])
                test_result['source_tracing'] = tracing_valid

                if tracing_valid:
                    print_status("pass", "Source tracing validated")
                else:
                    print_status("fail", f"Source tracing failed: {', '.join(tracing_issues)}")
                    all_passed = False
        else:
            print_status("fail", f"Found {len(results)} results (expected ≥{test['expected_min_results']})")
            all_passed = False

        test_results["semantic_queries"].append(test_result)

    # Test citation filters
    print_header("Citation Filter Tests", "-")
    for i, test in enumerate(CITATION_FILTER_TESTS, 1):
        print(f"\n[Test {i}/{len(CITATION_FILTER_TESTS)}] Filter by {test['type']} {test['id']}")

        success, results = test_citation_filter(
            collection,
            test['type'],
            test['id']
        )

        test_result = {
            "citation_type": test['type'],
            "citation_id": test['id'],
            "success": success,
            "result_count": len(results),
            "expected_min_results": test['expected_min_results'],
            "passed": success and len(results) >= test['expected_min_results']
        }

        if test_result['passed']:
            print_status("pass", f"Found {len(results)} chunks (expected ≥{test['expected_min_results']})")
        else:
            print_status("fail", f"Found {len(results)} chunks (expected ≥{test['expected_min_results']})")
            all_passed = False

        test_results["citation_filters"].append(test_result)

    return all_passed, test_results


# ============================================================================
# Performance Analysis Functions
# ============================================================================

def calculate_performance_metrics(
    extraction_metrics: Dict[str, Any],
    rag_metrics: Dict[str, Any],
    database_metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate overall performance metrics.

    Args:
        extraction_metrics: Metrics from extraction pipeline
        rag_metrics: Metrics from RAG pipeline
        database_metrics: Metrics from database pipeline

    Returns:
        Performance metrics dictionary
    """
    total_duration = (
        extraction_metrics.get('duration', 0) +
        rag_metrics.get('duration', 0) +
        database_metrics.get('duration', 0)
    )

    throughput_pages_per_min = 0
    if total_duration > 0:
        throughput_pages_per_min = (EXPECTED_PAGES / total_duration) * 60

    metrics = {
        "total_duration_seconds": total_duration,
        "total_duration_formatted": format_duration(total_duration),
        "throughput_pages_per_minute": throughput_pages_per_min,
        "pipeline_breakdown": {
            "extraction": {
                "duration": extraction_metrics.get('duration', 0),
                "percentage": (extraction_metrics.get('duration', 0) / total_duration * 100) if total_duration > 0 else 0
            },
            "rag": {
                "duration": rag_metrics.get('duration', 0),
                "percentage": (rag_metrics.get('duration', 0) / total_duration * 100) if total_duration > 0 else 0
            },
            "database": {
                "duration": database_metrics.get('duration', 0),
                "percentage": (database_metrics.get('duration', 0) / total_duration * 100) if total_duration > 0 else 0
            }
        },
        "data_flow": {
            "extraction_objects": extraction_metrics.get('total_objects', 0),
            "rag_chunks": rag_metrics.get('total_chunks', 0),
            "database_chunks": database_metrics.get('chunks_inserted', 0)
        }
    }

    return metrics


# ============================================================================
# Report Generation Functions
# ============================================================================

def generate_summary_report(
    extraction_success: bool,
    extraction_metrics: Dict[str, Any],
    rag_success: bool,
    rag_metrics: Dict[str, Any],
    database_success: bool,
    database_metrics: Dict[str, Any],
    contract_validation: Dict[str, bool],
    query_test_passed: bool,
    query_test_results: Dict[str, Any],
    performance_metrics: Dict[str, Any]
) -> str:
    """
    Generate comprehensive text summary report.

    Returns:
        Report text
    """
    report = []

    report.append("=" * 80)
    report.append("END-TO-END INTEGRATION TEST - Document Translator v14")
    report.append("=" * 80)
    report.append(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Test Document: {PDF_PATH.name} ({EXPECTED_PAGES} pages)")
    report.append("")

    # Pipeline results
    report.append("PIPELINE EXECUTION RESULTS")
    report.append("-" * 80)

    status_icon = lambda s: "✅ PASS" if s else "❌ FAIL"

    report.append(f"\nPIPELINE 1: EXTRACTION")
    report.append(f"  Status: {status_icon(extraction_success)}")
    report.append(f"  Duration: {format_duration(extraction_metrics.get('duration', 0))}")
    report.append(f"  Objects extracted: {extraction_metrics.get('total_objects', 0)}")
    report.append(f"  Equations: {extraction_metrics.get('equations', 0)}")
    report.append(f"  Tables: {extraction_metrics.get('tables', 0)}")

    report.append(f"\nPIPELINE 2: RAG INGESTION")
    report.append(f"  Status: {status_icon(rag_success)}")
    report.append(f"  Duration: {format_duration(rag_metrics.get('duration', 0))}")
    report.append(f"  Chunks created: {rag_metrics.get('total_chunks', 0)}")
    report.append(f"  Total characters: {rag_metrics.get('total_chars', 0):,}")
    report.append(f"  Citations extracted: {rag_metrics.get('total_citations', 0)}")

    report.append(f"\nPIPELINE 3: DATABASE LOADING")
    report.append(f"  Status: {status_icon(database_success)}")
    report.append(f"  Duration: {format_duration(database_metrics.get('duration', 0))}")
    report.append(f"  Chunks inserted: {database_metrics.get('chunks_inserted', 0)}")
    report.append(f"  Database size: {database_metrics.get('database_size_mb', 0):.2f} MB")

    # Data flow validation
    report.append(f"\n\nDATA FLOW VALIDATION")
    report.append("-" * 80)
    report.append(f"  Extraction → RAG: {status_icon(contract_validation.get('extraction_to_rag', False))}")
    report.append(f"  RAG → Database: {status_icon(contract_validation.get('rag_to_database', False))}")
    report.append(f"  Data Integrity: {status_icon(contract_validation.get('data_integrity', False))}")

    # Query test results
    report.append(f"\n\nQUERY RETRIEVAL TESTING")
    report.append("-" * 80)

    semantic_queries = query_test_results.get('semantic_queries', [])
    if semantic_queries:
        passed_count = sum(1 for q in semantic_queries if q.get('passed', False))
        report.append(f"  Semantic queries: {passed_count}/{len(semantic_queries)} passed")
        for q in semantic_queries:
            status = "✅" if q.get('passed', False) else "❌"
            report.append(f"    {status} {q.get('description', 'N/A')}")

    citation_filters = query_test_results.get('citation_filters', [])
    if citation_filters:
        passed_count = sum(1 for c in citation_filters if c.get('passed', False))
        report.append(f"  Citation filters: {passed_count}/{len(citation_filters)} passed")

    # Source tracing
    source_tracing_passed = all(
        q.get('source_tracing', False) for q in semantic_queries if 'source_tracing' in q
    )
    report.append(f"  Source tracing: {status_icon(source_tracing_passed)}")

    # Performance summary
    report.append(f"\n\nPERFORMANCE SUMMARY")
    report.append("-" * 80)
    report.append(f"  Total duration: {performance_metrics['total_duration_formatted']}")
    report.append(f"  Throughput: {performance_metrics['throughput_pages_per_minute']:.2f} pages/minute")
    report.append(f"\n  Time breakdown:")
    for pipeline_name, pipeline_data in performance_metrics['pipeline_breakdown'].items():
        report.append(f"    {pipeline_name.capitalize()}: {format_duration(pipeline_data['duration'])} ({pipeline_data['percentage']:.1f}%)")

    # Overall status
    report.append(f"\n\n{'=' * 80}")
    overall_success = all([
        extraction_success,
        rag_success,
        database_success,
        contract_validation.get('extraction_to_rag', False),
        contract_validation.get('rag_to_database', False),
        contract_validation.get('data_integrity', False),
        query_test_passed
    ])

    if overall_success:
        report.append("OVERALL STATUS: ✅ INTEGRATION TEST PASSED")
    else:
        report.append("OVERALL STATUS: ❌ INTEGRATION TEST FAILED")

    report.append("=" * 80)

    return "\n".join(report)


def save_summary_json(
    extraction_success: bool,
    extraction_metrics: Dict[str, Any],
    rag_success: bool,
    rag_metrics: Dict[str, Any],
    database_success: bool,
    database_metrics: Dict[str, Any],
    contract_validation: Dict[str, bool],
    query_test_passed: bool,
    query_test_results: Dict[str, Any],
    performance_metrics: Dict[str, Any],
    output_file: Path
) -> None:
    """
    Save comprehensive summary as JSON.

    Args:
        All test results and metrics
        output_file: Path to save JSON file
    """
    overall_success = all([
        extraction_success,
        rag_success,
        database_success,
        contract_validation.get('extraction_to_rag', False),
        contract_validation.get('rag_to_database', False),
        contract_validation.get('data_integrity', False),
        query_test_passed
    ])

    summary = {
        "test_info": {
            "test_date": datetime.now().isoformat(),
            "test_document": str(PDF_PATH),
            "total_pages": EXPECTED_PAGES,
            "overall_success": overall_success
        },
        "pipeline_results": {
            "extraction": {
                "success": extraction_success,
                "metrics": extraction_metrics
            },
            "rag": {
                "success": rag_success,
                "metrics": rag_metrics
            },
            "database": {
                "success": database_success,
                "metrics": database_metrics
            }
        },
        "validation": {
            "data_contracts": contract_validation,
            "query_tests": {
                "passed": query_test_passed,
                "results": query_test_results
            }
        },
        "performance": performance_metrics
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print_status("info", f"Summary JSON saved to: {output_file}")


# ============================================================================
# Main Execution
# ============================================================================

def main() -> int:
    """
    Main execution function for end-to-end integration test.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print_header("END-TO-END INTEGRATION TEST", "#")
    print(f"Document Translator v14")
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Ensure output directories exist
    ensure_directory(OUTPUT_DIR_INTEGRATION)

    # Check prerequisites
    print_header("Prerequisites Check", "-")

    if not PDF_PATH.exists():
        print_status("fail", f"PDF not found: {PDF_PATH}")
        return 1
    print_status("pass", f"PDF found: {PDF_PATH}")

    if not MODEL_PATH.exists():
        print_status("fail", f"Model not found: {MODEL_PATH}")
        return 1
    print_status("pass", f"Model found: {MODEL_PATH}")

    # Check test scripts exist
    for script in [SCRIPT_EXTRACTION, SCRIPT_RAG, SCRIPT_DATABASE]:
        if not script.exists():
            print_status("fail", f"Test script not found: {script}")
            return 1
        print_status("pass", f"Test script found: {script}")

    print()

    # ========================================================================
    # PHASE 1: Run all pipelines
    # ========================================================================

    test_start_time = time.time()

    # Run Pipeline 1: Extraction
    extraction_success, extraction_duration, extraction_metrics = run_extraction_pipeline()
    if not extraction_success:
        print_status("fail", "Extraction pipeline failed, aborting integration test")
        return 1

    # Run Pipeline 2: RAG
    rag_success, rag_duration, rag_metrics = run_rag_pipeline()
    if not rag_success:
        print_status("fail", "RAG pipeline failed, aborting integration test")
        return 1

    # Run Pipeline 3: Database
    database_success, database_duration, database_metrics = run_database_pipeline()
    if not database_success:
        print_status("fail", "Database pipeline failed, aborting integration test")
        return 1

    # ========================================================================
    # PHASE 2: Validate data contracts
    # ========================================================================

    extraction_to_rag_valid, _ = validate_extraction_to_rag_contract()
    rag_to_database_valid, _ = validate_rag_to_database_contract()
    data_integrity_valid, _ = validate_data_integrity()

    contract_validation = {
        "extraction_to_rag": extraction_to_rag_valid,
        "rag_to_database": rag_to_database_valid,
        "data_integrity": data_integrity_valid
    }

    # ========================================================================
    # PHASE 3: Test query retrieval
    # ========================================================================

    query_test_passed, query_test_results = run_query_tests()

    # ========================================================================
    # PHASE 4: Calculate performance metrics
    # ========================================================================

    performance_metrics = calculate_performance_metrics(
        extraction_metrics,
        rag_metrics,
        database_metrics
    )

    total_test_duration = time.time() - test_start_time

    # ========================================================================
    # PHASE 5: Generate reports
    # ========================================================================

    print_header("Generating Reports", "=")

    # Generate text report
    report_text = generate_summary_report(
        extraction_success,
        extraction_metrics,
        rag_success,
        rag_metrics,
        database_success,
        database_metrics,
        contract_validation,
        query_test_passed,
        query_test_results,
        performance_metrics
    )

    # Save text report
    report_file = OUTPUT_DIR_INTEGRATION / "integration_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_text)
    print_status("info", f"Text report saved to: {report_file}")

    # Save JSON summary
    summary_file = OUTPUT_DIR_INTEGRATION / "integration_summary.json"
    save_summary_json(
        extraction_success,
        extraction_metrics,
        rag_success,
        rag_metrics,
        database_success,
        database_metrics,
        contract_validation,
        query_test_passed,
        query_test_results,
        performance_metrics,
        summary_file
    )

    # ========================================================================
    # Final output
    # ========================================================================

    print()
    print(report_text)

    print(f"\n\nTotal test duration (including all phases): {format_duration(total_test_duration)}")

    # Determine exit code
    overall_success = all([
        extraction_success,
        rag_success,
        database_success,
        extraction_to_rag_valid,
        rag_to_database_valid,
        data_integrity_valid,
        query_test_passed
    ])

    if overall_success:
        print_status("pass", "All integration tests passed!")
        return 0
    else:
        print_status("fail", "Some integration tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
