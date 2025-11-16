# -*- coding: utf-8 -*-
"""
Document Manager CLI - Command-Line Interface for Document Management and Search

Provides commands for:
- Document management (list, show, stats)
- Full-text search (FTS5)
- Semantic search (ChromaDB)
- System management (ChromaDB rebuild, clear, stats)

Author: Claude Code
Date: 2025-01-22
Version: 1.0
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

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add src to path for imports
from database.document_registry import DocumentRegistry

# Optional ChromaDB import
try:
    from rag.chromadb_setup import RAGDatabase
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    RAGDatabase = None


class DocumentManagerCLI:
    """
    Command-line interface for document management and search.

    Provides access to:
    - Document registry (SQLite database)
    - FTS5 full-text search
    - ChromaDB semantic search
    """

    def __init__(self, db_path: str = "databases/document_registry.db",
                 chromadb_path: str = "rag_database"):
        """
        Initialize CLI with database connections.

        Args:
            db_path: Path to SQLite document registry
            chromadb_path: Path to ChromaDB directory
        """
        self.registry = DocumentRegistry(db_path)

        # Initialize ChromaDB if available
        if CHROMADB_AVAILABLE and RAGDatabase:
            self.chromadb = RAGDatabase(
                db_path=Path(chromadb_path),
                collection_name="engineering_content"
            )
        else:
            self.chromadb = None

    def close(self):
        """Close database connections."""
        self.registry.close()

    # =========================================================================
    # DOCUMENT MANAGEMENT COMMANDS
    # =========================================================================

    def list_documents(self, doc_type: Optional[str] = None,
                      subject: Optional[str] = None,
                      author: Optional[str] = None,
                      limit: int = 20):
        """
        List documents in the registry.

        Args:
            doc_type: Filter by document type (book, paper, manual, standard)
            subject: Filter by subject area
            author: Filter by author name
            limit: Maximum number of results
        """
        print("="*80)
        print("DOCUMENTS")
        print("="*80)
        print()

        # Find documents with filters
        docs = self.registry.find_documents(
            doc_type=doc_type,
            subject=subject,
            author=author
        )

        # Apply limit after retrieval
        if limit and len(docs) > limit:
            docs = docs[:limit]

        if not docs:
            print("No documents found matching criteria.")
            return

        print(f"Found {len(docs)} documents:\n")

        for i, doc in enumerate(docs, 1):
            print(f"{i}. {doc['title']}")
            print(f"   Doc ID: {doc['doc_id']}")
            print(f"   Type: {doc['doc_type']}")
            print(f"   Authors: {', '.join(json.loads(doc['authors']))}")
            if doc['year']:
                print(f"   Year: {doc['year']}")
            if doc['doi']:
                print(f"   DOI: {doc['doi']}")
            print()

    def show_document(self, doc_id: str):
        """
        Show detailed information about a document.

        Args:
            doc_id: Document ID to display
        """
        doc = self.registry.get_document(doc_id)

        if not doc:
            print(f"❌ Document not found: {doc_id}")
            return

        print("="*80)
        print(f"DOCUMENT: {doc['title']}")
        print("="*80)
        print()

        # Basic metadata
        print("Basic Information:")
        print(f"  Doc ID: {doc['doc_id']}")
        print(f"  Type: {doc['doc_type']}")
        print(f"  Authors: {', '.join(json.loads(doc['authors']))}")

        if doc['year']:
            print(f"  Year: {doc['year']}")
        if doc['language']:
            print(f"  Language: {doc['language']}")
        if doc['isbn']:
            print(f"  ISBN: {doc['isbn']}")
        if doc['doi']:
            print(f"  DOI: {doc['doi']}")
        if doc['zotero_key']:
            print(f"  Zotero Key: {doc['zotero_key']}")
        print()

        # Subject areas
        if doc['subject_areas']:
            print("Subject Areas:")
            for area in json.loads(doc['subject_areas']):
                print(f"  - {area}")
            print()

        # Abstract
        if doc['abstract']:
            print("Abstract:")
            print(f"  {doc['abstract'][:300]}...")
            print()

        # Type-specific metadata
        if doc['doc_type'] == 'book':
            print("Book-Specific:")
            if doc['publisher']:
                print(f"  Publisher: {doc['publisher']}")
            if doc['edition']:
                print(f"  Edition: {doc['edition']}")
            if doc['total_chapters']:
                print(f"  Total Chapters: {doc['total_chapters']}")
            print()

        elif doc['doc_type'] == 'paper':
            print("Paper-Specific:")
            if doc['journal']:
                print(f"  Journal: {doc['journal']}")
            if doc['paper_volume']:
                print(f"  Volume: {doc['paper_volume']}")
            if doc['issue']:
                print(f"  Issue: {doc['issue']}")
            if doc['pages']:
                print(f"  Pages: {doc['pages']}")
            print(f"  Peer Reviewed: {'Yes' if doc['peer_reviewed'] else 'No'}")
            print(f"  Open Access: {'Yes' if doc['open_access'] else 'No'}")
            print()

        # Find extractions for this document
        extractions = self.registry.find_extractions(doc_id=doc_id)
        if extractions:
            print(f"Extractions ({len(extractions)}):")
            for extr in extractions:
                print(f"  - {extr['extraction_id']}")
                if extr['chapter_title']:
                    print(f"    Chapter: {extr['chapter_title']}")
                print(f"    Status: {extr['status']}")
                print(f"    Date: {extr['extraction_date']}")
            print()

    def show_stats(self):
        """Show registry statistics."""
        stats = self.registry.get_statistics()

        print("="*80)
        print("REGISTRY STATISTICS")
        print("="*80)
        print()

        # Total counts
        print(f"Documents: {stats['total_documents']}")
        print(f"Extractions: {stats['total_extractions']}")

        # Calculate total objects from objects_by_type
        total_objects = sum(stats.get('objects_by_type', {}).values())
        print(f"Extracted Objects: {total_objects}")
        print()

        # Show breakdowns if available
        if stats.get('documents_by_type'):
            print("Documents by Type:")
            for doc_type, count in stats['documents_by_type'].items():
                print(f"  {doc_type}: {count}")
            print()

        if stats.get('objects_by_type'):
            print("Objects by Type:")
            for obj_type, count in stats['objects_by_type'].items():
                print(f"  {obj_type}: {count}")
            print()

    # =========================================================================
    # SEARCH COMMANDS
    # =========================================================================

    def search_fts(self, query: str, limit: int = 20):
        """
        Full-text search using FTS5.

        Args:
            query: Search query
            limit: Maximum number of results
        """
        print("="*80)
        print(f"FTS5 FULL-TEXT SEARCH: \"{query}\"")
        print("="*80)
        print()

        results = self.registry.search_full_text(query, limit=limit)

        if not results:
            print("No results found.")
            return

        print(f"Found {len(results)} results:\n")

        for i, result in enumerate(results, 1):
            print(f"{i}. {result['object_type'].upper()} - {result['object_id']}")
            print(f"   Document: {result['document_title']}")
            if result.get('chapter_title'):
                print(f"   Chapter: {result['chapter_title']}")
            print(f"   Relevance: {result['rank']:.4f}")
            print(f"   Snippet: {result['snippet']}...")
            print()

    def search_semantic(self, query: str, limit: int = 20,
                       object_type: Optional[str] = None,
                       min_quality: Optional[float] = None):
        """
        Semantic search using ChromaDB.

        Args:
            query: Search query
            limit: Maximum number of results
            object_type: Filter by type (equation, table, figure, text)
            min_quality: Minimum quality score (0.0-1.0)
        """
        print("="*80)
        print(f"CHROMADB SEMANTIC SEARCH: \"{query}\"")
        print("="*80)
        print()

        # Check if ChromaDB is available
        if not self.chromadb:
            print("❌ ChromaDB is not available. Install chromadb package to use semantic search.")
            return

        # Build metadata filter
        metadata_filter = {}
        if object_type:
            metadata_filter['type'] = object_type
        if min_quality is not None:
            metadata_filter['quality'] = {'$gte': min_quality}

        # Query ChromaDB
        results = self.chromadb.query(
            query_text=query,
            n_results=limit,
            metadata_filter=metadata_filter if metadata_filter else None
        )

        if not results or not results.get('ids'):
            print("No results found.")
            return

        print(f"Found {len(results['ids'][0])} results:\n")

        for i, (obj_id, distance, metadata, text) in enumerate(zip(
            results['ids'][0],
            results['distances'][0],
            results['metadatas'][0],
            results['documents'][0]
        ), 1):
            print(f"{i}. {metadata.get('type', 'unknown').upper()} - {obj_id}")
            print(f"   Similarity: {1 - distance:.4f}")
            print(f"   Quality: {metadata.get('quality', 'N/A')}")
            print(f"   Domain: {metadata.get('domain', 'N/A')}")
            print(f"   Text: {text[:100]}...")
            print()

    # =========================================================================
    # CHROMADB MANAGEMENT COMMANDS
    # =========================================================================

    def chromadb_stats(self):
        """Show ChromaDB statistics."""
        if not self.chromadb:
            print("❌ ChromaDB is not available. Install chromadb package to use this feature.")
            return

        stats = self.chromadb.get_stats()

        print("="*80)
        print("CHROMADB STATISTICS")
        print("="*80)
        print()

        print(f"Collection: {stats['collection_name']}")
        print(f"Total Objects: {stats['count']}")
        print()

        if stats['by_type']:
            print("Objects by Type:")
            for obj_type, count in stats['by_type'].items():
                print(f"  {obj_type}: {count}")
            print()

        if stats['by_domain']:
            print("Objects by Domain:")
            for domain, count in stats['by_domain'].items():
                print(f"  {domain}: {count}")
            print()

        print(f"Sample IDs ({len(stats['sample_ids'])} shown):")
        for obj_id in stats['sample_ids']:
            print(f"  - {obj_id}")

    def chromadb_rebuild(self, jsonl_file: str, batch_size: int = 10):
        """
        Rebuild ChromaDB index from JSONL file.

        Args:
            jsonl_file: Path to JSONL package file
            batch_size: Batch size for ingestion
        """
        print("="*80)
        print(f"REBUILDING CHROMADB INDEX")
        print("="*80)
        print()

        if not self.chromadb:
            print("❌ ChromaDB is not available. Install chromadb package to use this feature.")
            return

        jsonl_path = Path(jsonl_file)
        if not jsonl_path.exists():
            print(f"❌ JSONL file not found: {jsonl_file}")
            return

        print(f"Source: {jsonl_file}")
        print(f"Batch size: {batch_size}")
        print()

        # Clear existing data
        print("Clearing existing data...")
        self.chromadb.reset()
        print("✅ Cleared\n")

        # Ingest new data
        print("Ingesting JSONL...")
        try:
            count = self.chromadb.ingest_jsonl(jsonl_path, batch_size=batch_size)
            print(f"✅ Indexed {count} objects successfully")
        except Exception as e:
            print(f"❌ Ingestion failed: {e}")

    def chromadb_clear(self):
        """Clear ChromaDB database."""
        print("="*80)
        print("CLEARING CHROMADB DATABASE")
        print("="*80)
        print()

        if not self.chromadb:
            print("❌ ChromaDB is not available. Install chromadb package to use this feature.")
            return

        # Confirm with user
        response = input("Are you sure you want to clear ChromaDB? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return

        self.chromadb.reset()
        print("✅ ChromaDB cleared successfully")


def create_parser():
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        prog='docmgr',
        description='Document Manager CLI - Manage documents and search content',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all documents
  docmgr docs list

  # Show document details
  docmgr docs show doc_123

  # Show statistics
  docmgr docs stats

  # Full-text search
  docmgr search fts "thermal conductivity"

  # Semantic search
  docmgr search semantic "heat transfer equations" --type equation

  # ChromaDB statistics
  docmgr chromadb stats

  # Rebuild ChromaDB index
  docmgr chromadb rebuild results/chromadb_package.jsonl
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # -------------------------------------------------------------------------
    # DOCS COMMAND GROUP
    # -------------------------------------------------------------------------

    docs_parser = subparsers.add_parser('docs', help='Document management commands')
    docs_subparsers = docs_parser.add_subparsers(dest='docs_command')

    # docs list
    list_parser = docs_subparsers.add_parser('list', help='List documents')
    list_parser.add_argument('--type', help='Filter by document type (book, paper, manual, standard)')
    list_parser.add_argument('--subject', help='Filter by subject area')
    list_parser.add_argument('--author', help='Filter by author name')
    list_parser.add_argument('--limit', type=int, default=20, help='Maximum results (default: 20)')

    # docs show
    show_parser = docs_subparsers.add_parser('show', help='Show document details')
    show_parser.add_argument('doc_id', help='Document ID to display')

    # docs stats
    docs_subparsers.add_parser('stats', help='Show registry statistics')

    # -------------------------------------------------------------------------
    # SEARCH COMMAND GROUP
    # -------------------------------------------------------------------------

    search_parser = subparsers.add_parser('search', help='Search commands')
    search_subparsers = search_parser.add_subparsers(dest='search_command')

    # search fts
    fts_parser = search_subparsers.add_parser('fts', help='Full-text search (FTS5)')
    fts_parser.add_argument('query', help='Search query')
    fts_parser.add_argument('--limit', type=int, default=20, help='Maximum results (default: 20)')

    # search semantic
    semantic_parser = search_subparsers.add_parser('semantic', help='Semantic search (ChromaDB)')
    semantic_parser.add_argument('query', help='Search query')
    semantic_parser.add_argument('--limit', type=int, default=20, help='Maximum results (default: 20)')
    semantic_parser.add_argument('--type', help='Filter by object type (equation, table, figure, text)')
    semantic_parser.add_argument('--quality', type=float, help='Minimum quality score (0.0-1.0)')

    # -------------------------------------------------------------------------
    # CHROMADB COMMAND GROUP
    # -------------------------------------------------------------------------

    chromadb_parser = subparsers.add_parser('chromadb', help='ChromaDB management commands')
    chromadb_subparsers = chromadb_parser.add_subparsers(dest='chromadb_command')

    # chromadb stats
    chromadb_subparsers.add_parser('stats', help='Show ChromaDB statistics')

    # chromadb rebuild
    rebuild_parser = chromadb_subparsers.add_parser('rebuild', help='Rebuild ChromaDB index from JSONL')
    rebuild_parser.add_argument('jsonl_file', help='Path to JSONL package file')
    rebuild_parser.add_argument('--batch-size', type=int, default=10, help='Batch size (default: 10)')

    # chromadb clear
    chromadb_subparsers.add_parser('clear', help='Clear ChromaDB database')

    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize CLI
    cli = DocumentManagerCLI()

    try:
        # Execute command
        if args.command == 'docs':
            if args.docs_command == 'list':
                cli.list_documents(
                    doc_type=args.type,
                    subject=args.subject,
                    author=args.author,
                    limit=args.limit
                )
            elif args.docs_command == 'show':
                cli.show_document(args.doc_id)
            elif args.docs_command == 'stats':
                cli.show_stats()
            else:
                parser.parse_args(['docs', '--help'])

        elif args.command == 'search':
            if args.search_command == 'fts':
                cli.search_fts(args.query, limit=args.limit)
            elif args.search_command == 'semantic':
                cli.search_semantic(
                    args.query,
                    limit=args.limit,
                    object_type=args.type,
                    min_quality=args.quality
                )
            else:
                parser.parse_args(['search', '--help'])

        elif args.command == 'chromadb':
            if args.chromadb_command == 'stats':
                cli.chromadb_stats()
            elif args.chromadb_command == 'rebuild':
                cli.chromadb_rebuild(args.jsonl_file, batch_size=args.batch_size)
            elif args.chromadb_command == 'clear':
                cli.chromadb_clear()
            else:
                parser.parse_args(['chromadb', '--help'])

        else:
            parser.print_help()

    finally:
        cli.close()


if __name__ == '__main__':
    main()
