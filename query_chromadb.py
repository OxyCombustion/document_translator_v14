#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChromaDB Query Interface - Interactive query tool for Pipeline 3 database

Allows running custom queries against the ingested ChromaDB collection.

Usage:
    python3 query_chromadb.py "your query here"
    python3 query_chromadb.py "your query here" --n 5
    python3 query_chromadb.py --filter-figures "11,7"
    python3 query_chromadb.py --filter-equations "1,4"
    python3 query_chromadb.py --stats

Author: Claude Code
Date: 2025-11-19
Version: 1.0
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


# Configuration
CHROMA_DIR = Path("/home/thermodynamics/document_translator_v14/test_output_database/chromadb")
COLLECTION_NAME = "chapter_4_heat_transfer"


def get_collection() -> chromadb.Collection:
    """Get the ChromaDB collection."""
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False)
    )

    # Use same embedding function as ingestion
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function
    )

    return collection


def semantic_query(query_text: str, n_results: int = 3) -> None:
    """Run a semantic search query."""
    print(f"\nSemantic Query: '{query_text}'")
    print(f"="*80)

    collection = get_collection()
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )

    for i, (chunk_id, text, metadata) in enumerate(zip(
        results['ids'][0],
        results['documents'][0],
        results['metadatas'][0]
    ), 1):
        print(f"\n[Result {i}]")
        print(f"Chunk ID: {chunk_id}")
        print(f"Section: {metadata.get('section_title', 'N/A')}")
        print(f"Page: {metadata.get('page_number', 'N/A')}")
        print(f"Citations: {metadata.get('citation_count', 0)}")

        # Show citations if present
        if metadata.get('cited_figures'):
            print(f"Cited Figures: {metadata.get('cited_figures')}")
        if metadata.get('cited_tables'):
            print(f"Cited Tables: {metadata.get('cited_tables')}")
        if metadata.get('cited_equations'):
            print(f"Cited Equations: {metadata.get('cited_equations')}")
        if metadata.get('cited_references'):
            print(f"Cited References: {metadata.get('cited_references')}")

        print(f"\nText Preview:\n{text[:300]}...")
        print(f"-"*80)


def filter_by_citations(citation_type: str, citation_ids: List[str]) -> None:
    """Filter chunks by citation."""
    print(f"\nFilter Query: Chunks citing {citation_type} {', '.join(citation_ids)}")
    print(f"="*80)

    collection = get_collection()
    all_results = collection.get()

    field_name = f'cited_{citation_type}'

    matching_chunks = []
    for i, metadata in enumerate(all_results['metadatas']):
        cited = metadata.get(field_name, '')
        if cited:
            cited_list = cited.split(',')
            if any(cid in cited_list for cid in citation_ids):
                matching_chunks.append({
                    'id': all_results['ids'][i],
                    'text': all_results['documents'][i],
                    'metadata': metadata
                })

    print(f"Found {len(matching_chunks)} chunks\n")

    for i, chunk in enumerate(matching_chunks, 1):
        print(f"[Result {i}]")
        print(f"Chunk ID: {chunk['id']}")
        print(f"Section: {chunk['metadata'].get('section_title', 'N/A')}")
        print(f"Page: {chunk['metadata'].get('page_number', 'N/A')}")
        print(f"All {citation_type}: {chunk['metadata'].get(field_name, 'none')}")
        print(f"\nText Preview:\n{chunk['text'][:200]}...")
        print(f"-"*80)


def show_statistics() -> None:
    """Show database statistics."""
    print(f"\nDatabase Statistics")
    print(f"="*80)

    collection = get_collection()
    total_count = collection.count()

    print(f"Collection: {COLLECTION_NAME}")
    print(f"Total Chunks: {total_count}")
    print(f"Database Location: {CHROMA_DIR}")

    # Get all metadata for statistics
    all_results = collection.get()

    # Citation statistics
    chunks_with_citations = 0
    total_citations = 0
    figure_refs = set()
    table_refs = set()
    equation_refs = set()

    for metadata in all_results['metadatas']:
        if metadata.get('has_citations') == 'True':
            chunks_with_citations += 1
            total_citations += int(metadata.get('citation_count', 0))

        # Collect unique citations
        if metadata.get('cited_figures'):
            figure_refs.update(metadata['cited_figures'].split(','))
        if metadata.get('cited_tables'):
            table_refs.update(metadata['cited_tables'].split(','))
        if metadata.get('cited_equations'):
            equation_refs.update(metadata['cited_equations'].split(','))

    print(f"\nCitation Statistics:")
    print(f"  Chunks with Citations: {chunks_with_citations}/{total_count}")
    print(f"  Total Citation Links: {total_citations}")
    print(f"  Unique Figures Referenced: {len(figure_refs)}")
    print(f"  Unique Tables Referenced: {len(table_refs)}")
    print(f"  Unique Equations Referenced: {len(equation_refs)}")

    # Section distribution
    sections = {}
    for metadata in all_results['metadatas']:
        section = metadata.get('section_title', 'Unknown')
        sections[section] = sections.get(section, 0) + 1

    print(f"\nSection Distribution:")
    for section, count in sorted(sections.items(), key=lambda x: x[1], reverse=True):
        print(f"  {section}: {count} chunks")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Query ChromaDB collection from Pipeline 3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Semantic search
  python3 query_chromadb.py "radiation heat transfer" --n 5

  # Filter by figure citations
  python3 query_chromadb.py --filter-figures "11,7"

  # Filter by equation citations
  python3 query_chromadb.py --filter-equations "1,4"

  # Show statistics
  python3 query_chromadb.py --stats
        """
    )

    parser.add_argument('query', nargs='?', help='Search query text')
    parser.add_argument('-n', '--n-results', type=int, default=3,
                       help='Number of results to return (default: 3)')
    parser.add_argument('--filter-figures', type=str,
                       help='Filter by figure IDs (comma-separated)')
    parser.add_argument('--filter-tables', type=str,
                       help='Filter by table IDs (comma-separated)')
    parser.add_argument('--filter-equations', type=str,
                       help='Filter by equation IDs (comma-separated)')
    parser.add_argument('--stats', action='store_true',
                       help='Show database statistics')

    args = parser.parse_args()

    try:
        if args.stats:
            show_statistics()
        elif args.filter_figures:
            ids = [x.strip() for x in args.filter_figures.split(',')]
            filter_by_citations('figures', ids)
        elif args.filter_tables:
            ids = [x.strip() for x in args.filter_tables.split(',')]
            filter_by_citations('tables', ids)
        elif args.filter_equations:
            ids = [x.strip() for x in args.filter_equations.split(',')]
            filter_by_citations('equations', ids)
        elif args.query:
            semantic_query(args.query, args.n_results)
        else:
            parser.print_help()
            return 1

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
