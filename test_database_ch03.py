#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline 3 (Database) Test Script - JSONL to ChromaDB Ingestion

Tests the complete database ingestion pipeline:
- Load JSONL chunks from Pipeline 2 output
- Load citation graph for metadata enrichment
- Create ChromaDB collection with local embeddings
- Enrich chunk metadata with citation information
- Batch insert with retry logic
- Validate insertion and metadata
- Test semantic queries with citation filtering

Author: Claude Code
Date: 2025-11-19
Version: 1.0
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

# ChromaDB imports
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


# ============================================================================
# Configuration
# ============================================================================

# Input files from Pipeline 2 (Chapter 3)
INPUT_DIR = Path("/home/thermodynamics/document_translator_v14/test_output_ch03_rag")
JSONL_FILE = INPUT_DIR / "rag_bundles.jsonl"
CITATION_GRAPH_FILE = INPUT_DIR / "citation_graph.json"

# Output directory for ChromaDB
OUTPUT_DIR = Path("/home/thermodynamics/document_translator_v14/test_output_database_ch03")
CHROMA_DIR = OUTPUT_DIR / "chromadb"

# ChromaDB collection settings
COLLECTION_NAME = "chapter_3_fluid_dynamics"
COLLECTION_DESCRIPTION = "Chapter 3 semantic chunks (Fluid Dynamics)"

# Batch processing settings
BATCH_SIZE = 10
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


# ============================================================================
# Data Loading Functions
# ============================================================================

def load_jsonl_chunks(file_path: Path) -> List[Dict[str, Any]]:
    """
    Load JSONL chunks from Pipeline 2 output.

    Args:
        file_path: Path to rag_bundles.jsonl file

    Returns:
        List of chunk dictionaries
    """
    print(f"\n{'='*80}")
    print(f"LOADING JSONL CHUNKS")
    print(f"{'='*80}")
    print(f"Source: {file_path}")

    chunks = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                chunk = json.loads(line.strip())
                chunks.append(chunk)
            except json.JSONDecodeError as e:
                print(f"ERROR: Failed to parse line {line_num}: {e}")
                continue

    print(f"✓ Loaded {len(chunks)} chunks")

    # Show sample chunk
    if chunks:
        print(f"\nSample chunk (first):")
        sample = chunks[0]
        print(f"  - chunk_id: {sample['chunk_id']}")
        print(f"  - page_number: {sample['page_number']}")
        print(f"  - char_count: {sample['char_count']}")
        print(f"  - section: {sample['metadata'].get('section_title', 'N/A')}")
        print(f"  - text preview: {sample['text'][:100]}...")

    return chunks


def load_citation_graph(file_path: Path) -> Dict[str, Any]:
    """
    Load citation graph from Pipeline 2 output.

    Args:
        file_path: Path to citation_graph.json file

    Returns:
        Citation graph dictionary
    """
    print(f"\n{'='*80}")
    print(f"LOADING CITATION GRAPH")
    print(f"{'='*80}")
    print(f"Source: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        citation_graph = json.load(f)

    stats = citation_graph.get('citation_stats', {})
    print(f"✓ Total citations: {stats.get('total_citations', 0)}")
    print(f"  - Figures: {stats.get('by_type', {}).get('figure', 0)}")
    print(f"  - Tables: {stats.get('by_type', {}).get('table', 0)}")
    print(f"  - Equations: {stats.get('by_type', {}).get('equation', 0)}")
    print(f"  - Chapters: {stats.get('by_type', {}).get('chapter', 0)}")
    print(f"  - References: {stats.get('by_type', {}).get('reference', 0)}")

    return citation_graph


# ============================================================================
# Metadata Enrichment Functions
# ============================================================================

def enrich_chunk_metadata(
    chunk: Dict[str, Any],
    citation_graph: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Enrich chunk metadata with citation information.

    Args:
        chunk: Original chunk from JSONL
        citation_graph: Citation graph data

    Returns:
        Enriched metadata dictionary suitable for ChromaDB
    """
    chunk_id = chunk['chunk_id']
    citations_by_chunk = citation_graph.get('citations_by_chunk', {})
    chunk_citations = citations_by_chunk.get(chunk_id, {})

    # Extract base metadata
    metadata = {
        'chunk_id': chunk_id,
        'page_number': str(chunk['page_number']),  # ChromaDB requires string values
        'char_count': str(chunk['char_count']),
        'section_id': chunk['metadata'].get('section_id', ''),
        'section_title': chunk['metadata'].get('section_title', ''),
        'section_type': chunk['metadata'].get('section_type', ''),
        'is_complete_section': str(chunk['metadata'].get('is_complete_section', False)),
        'unit_id': chunk['metadata'].get('unit_id', ''),
    }

    # Add citation enrichment
    figures = chunk_citations.get('figures', [])
    tables = chunk_citations.get('tables', [])
    equations = chunk_citations.get('equations', [])
    chapters = chunk_citations.get('chapters', [])
    references = chunk_citations.get('references', [])

    # Citation counts
    total_citations = len(figures) + len(tables) + len(equations) + len(chapters) + len(references)
    metadata['has_citations'] = str(total_citations > 0)
    metadata['citation_count'] = str(total_citations)

    # Individual citation types (convert lists to comma-separated strings)
    metadata['cited_figures'] = ','.join(figures) if figures else ''
    metadata['cited_tables'] = ','.join(tables) if tables else ''
    metadata['cited_equations'] = ','.join(equations) if equations else ''
    metadata['cited_chapters'] = ','.join(chapters) if chapters else ''
    metadata['cited_references'] = ','.join(references) if references else ''

    # Individual counts
    metadata['figure_count'] = str(len(figures))
    metadata['table_count'] = str(len(tables))
    metadata['equation_count'] = str(len(equations))
    metadata['chapter_count'] = str(len(chapters))
    metadata['reference_count'] = str(len(references))

    return metadata


def prepare_batch_for_chromadb(
    chunks: List[Dict[str, Any]],
    citation_graph: Dict[str, Any]
) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
    """
    Prepare chunks for ChromaDB batch insertion.

    Args:
        chunks: List of chunk dictionaries
        citation_graph: Citation graph data

    Returns:
        Tuple of (ids, documents, metadatas)
    """
    ids = []
    documents = []
    metadatas = []

    for chunk in chunks:
        chunk_id = chunk['chunk_id']
        text = chunk['text']
        metadata = enrich_chunk_metadata(chunk, citation_graph)

        ids.append(chunk_id)
        documents.append(text)
        metadatas.append(metadata)

    return ids, documents, metadatas


# ============================================================================
# ChromaDB Setup Functions
# ============================================================================

def setup_chromadb_client() -> chromadb.PersistentClient:
    """
    Initialize ChromaDB persistent client.

    Returns:
        ChromaDB client instance
    """
    print(f"\n{'='*80}")
    print(f"INITIALIZING CHROMADB CLIENT")
    print(f"{'='*80}")

    # Create output directory
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Database location: {CHROMA_DIR}")

    # Initialize client
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )

    print(f"✓ ChromaDB client initialized")
    return client


def create_collection(client: chromadb.PersistentClient) -> chromadb.Collection:
    """
    Create or get ChromaDB collection with embedding function.

    Args:
        client: ChromaDB client instance

    Returns:
        ChromaDB collection
    """
    print(f"\n{'='*80}")
    print(f"CREATING CHROMADB COLLECTION")
    print(f"{'='*80}")
    print(f"Collection name: {COLLECTION_NAME}")

    # Try to delete existing collection if it exists
    try:
        client.delete_collection(name=COLLECTION_NAME)
        print(f"✓ Deleted existing collection")
    except Exception:
        pass  # Collection doesn't exist, that's fine

    # Use sentence-transformers embedding function (local, no API needed)
    # This is a small, fast model suitable for testing
    print(f"Initializing embedding function: all-MiniLM-L6-v2")
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    # Create collection
    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={
            "description": COLLECTION_DESCRIPTION,
            "source": "Pipeline 2 RAG output",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    )

    print(f"✓ Collection created successfully")
    return collection


# ============================================================================
# Database Insertion Functions
# ============================================================================

def insert_chunks_with_retry(
    collection: chromadb.Collection,
    chunks: List[Dict[str, Any]],
    citation_graph: Dict[str, Any]
) -> Tuple[int, int]:
    """
    Insert chunks into ChromaDB with batch processing and retry logic.

    Args:
        collection: ChromaDB collection
        chunks: List of chunk dictionaries
        citation_graph: Citation graph data

    Returns:
        Tuple of (successful_count, failed_count)
    """
    print(f"\n{'='*80}")
    print(f"INSERTING CHUNKS INTO CHROMADB")
    print(f"{'='*80}")
    print(f"Total chunks: {len(chunks)}")
    print(f"Batch size: {BATCH_SIZE}")

    successful = 0
    failed = 0

    # Process in batches
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} chunks)...")

        # Prepare batch data
        ids, documents, metadatas = prepare_batch_for_chromadb(batch, citation_graph)

        # Retry logic
        retry_count = 0
        while retry_count < MAX_RETRIES:
            try:
                collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
                successful += len(batch)
                print(f"  ✓ Batch {batch_num} inserted successfully")
                break
            except Exception as e:
                retry_count += 1
                if retry_count < MAX_RETRIES:
                    print(f"  ⚠ Batch {batch_num} failed (attempt {retry_count}/{MAX_RETRIES}): {e}")
                    print(f"  Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"  ✗ Batch {batch_num} failed after {MAX_RETRIES} attempts: {e}")
                    failed += len(batch)

    print(f"\n{'='*80}")
    print(f"INSERTION SUMMARY")
    print(f"{'='*80}")
    print(f"✓ Successful: {successful}")
    if failed > 0:
        print(f"✗ Failed: {failed}")

    return successful, failed


# ============================================================================
# Validation Functions
# ============================================================================

def validate_insertion(
    collection: chromadb.Collection,
    expected_count: int,
    citation_graph: Dict[str, Any]
) -> bool:
    """
    Validate that chunks were inserted correctly.

    Args:
        collection: ChromaDB collection
        expected_count: Expected number of chunks
        citation_graph: Citation graph data

    Returns:
        True if validation passed, False otherwise
    """
    print(f"\n{'='*80}")
    print(f"VALIDATING INSERTION")
    print(f"{'='*80}")

    # Check count
    actual_count = collection.count()
    print(f"Expected chunks: {expected_count}")
    print(f"Actual chunks:   {actual_count}")

    if actual_count != expected_count:
        print(f"✗ Count mismatch!")
        return False
    print(f"✓ Count matches")

    # Check metadata fields (get one sample)
    results = collection.get(limit=1)
    if not results['ids']:
        print(f"✗ No chunks found in collection")
        return False

    sample_metadata = results['metadatas'][0]
    expected_fields = [
        'chunk_id', 'page_number', 'char_count', 'section_id', 'section_title',
        'has_citations', 'citation_count', 'cited_figures', 'cited_tables',
        'cited_equations', 'figure_count', 'table_count', 'equation_count'
    ]

    print(f"\nValidating metadata fields...")
    missing_fields = [field for field in expected_fields if field not in sample_metadata]
    if missing_fields:
        print(f"✗ Missing fields: {missing_fields}")
        return False
    print(f"✓ All expected metadata fields present")

    # Sample metadata details
    print(f"\nSample metadata (chunk: {results['ids'][0]}):")
    print(f"  - section_title: {sample_metadata.get('section_title')}")
    print(f"  - has_citations: {sample_metadata.get('has_citations')}")
    print(f"  - citation_count: {sample_metadata.get('citation_count')}")
    print(f"  - cited_figures: {sample_metadata.get('cited_figures', 'none')}")
    print(f"  - cited_equations: {sample_metadata.get('cited_equations', 'none')}")

    # Check citation enrichment statistics
    chunks_with_citations = 0
    total_citations = 0

    all_results = collection.get()
    for metadata in all_results['metadatas']:
        if metadata.get('has_citations') == 'True':
            chunks_with_citations += 1
            total_citations += int(metadata.get('citation_count', 0))

    print(f"\nCitation enrichment statistics:")
    print(f"  - Chunks with citations: {chunks_with_citations}/{actual_count}")
    print(f"  - Total citation links: {total_citations}")
    print(f"  - Expected citations: {citation_graph.get('citation_stats', {}).get('total_citations', 0)}")

    print(f"\n✓ Validation passed")
    return True


# ============================================================================
# Query Testing Functions
# ============================================================================

def test_semantic_query(
    collection: chromadb.Collection,
    query_text: str,
    n_results: int = 3
) -> None:
    """
    Test semantic search query.

    Args:
        collection: ChromaDB collection
        query_text: Query string
        n_results: Number of results to return
    """
    print(f"\nQuery: '{query_text}'")
    print(f"-" * 80)

    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )

    for i, (chunk_id, text, metadata) in enumerate(zip(
        results['ids'][0],
        results['documents'][0],
        results['metadatas'][0]
    ), 1):
        print(f"\nResult {i}:")
        print(f"  Chunk ID: {chunk_id}")
        print(f"  Section: {metadata.get('section_title', 'N/A')}")
        print(f"  Page: {metadata.get('page_number', 'N/A')}")
        print(f"  Citations: {metadata.get('citation_count', 0)}")
        if metadata.get('cited_figures'):
            print(f"  Cited figures: {metadata.get('cited_figures')}")
        if metadata.get('cited_equations'):
            print(f"  Cited equations: {metadata.get('cited_equations')}")
        print(f"  Text preview: {text[:200]}...")


def test_citation_filter_query(
    collection: chromadb.Collection,
    citation_type: str,
    citation_id: str,
    n_results: int = 3
) -> None:
    """
    Test query with citation metadata filtering.

    Args:
        collection: ChromaDB collection
        citation_type: Type of citation (figures, tables, equations)
        citation_id: ID of the cited object
        n_results: Number of results to return
    """
    print(f"\nQuery: Chunks citing {citation_type} '{citation_id}'")
    print(f"-" * 80)

    field_name = f'cited_{citation_type}'

    # Get all chunks and filter by citation
    # Note: ChromaDB's where clause doesn't support "contains", so we get all and filter
    all_results = collection.get()

    matching_indices = []
    for i, metadata in enumerate(all_results['metadatas']):
        cited = metadata.get(field_name, '')
        if cited and citation_id in cited.split(','):
            matching_indices.append(i)

    print(f"Found {len(matching_indices)} chunks citing {citation_type} {citation_id}")

    # Show first n_results
    for idx, i in enumerate(matching_indices[:n_results], 1):
        chunk_id = all_results['ids'][i]
        text = all_results['documents'][i]
        metadata = all_results['metadatas'][i]

        print(f"\nResult {idx}:")
        print(f"  Chunk ID: {chunk_id}")
        print(f"  Section: {metadata.get('section_title', 'N/A')}")
        print(f"  Page: {metadata.get('page_number', 'N/A')}")
        print(f"  All {citation_type}: {metadata.get(field_name, 'none')}")
        print(f"  Text preview: {text[:200]}...")


def run_test_queries(collection: chromadb.Collection) -> None:
    """
    Run comprehensive test queries to validate retrieval.

    Args:
        collection: ChromaDB collection
    """
    print(f"\n{'='*80}")
    print(f"RUNNING TEST QUERIES")
    print(f"{'='*80}")

    # Test 1: Semantic search - heat transfer convection
    print(f"\n[TEST 1] Semantic search - convection")
    print(f"="*80)
    test_semantic_query(collection, "heat transfer convection", n_results=3)

    # Test 2: Semantic search - equation references
    print(f"\n[TEST 2] Semantic search - thermal conductivity")
    print(f"="*80)
    test_semantic_query(collection, "thermal conductivity equations", n_results=3)

    # Test 3: Citation filter - Figure 11
    print(f"\n[TEST 3] Citation filter - Figure 11")
    print(f"="*80)
    test_citation_filter_query(collection, "figures", "11", n_results=3)

    # Test 4: Citation filter - Equation 1
    print(f"\n[TEST 4] Citation filter - Equation 1")
    print(f"="*80)
    test_citation_filter_query(collection, "equations", "1", n_results=3)

    # Test 5: Citation filter - Table 1
    print(f"\n[TEST 5] Citation filter - Table 1")
    print(f"="*80)
    test_citation_filter_query(collection, "tables", "1", n_results=2)


# ============================================================================
# Statistics and Reporting
# ============================================================================

def print_statistics(
    chunks: List[Dict[str, Any]],
    citation_graph: Dict[str, Any],
    collection: chromadb.Collection,
    insertion_time: float
) -> None:
    """
    Print comprehensive statistics about the ingestion process.

    Args:
        chunks: Original chunks
        citation_graph: Citation graph data
        collection: ChromaDB collection
        insertion_time: Time taken for insertion (seconds)
    """
    print(f"\n{'='*80}")
    print(f"FINAL STATISTICS")
    print(f"{'='*80}")

    # Input statistics
    print(f"\nInput Data:")
    print(f"  - Total chunks: {len(chunks)}")
    print(f"  - Total characters: {sum(c['char_count'] for c in chunks):,}")
    print(f"  - Average chunk size: {sum(c['char_count'] for c in chunks) // len(chunks):,} chars")

    # Citation statistics
    stats = citation_graph.get('citation_stats', {})
    print(f"\nCitation Graph:")
    print(f"  - Total citations: {stats.get('total_citations', 0)}")
    print(f"  - Figures: {stats.get('by_type', {}).get('figure', 0)}")
    print(f"  - Tables: {stats.get('by_type', {}).get('table', 0)}")
    print(f"  - Equations: {stats.get('by_type', {}).get('equation', 0)}")
    print(f"  - Chapters: {stats.get('by_type', {}).get('chapter', 0)}")
    print(f"  - References: {stats.get('by_type', {}).get('reference', 0)}")

    # Database statistics
    print(f"\nChromaDB Collection:")
    print(f"  - Collection name: {COLLECTION_NAME}")
    print(f"  - Total documents: {collection.count()}")
    print(f"  - Insertion time: {insertion_time:.2f} seconds")
    print(f"  - Throughput: {len(chunks) / insertion_time:.2f} chunks/second")

    # Enrichment statistics
    all_results = collection.get()
    chunks_with_citations = sum(
        1 for m in all_results['metadatas'] if m.get('has_citations') == 'True'
    )
    print(f"\nMetadata Enrichment:")
    print(f"  - Chunks with citations: {chunks_with_citations}/{len(chunks)}")
    print(f"  - Enrichment rate: {chunks_with_citations / len(chunks) * 100:.1f}%")

    # Storage statistics
    print(f"\nStorage:")
    print(f"  - Database location: {CHROMA_DIR}")

    # Calculate database size
    db_size = sum(
        f.stat().st_size
        for f in CHROMA_DIR.rglob('*')
        if f.is_file()
    )
    print(f"  - Database size: {db_size / 1024 / 1024:.2f} MB")


# ============================================================================
# Main Execution
# ============================================================================

def main() -> int:
    """
    Main execution function for Pipeline 3 database ingestion test.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print(f"\n{'#'*80}")
    print(f"# PIPELINE 3 (DATABASE) TEST - JSONL TO CHROMADB INGESTION")
    print(f"{'#'*80}")
    print(f"\nTest Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Step 1: Load input data
        chunks = load_jsonl_chunks(JSONL_FILE)
        citation_graph = load_citation_graph(CITATION_GRAPH_FILE)

        if not chunks:
            print(f"\nERROR: No chunks loaded from {JSONL_FILE}")
            return 1

        # Step 2: Setup ChromaDB
        client = setup_chromadb_client()
        collection = create_collection(client)

        # Step 3: Insert chunks with citation enrichment
        start_time = time.time()
        successful, failed = insert_chunks_with_retry(collection, chunks, citation_graph)
        insertion_time = time.time() - start_time

        if failed > 0:
            print(f"\nWARNING: {failed} chunks failed to insert")

        # Step 4: Validate insertion
        if not validate_insertion(collection, len(chunks), citation_graph):
            print(f"\nERROR: Validation failed")
            return 1

        # Step 5: Run test queries
        run_test_queries(collection)

        # Step 6: Print statistics
        print_statistics(chunks, citation_graph, collection, insertion_time)

        # Success message
        print(f"\n{'='*80}")
        print(f"✓ PIPELINE 3 TEST COMPLETED SUCCESSFULLY")
        print(f"{'='*80}")
        print(f"\nAll {len(chunks)} chunks ingested into ChromaDB with citation enrichment.")
        print(f"Database location: {CHROMA_DIR}")
        print(f"\nYou can now use this collection for semantic search and retrieval.")

        return 0

    except FileNotFoundError as e:
        print(f"\nERROR: Required file not found: {e}")
        return 1
    except Exception as e:
        print(f"\nERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
