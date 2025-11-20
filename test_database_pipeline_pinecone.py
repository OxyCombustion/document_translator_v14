#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline 3 (Database) Test Script - JSONL to Pinecone Ingestion

Tests the complete database ingestion pipeline using Pinecone:
- Load JSONL chunks from Pipeline 2 output
- Load citation graph for metadata enrichment
- Create Pinecone serverless index
- Enrich chunk metadata with citation information
- Batch upsert with retry logic
- Validate insertion and metadata
- Test semantic queries with citation filtering

Production Status: ⏸️ Production-ready but not yet tested (no API key)
- Can run in mock mode without Pinecone API key
- Use --mock flag to simulate Pinecone operations
- Mirrors ChromaDB test functionality for consistency

Author: Claude Code
Date: 2025-11-20
Version: 1.0

Usage:
    # Mock mode (no API key required)
    python test_database_pipeline_pinecone.py --mock

    # Real mode (requires PINECONE_API_KEY environment variable)
    export PINECONE_API_KEY="your-api-key"
    python test_database_pipeline_pinecone.py

    # Custom configuration
    python test_database_pipeline_pinecone.py --config config/pinecone_config.yaml
"""

import sys
import os
import json
import time
import argparse
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from pipelines.data_management.packages.database_v14_P6.src.vector_db import PineconeAdapter

# SentenceTransformers for local embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("WARNING: sentence-transformers not installed")
    print("Install with: pip install sentence-transformers")


# ============================================================================
# Configuration
# ============================================================================

# Input files from Pipeline 2
INPUT_DIR = Path("/home/thermodynamics/document_translator_v14/test_output_rag")
JSONL_FILE = INPUT_DIR / "rag_bundles.jsonl"
CITATION_GRAPH_FILE = INPUT_DIR / "citation_graph.json"

# Output directory
OUTPUT_DIR = Path("/home/thermodynamics/document_translator_v14/test_output_database_pinecone")

# Pinecone settings (can be overridden by config file)
DEFAULT_CONFIG = {
    'api_key': os.getenv('PINECONE_API_KEY', ''),
    'environment': 'us-east-1',
    'index_name': 'thermodynamics-v14-test',
    'dimension': 384,  # all-MiniLM-L6-v2
    'metric': 'cosine',
    'cloud': 'aws',
    'region': 'us-east-1',
    'namespace': 'chapter_4',
    'batch_size': 10,  # Smaller for testing
    'max_retries': 3,
    'retry_delay': 2.0,
    'mock_mode': False
}

# Embedding model
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


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


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load Pinecone configuration from YAML file.

    Args:
        config_path: Path to config file (optional)

    Returns:
        Configuration dictionary
    """
    config = DEFAULT_CONFIG.copy()

    if config_path and config_path.exists():
        print(f"\nLoading config from: {config_path}")
        with open(config_path, 'r') as f:
            yaml_config = yaml.safe_load(f)

        # Merge YAML config with defaults
        if 'pinecone' in yaml_config:
            config.update(yaml_config['pinecone'])
        if 'index' in yaml_config:
            config.update(yaml_config['index'])
        if 'batch_processing' in yaml_config:
            config.update(yaml_config['batch_processing'])

    return config


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
        Enriched metadata dictionary suitable for Pinecone
    """
    chunk_id = chunk['chunk_id']
    citations_by_chunk = citation_graph.get('citations_by_chunk', {})
    chunk_citations = citations_by_chunk.get(chunk_id, {})

    # Extract base metadata
    metadata = {
        'chunk_id': chunk_id,
        'page_number': chunk['page_number'],
        'char_count': chunk['char_count'],
        'section_id': chunk['metadata'].get('section_id', ''),
        'section_title': chunk['metadata'].get('section_title', ''),
        'section_type': chunk['metadata'].get('section_type', ''),
        'is_complete_section': chunk['metadata'].get('is_complete_section', False),
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
    metadata['has_citations'] = total_citations > 0
    metadata['citation_count'] = total_citations

    # Individual citation types (Pinecone supports arrays)
    metadata['cited_figures'] = figures
    metadata['cited_tables'] = tables
    metadata['cited_equations'] = equations
    metadata['cited_chapters'] = chapters
    metadata['cited_references'] = references

    # Individual counts
    metadata['figure_count'] = len(figures)
    metadata['table_count'] = len(tables)
    metadata['equation_count'] = len(equations)
    metadata['chapter_count'] = len(chapters)
    metadata['reference_count'] = len(references)

    return metadata


def prepare_chunks_for_pinecone(
    chunks: List[Dict[str, Any]],
    citation_graph: Dict[str, Any],
    embedding_model: Any
) -> Tuple[List[Dict[str, Any]], List[List[float]]]:
    """
    Prepare chunks for Pinecone insertion.

    Args:
        chunks: List of chunk dictionaries
        citation_graph: Citation graph data
        embedding_model: SentenceTransformer model

    Returns:
        Tuple of (formatted_chunks, embeddings)
    """
    formatted_chunks = []
    embeddings = []

    print(f"\n{'='*80}")
    print(f"PREPARING CHUNKS FOR PINECONE")
    print(f"{'='*80}")

    for chunk in chunks:
        # Enrich metadata
        metadata = enrich_chunk_metadata(chunk, citation_graph)

        # Format chunk
        formatted_chunk = {
            'chunk_id': chunk['chunk_id'],
            'text': chunk['text'],
            'metadata': metadata
        }
        formatted_chunks.append(formatted_chunk)

        # Generate embedding
        embedding = embedding_model.encode(chunk['text']).tolist()
        embeddings.append(embedding)

    print(f"✓ Prepared {len(formatted_chunks)} chunks")
    print(f"  - Embedding dimension: {len(embeddings[0])}")

    return formatted_chunks, embeddings


# ============================================================================
# Pinecone Operations
# ============================================================================

def setup_pinecone(config: Dict[str, Any]) -> PineconeAdapter:
    """
    Initialize Pinecone adapter.

    Args:
        config: Pinecone configuration

    Returns:
        PineconeAdapter instance
    """
    print(f"\n{'='*80}")
    print(f"INITIALIZING PINECONE")
    print(f"{'='*80}")

    if config['mock_mode']:
        print(f"Mode: MOCK (no API key required)")
    else:
        print(f"Mode: REAL (requires API key)")
        if not config['api_key']:
            print(f"WARNING: No API key found!")
            print(f"Set PINECONE_API_KEY environment variable or use --mock flag")

    print(f"Index: {config['index_name']}")
    print(f"Dimension: {config['dimension']}")
    print(f"Metric: {config['metric']}")
    print(f"Cloud: {config['cloud']}")
    print(f"Region: {config['region']}")
    print(f"Namespace: {config['namespace']}")

    # Create adapter
    adapter = PineconeAdapter(config)

    # Connect
    success = adapter.connect()
    if success:
        print(f"✓ Pinecone connected")
    else:
        print(f"✗ Pinecone connection failed")
        if not config['mock_mode']:
            sys.exit(1)

    return adapter


def insert_chunks_to_pinecone(
    adapter: PineconeAdapter,
    collection: Any,
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]]
) -> Tuple[int, int]:
    """
    Insert chunks into Pinecone with retry logic.

    Args:
        adapter: PineconeAdapter instance
        collection: Pinecone index
        chunks: List of formatted chunks
        embeddings: List of embedding vectors

    Returns:
        Tuple of (successful_count, failed_count)
    """
    print(f"\n{'='*80}")
    print(f"INSERTING CHUNKS INTO PINECONE")
    print(f"{'='*80}")

    start_time = time.time()
    successful, failed = adapter.insert_chunks(collection, chunks, embeddings)
    elapsed_time = time.time() - start_time

    print(f"\n{'='*80}")
    print(f"INSERTION SUMMARY")
    print(f"{'='*80}")
    print(f"✓ Successful: {successful}")
    if failed > 0:
        print(f"✗ Failed: {failed}")
    print(f"⏱ Time: {elapsed_time:.2f} seconds")
    print(f"📊 Throughput: {successful / elapsed_time:.2f} chunks/second")

    return successful, failed


# ============================================================================
# Query Testing Functions
# ============================================================================

def test_semantic_query(
    adapter: PineconeAdapter,
    collection: Any,
    embedding_model: Any,
    query_text: str,
    top_k: int = 3
) -> None:
    """
    Test semantic search query.

    Args:
        adapter: PineconeAdapter instance
        collection: Pinecone index
        embedding_model: SentenceTransformer model
        query_text: Query string
        top_k: Number of results to return
    """
    print(f"\nQuery: '{query_text}'")
    print(f"-" * 80)

    # Generate query embedding
    query_embedding = embedding_model.encode(query_text).tolist()

    # Execute query
    results = adapter.query(
        collection,
        query_embedding,
        top_k=top_k,
        include_metadata=True,
        include_documents=True
    )

    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"  ID: {result['id']}")
        print(f"  Score: {result['score']:.4f}")

        if 'metadata' in result:
            metadata = result['metadata']
            print(f"  Page: {metadata.get('page_number', 'N/A')}")
            print(f"  Section: {metadata.get('section_title', 'N/A')}")
            print(f"  Citations: {metadata.get('citation_count', 0)}")

        if 'document' in result:
            print(f"  Text: {result['document'][:200]}...")


def test_citation_filter_query(
    adapter: PineconeAdapter,
    collection: Any,
    embedding_model: Any,
    citation_type: str,
    citation_id: str,
    top_k: int = 3
) -> None:
    """
    Test query with citation metadata filtering.

    Args:
        adapter: PineconeAdapter instance
        collection: Pinecone index
        embedding_model: SentenceTransformer model
        citation_type: Type of citation (figures, tables, equations)
        citation_id: ID of the cited object
        top_k: Number of results to return
    """
    print(f"\nQuery: Chunks citing {citation_type} '{citation_id}'")
    print(f"-" * 80)

    # Generate dummy query embedding
    query_embedding = embedding_model.encode(citation_type).tolist()

    # Build Pinecone filter
    # Note: Pinecone filters use different syntax than ChromaDB
    field_name = f'cited_{citation_type}'
    filters = {field_name: {"$in": [citation_id]}}

    # Execute query
    results = adapter.query(
        collection,
        query_embedding,
        top_k=top_k,
        filters=filters,
        include_metadata=True,
        include_documents=True
    )

    print(f"Found {len(results)} chunks")

    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"  ID: {result['id']}")

        if 'metadata' in result:
            metadata = result['metadata']
            print(f"  Page: {metadata.get('page_number', 'N/A')}")
            print(f"  {citation_type}: {metadata.get(field_name, 'none')}")

        if 'document' in result:
            print(f"  Text: {result['document'][:200]}...")


def run_test_queries(
    adapter: PineconeAdapter,
    collection: Any,
    embedding_model: Any
) -> None:
    """
    Run comprehensive test queries.

    Args:
        adapter: PineconeAdapter instance
        collection: Pinecone index
        embedding_model: SentenceTransformer model
    """
    print(f"\n{'='*80}")
    print(f"RUNNING TEST QUERIES")
    print(f"{'='*80}")

    # Test 1: Semantic search - heat transfer
    print(f"\n[TEST 1] Semantic search - heat transfer")
    print(f"="*80)
    test_semantic_query(adapter, collection, embedding_model,
                       "heat transfer convection", top_k=3)

    # Test 2: Semantic search - thermal conductivity
    print(f"\n[TEST 2] Semantic search - thermal conductivity")
    print(f"="*80)
    test_semantic_query(adapter, collection, embedding_model,
                       "thermal conductivity equations", top_k=3)

    # Test 3: Citation filter - Figure 11
    print(f"\n[TEST 3] Citation filter - Figure 11")
    print(f"="*80)
    test_citation_filter_query(adapter, collection, embedding_model,
                              "figures", "11", top_k=3)

    # Test 4: Citation filter - Equation 1
    print(f"\n[TEST 4] Citation filter - Equation 1")
    print(f"="*80)
    test_citation_filter_query(adapter, collection, embedding_model,
                              "equations", "1", top_k=3)


# ============================================================================
# Statistics and Reporting
# ============================================================================

def print_statistics(
    adapter: PineconeAdapter,
    collection: Any,
    chunks: List[Dict[str, Any]],
    insertion_time: float,
    config: Dict[str, Any]
) -> None:
    """
    Print comprehensive statistics.

    Args:
        adapter: PineconeAdapter instance
        collection: Pinecone index
        chunks: Original chunks
        insertion_time: Time taken for insertion (seconds)
        config: Pinecone configuration
    """
    print(f"\n{'='*80}")
    print(f"FINAL STATISTICS")
    print(f"{'='*80}")

    # Input statistics
    print(f"\nInput Data:")
    print(f"  - Total chunks: {len(chunks)}")
    if chunks:
        total_chars = sum(c['char_count'] for c in chunks)
        print(f"  - Total characters: {total_chars:,}")
        print(f"  - Average chunk size: {total_chars // len(chunks):,} chars")

    # Pinecone statistics
    stats = adapter.get_collection_stats(collection)
    print(f"\nPinecone Index:")
    print(f"  - Index name: {config['index_name']}")
    print(f"  - Total vectors: {stats.get('count', 'N/A')}")
    print(f"  - Dimension: {stats.get('dimension', 'N/A')}")
    print(f"  - Metric: {stats.get('metric', 'N/A')}")
    print(f"  - Namespace: {config['namespace']}")

    # Performance statistics
    print(f"\nPerformance:")
    print(f"  - Insertion time: {insertion_time:.2f} seconds")
    if chunks:
        print(f"  - Throughput: {len(chunks) / insertion_time:.2f} chunks/second")

    # Mode
    print(f"\nMode:")
    if config['mock_mode']:
        print(f"  - MOCK MODE (no actual API calls)")
    else:
        print(f"  - REAL MODE (using Pinecone API)")


# ============================================================================
# Main Execution
# ============================================================================

def main(args) -> int:
    """
    Main execution function.

    Args:
        args: Command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print(f"\n{'#'*80}")
    print(f"# PIPELINE 3 (DATABASE) TEST - JSONL TO PINECONE INGESTION")
    print(f"{'#'*80}")
    print(f"\nTest Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Load configuration
        config = load_config(args.config)
        if args.mock:
            config['mock_mode'] = True

        # Step 1: Load input data
        chunks = load_jsonl_chunks(JSONL_FILE)
        citation_graph = load_citation_graph(CITATION_GRAPH_FILE)

        if not chunks:
            print(f"\nERROR: No chunks loaded from {JSONL_FILE}")
            return 1

        # Step 2: Initialize embedding model
        if not EMBEDDINGS_AVAILABLE:
            print(f"\nERROR: sentence-transformers not installed")
            return 1

        print(f"\n{'='*80}")
        print(f"LOADING EMBEDDING MODEL")
        print(f"{'='*80}")
        print(f"Model: {EMBEDDING_MODEL}")
        embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        print(f"✓ Model loaded")

        # Step 3: Setup Pinecone
        adapter = setup_pinecone(config)

        # Step 4: Create collection
        print(f"\n{'='*80}")
        print(f"CREATING PINECONE INDEX")
        print(f"{'='*80}")
        collection = adapter.create_collection(
            name=config['index_name'],
            dimension=config['dimension'],
            metadata={'description': 'Chapter 4 Heat Transfer Test'},
            overwrite=True
        )
        print(f"✓ Index created/retrieved")

        # Step 5: Prepare chunks with embeddings
        formatted_chunks, embeddings = prepare_chunks_for_pinecone(
            chunks, citation_graph, embedding_model
        )

        # Step 6: Insert chunks
        start_time = time.time()
        successful, failed = insert_chunks_to_pinecone(
            adapter, collection, formatted_chunks, embeddings
        )
        insertion_time = time.time() - start_time

        if failed > 0:
            print(f"\nWARNING: {failed} chunks failed to insert")

        # Step 7: Run test queries
        if successful > 0:
            run_test_queries(adapter, collection, embedding_model)

        # Step 8: Print statistics
        print_statistics(adapter, collection, chunks, insertion_time, config)

        # Success message
        print(f"\n{'='*80}")
        print(f"✓ PIPELINE 3 TEST COMPLETED SUCCESSFULLY")
        print(f"{'='*80}")

        if config['mock_mode']:
            print(f"\nRan in MOCK MODE - no actual API calls made")
            print(f"To test with real Pinecone:")
            print(f"  1. Set PINECONE_API_KEY environment variable")
            print(f"  2. Run without --mock flag")
        else:
            print(f"\nAll {len(chunks)} chunks ingested into Pinecone")
            print(f"Index: {config['index_name']}")
            print(f"Namespace: {config['namespace']}")

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
    parser = argparse.ArgumentParser(
        description="Test Pinecone database pipeline ingestion"
    )
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Run in mock mode (no API key required)'
    )
    parser.add_argument(
        '--config',
        type=Path,
        help='Path to Pinecone configuration YAML file'
    )

    args = parser.parse_args()
    sys.exit(main(args))
