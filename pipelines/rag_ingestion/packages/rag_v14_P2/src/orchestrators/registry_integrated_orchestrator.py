# -*- coding: utf-8 -*-
"""
Registry-Integrated Pipeline Orchestrator

This extends the unified pipeline orchestrator to automatically register
and organize all extractions in the document registry system.

Workflow:
1. Run unified extraction pipeline (unchanged)
2. Extract document metadata (PDF + Zotero + filename + user)
3. Register document in database (if not already registered)
4. Register extraction with PDF hash and timestamps
5. Move files to organized directory structure
6. Index objects in database for search
7. Index for FTS5 full-text search
8. Index for ChromaDB semantic search
9. Generate reports and statistics

Author: Claude Code
Date: 2025-01-21
Version: 1.1 (ChromaDB semantic search integration)
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

from pathlib import Path
from typing import Dict, Optional, Any
import json
from datetime import datetime

# Import existing orchestrator
from orchestration.unified_pipeline_orchestrator import UnifiedPipelineOrchestrator

# Import document registry system
from database.document_registry import DocumentRegistry, DocumentMetadata, ExtractionMetadata, create_book_metadata
from database.metadata_extractor import MetadataExtractor
from database.directory_organizer import DirectoryOrganizer

# Import ChromaDB for semantic search
from rag.chromadb_setup import RAGDatabase


class RegistryIntegratedOrchestrator:
    """
    Orchestrator that integrates extraction pipeline with document registry.

    This class wraps the UnifiedPipelineOrchestrator and adds automatic
    document registration and organization.
    """

    def __init__(self,
                 model_path: str,
                 user_metadata: Optional[Dict[str, Any]] = None,
                 zotero_db_path: Optional[Path] = None):
        """
        Initialize registry-integrated orchestrator.

        Args:
            model_path: Path to DocLayout-YOLO model
            user_metadata: Optional user-provided metadata
            zotero_db_path: Optional path to Zotero database
        """
        self.model_path = model_path
        self.user_metadata = user_metadata or {}

        # Initialize registry systems
        self.registry = DocumentRegistry()
        self.metadata_extractor = MetadataExtractor(zotero_db_path)
        self.dir_organizer = DirectoryOrganizer()

        # Initialize ChromaDB for semantic search
        self.chromadb = RAGDatabase(
            db_path=Path("rag_database"),
            collection_name="engineering_content"
        )

        # Temporary output directory for unified pipeline
        self.temp_output = Path("results/temp_unified_pipeline")

    def process_document(self,
                        pdf_path: Path,
                        doc_type: str = 'book',
                        auto_detect_metadata: bool = True) -> Dict[str, Any]:
        """
        Process document with complete extraction and registration.

        Args:
            pdf_path: Path to PDF file
            doc_type: Document type ('book', 'paper', 'manual', 'standard')
            auto_detect_metadata: If True, extract metadata from PDF/Zotero/filename

        Returns:
            Dictionary with extraction_id, doc_id, output_directory, and statistics
        """
        print("\n" + "="*80)
        print("REGISTRY-INTEGRATED PIPELINE")
        print("="*80)
        print(f"PDF: {pdf_path}")
        print(f"Document Type: {doc_type}")
        print()

        # =================================================================
        # PHASE 1: EXTRACT CONTENT (UNIFIED PIPELINE)
        # =================================================================

        print("="*80)
        print("PHASE 1: UNIFIED EXTRACTION PIPELINE")
        print("="*80)
        print()

        # Run unified pipeline to temporary directory
        orchestrator = UnifiedPipelineOrchestrator(
            model_path=self.model_path,
            output_dir=self.temp_output,
            clean_before_run=True
        )

        results = orchestrator.process_document(pdf_path)

        print(f"\n✅ Extraction complete:")
        print(f"   Equations: {results['extraction_counts']['equations']}")
        print(f"   Tables: {results['extraction_counts']['tables']}")
        print(f"   Figures: {results['extraction_counts']['figures']}")
        print(f"   Processing time: {results['timing']['total']:.1f}s")
        print()

        # =================================================================
        # PHASE 2: EXTRACT METADATA
        # =================================================================

        print("="*80)
        print("PHASE 2: METADATA EXTRACTION")
        print("="*80)
        print()

        if auto_detect_metadata:
            # Extract from multiple sources
            complete_meta = self.metadata_extractor.extract_complete_metadata(
                pdf_path,
                user_metadata=self.user_metadata
            )
        else:
            complete_meta = self.user_metadata

        # Compute PDF hash for change detection
        pdf_hash = DocumentRegistry.compute_pdf_hash(pdf_path)
        print(f"📄 PDF hash: {pdf_hash[:16]}...")
        print()

        # =================================================================
        # PHASE 3: REGISTER DOCUMENT
        # =================================================================

        print("="*80)
        print("PHASE 3: DOCUMENT REGISTRATION")
        print("="*80)
        print()

        # Check if document already registered
        existing_docs = self.registry.find_documents(
            doc_type=doc_type,
            title=complete_meta.get('title')
        )

        if existing_docs and len(existing_docs) > 0:
            doc_id = existing_docs[0]['doc_id']
            print(f"✅ Document already registered: {doc_id}")
            print(f"   Title: {existing_docs[0]['title']}")
        else:
            # Create new document metadata
            if doc_type == 'book':
                doc_metadata = create_book_metadata(
                    title=complete_meta.get('title', pdf_path.stem),
                    authors=complete_meta.get('authors', []),
                    year=complete_meta.get('year'),
                    edition=complete_meta.get('edition'),
                    publisher=complete_meta.get('publisher'),
                    isbn=complete_meta.get('isbn'),
                    total_chapters=complete_meta.get('total_chapters'),
                    subject_areas=complete_meta.get('subject_areas', []),
                    abstract=complete_meta.get('abstract'),
                    keywords=complete_meta.get('keywords', [])
                )
            else:
                # Generic document metadata
                doc_metadata = DocumentMetadata(
                    doc_id=DocumentRegistry.generate_doc_id(
                        title=complete_meta.get('title', pdf_path.stem),
                        year=complete_meta.get('year')
                    ),
                    doc_type=doc_type,
                    title=complete_meta.get('title', pdf_path.stem),
                    authors=complete_meta.get('authors', []),
                    year=complete_meta.get('year'),
                    doi=complete_meta.get('doi'),
                    subject_areas=complete_meta.get('subject_areas', [])
                )

            doc_id = self.registry.register_document(doc_metadata)
            print(f"✅ New document registered: {doc_id}")
            print(f"   Title: {doc_metadata.title}")

            # Save document metadata to file
            self.dir_organizer.save_document_metadata(doc_type, doc_id, {
                'doc_id': doc_id,
                'title': complete_meta.get('title', pdf_path.stem),
                'authors': complete_meta.get('authors', []),
                'year': complete_meta.get('year'),
                'doc_type': doc_type
            })

        print()

        # =================================================================
        # PHASE 4: REGISTER EXTRACTION
        # =================================================================

        print("="*80)
        print("PHASE 4: EXTRACTION REGISTRATION")
        print("="*80)
        print()

        # Generate extraction ID
        extraction_id = DocumentRegistry.generate_extraction_id(
            doc_id,
            chapter_number=complete_meta.get('chapter_number')
        )

        # Determine organized directory
        extraction_dir = self.dir_organizer.get_extraction_directory(
            doc_type=doc_type,
            doc_id=doc_id,
            chapter_number=complete_meta.get('chapter_number'),
            chapter_title=complete_meta.get('chapter_title'),
            section_id=complete_meta.get('section_id')
        )

        print(f"Extraction ID: {extraction_id}")
        print(f"Output directory: {extraction_dir}")
        print()

        # Create extraction metadata
        extraction_metadata = ExtractionMetadata(
            extraction_id=extraction_id,
            doc_id=doc_id,
            chapter_number=complete_meta.get('chapter_number'),
            chapter_title=complete_meta.get('chapter_title'),
            pdf_file=str(pdf_path),
            pdf_hash=pdf_hash,
            output_directory=str(extraction_dir),
            extraction_date=datetime.now().isoformat(),
            pipeline_version='v13.2.0',  # Registry-integrated version
            status='complete',
            processing_time_seconds=results['timing']['total']
        )

        self.registry.register_extraction(extraction_metadata)
        print("✅ Extraction registered in database")
        print()

        # =================================================================
        # PHASE 5: ORGANIZE FILES
        # =================================================================

        print("="*80)
        print("PHASE 5: FILE ORGANIZATION")
        print("="*80)
        print()

        print(f"Moving files from: {self.temp_output}")
        print(f"              to: {extraction_dir}")
        print()

        # Move extraction files to organized structure
        self.dir_organizer.move_extraction_files(
            source_dir=self.temp_output,
            extraction_dir=extraction_dir
        )

        # Save extraction metadata
        self.dir_organizer.save_extraction_metadata(extraction_dir, {
            'extraction_id': extraction_id,
            'doc_id': doc_id,
            'chapter_number': complete_meta.get('chapter_number'),
            'chapter_title': complete_meta.get('chapter_title'),
            'pdf_file': str(pdf_path),
            'pdf_hash': pdf_hash,
            'extraction_date': extraction_metadata.extraction_date,
            'pipeline_version': extraction_metadata.pipeline_version,
            'stats': {
                'equations_extracted': results['extraction_counts']['equations'],
                'tables_extracted': results['extraction_counts']['tables'],
                'figures_extracted': results['extraction_counts']['figures'],
                'text_blocks_extracted': results['extraction_counts'].get('text', 0)
            }
        })

        print()

        # =================================================================
        # PHASE 6: INDEX OBJECTS
        # =================================================================

        print("="*80)
        print("PHASE 6: DATABASE INDEXING")
        print("="*80)
        print()

        # Index equations
        equations_indexed = 0
        equations_dir = extraction_dir / 'equations'
        if equations_dir.exists():
            equation_files = sorted(equations_dir.glob('eq_*.png'))
            print(f"Indexing {len(equation_files)} equations...")

            for eq_file in equation_files:
                # Parse equation number from filename
                eq_num = eq_file.stem.replace('eq_', '')

                self.registry.add_extracted_object(
                    extraction_id=extraction_id,
                    object_type='equation',
                    page_number=1,  # Would need to parse from zone metadata
                    bbox=[0, 0, 100, 100],  # Would need to get from zone metadata
                    object_number=eq_num,
                    file_path=f"equations/{eq_file.name}",
                    confidence=0.95
                )
                equations_indexed += 1

            print(f"✅ Indexed {equations_indexed} equations")

        # Index tables
        tables_indexed = 0
        tables_dir = extraction_dir / 'tables'
        if tables_dir.exists():
            table_files = sorted(tables_dir.glob('table_*.csv'))
            print(f"Indexing {len(table_files)} tables...")

            for table_file in table_files:
                # Parse table number from filename
                table_num = table_file.stem.replace('table_', '')

                self.registry.add_extracted_object(
                    extraction_id=extraction_id,
                    object_type='table',
                    page_number=1,
                    bbox=[0, 0, 100, 100],
                    object_number=table_num,
                    file_path=f"tables/{table_file.name}",
                    confidence=0.95
                )
                tables_indexed += 1

            print(f"✅ Indexed {tables_indexed} tables")

        # Index figures
        figures_indexed = 0
        figures_dir = extraction_dir / 'figures'
        if figures_dir.exists():
            figure_files = sorted(figures_dir.glob('fig_*.png'))
            print(f"Indexing {len(figure_files)} figures...")

            for fig_file in figure_files:
                # Use full filename as figure number
                fig_num = fig_file.stem.replace('fig_', '')

                self.registry.add_extracted_object(
                    extraction_id=extraction_id,
                    object_type='figure',
                    page_number=1,
                    bbox=[0, 0, 100, 100],
                    object_number=fig_num,
                    file_path=f"figures/{fig_file.name}",
                    confidence=0.95
                )
                figures_indexed += 1

            print(f"✅ Indexed {figures_indexed} figures")

        print()

        # =================================================================
        # PHASE 7: ENABLE SEARCH
        # =================================================================

        print("="*80)
        print("PHASE 7: FULL-TEXT SEARCH INDEXING")
        print("="*80)
        print()

        # Load text content for indexing
        text_dir = extraction_dir / 'text'
        combined_text = ""

        if text_dir.exists():
            for text_file in text_dir.glob('*.txt'):
                try:
                    with open(text_file, 'r', encoding='utf-8') as f:
                        combined_text += f.read() + "\n"
                except:
                    pass

        # Index for full-text search
        chapter_title_full = f"Chapter {complete_meta.get('chapter_number', '')}: {complete_meta.get('chapter_title', '')}"

        self.registry.index_extraction_for_search(
            extraction_id=extraction_id,
            chapter_title=chapter_title_full,
            text_content=combined_text if combined_text else "Content indexed"
        )

        print("✅ Extraction indexed for full-text search")
        print()

        # =================================================================
        # PHASE 8: SEMANTIC SEARCH (CHROMADB) INDEXING
        # =================================================================

        print("="*80)
        print("PHASE 8: SEMANTIC SEARCH (CHROMADB) INDEXING")
        print("="*80)
        print()

        # Create JSONL for ChromaDB ingestion
        jsonl_file = extraction_dir / 'chromadb_package.jsonl'
        objects_for_chromadb = []

        # Index equations
        equations_dir = extraction_dir / 'equations'
        if equations_dir.exists():
            for eq_file in sorted(equations_dir.glob('eq_*.png')):
                eq_num = eq_file.stem.replace('eq_', '')
                # Use equation number as text for embedding
                objects_for_chromadb.append({
                    'id': f"equation_{eq_num}",
                    'text': f"Equation {eq_num}",  # Minimal text representation
                    'type': 'equation',
                    'metadata': {
                        'page': 1,  # Would need actual page number
                        'domain': 'thermodynamics',
                        'quality': 0.95,
                        'has_latex': False,
                        'has_image': True
                    }
                })

        # Index tables
        tables_dir = extraction_dir / 'tables'
        if tables_dir.exists():
            for table_file in sorted(tables_dir.glob('table_*.csv')):
                table_num = table_file.stem.replace('table_', '')
                # Read first few lines for text content
                try:
                    with open(table_file, 'r', encoding='utf-8') as f:
                        table_text = '\n'.join(f.readlines()[:5])  # First 5 lines
                except:
                    table_text = f"Table {table_num}"

                objects_for_chromadb.append({
                    'id': f"table_{table_num}",
                    'text': table_text,
                    'type': 'table',
                    'metadata': {
                        'page': 1,
                        'domain': 'thermodynamics',
                        'quality': 0.90,
                        'has_latex': False,
                        'has_image': False
                    }
                })

        # Index text blocks
        text_dir = extraction_dir / 'text'
        if text_dir.exists():
            for text_file in sorted(text_dir.glob('text_*.txt')):
                try:
                    with open(text_file, 'r', encoding='utf-8') as f:
                        text_content = f.read()

                    if len(text_content.strip()) >= 10:  # Skip very short text
                        objects_for_chromadb.append({
                            'id': text_file.stem,
                            'text': text_content,
                            'type': 'text',
                            'metadata': {
                                'page': 1,
                                'domain': 'thermodynamics',
                                'quality': 0.85,
                                'has_latex': False,
                                'has_image': False
                            }
                        })
                except:
                    pass

        # Write JSONL file
        print(f"Creating JSONL package for ChromaDB...")
        with open(jsonl_file, 'w', encoding='utf-8') as f:
            for obj in objects_for_chromadb:
                f.write(json.dumps(obj) + '\n')

        print(f"  Created {jsonl_file.name} ({len(objects_for_chromadb)} objects)")

        # Ingest into ChromaDB
        print(f"\nIngesting into ChromaDB...")
        chromadb_indexed = 0
        try:
            chromadb_indexed = self.chromadb.ingest_jsonl(jsonl_file, batch_size=10)
            print(f"✅ ChromaDB indexing complete: {chromadb_indexed} objects")
        except Exception as e:
            print(f"⚠️  ChromaDB indexing failed: {e}")
            chromadb_indexed = 0

        print()

        # =================================================================
        # PHASE 9: SUMMARY AND STATISTICS
        # =================================================================

        print("="*80)
        print("SUMMARY")
        print("="*80)
        print()

        stats = self.registry.get_statistics()

        print(f"✅ Processing complete!")
        print(f"\n📂 Organized output:")
        print(f"   {extraction_dir}")
        print(f"\n📊 Database statistics:")
        print(f"   Total documents: {stats.get('total_documents', 0)}")
        print(f"   Total extractions: {stats.get('total_extractions', 0)}")
        print(f"   Documents by type: {stats.get('documents_by_type', {})}")
        print(f"\n📈 Objects indexed:")
        print(f"   Equations: {equations_indexed}")
        print(f"   Tables: {tables_indexed}")
        print(f"   Figures: {figures_indexed}")
        print(f"\n🔍 Search systems:")
        print(f"   FTS5 full-text search: ✅ Enabled")
        print(f"   ChromaDB semantic search: {chromadb_indexed} objects")
        print()

        # Return summary
        return {
            'extraction_id': extraction_id,
            'doc_id': doc_id,
            'output_directory': str(extraction_dir),
            'extraction_counts': {
                'equations': results['extraction_counts']['equations'],
                'tables': results['extraction_counts']['tables'],
                'figures': results['extraction_counts']['figures'],
                'equations_indexed': equations_indexed,
                'tables_indexed': tables_indexed,
                'figures_indexed': figures_indexed
            },
            'search_systems': {
                'fts5_enabled': True,
                'chromadb_objects': chromadb_indexed
            },
            'timing': results['timing'],
            'database_stats': stats
        }

    def close(self):
        """Close database connections."""
        if self.registry:
            self.registry.close()


def main():
    """
    Main entry point for registry-integrated pipeline.

    Usage:
        python -m orchestration.registry_integrated_orchestrator path/to/document.pdf
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m orchestration.registry_integrated_orchestrator <pdf_path>")
        print("\nExample:")
        print("  python -m orchestration.registry_integrated_orchestrator tests/test_data/Ch-04_Heat_Transfer.pdf")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])

    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    # Model path (should be configured in settings)
    model_path = "models/doclayout_yolo_docstructbench_imgsz1280_2501.pt"

    # Create orchestrator with blanket approval to proceed
    orchestrator = RegistryIntegratedOrchestrator(
        model_path=model_path,
        user_metadata={
            'chapter_number': 4,
            'chapter_title': 'Heat Transfer',
            'title': 'Steam: Its Generation and Use',
            'authors': ['Babcock & Wilcox Company'],
            'year': 2005,
            'edition': '41st',
            'publisher': 'Babcock & Wilcox',
            'total_chapters': 50,
            'doc_type': 'book'
        }
    )

    try:
        # Process document
        results = orchestrator.process_document(
            pdf_path=pdf_path,
            doc_type='book',
            auto_detect_metadata=True
        )

        print("\n" + "="*80)
        print("REGISTRY-INTEGRATED PIPELINE COMPLETE")
        print("="*80)
        print(f"\n✅ Extraction ID: {results['extraction_id']}")
        print(f"✅ Document ID: {results['doc_id']}")
        print(f"✅ Output: {results['output_directory']}")
        print()

    finally:
        orchestrator.close()


if __name__ == "__main__":
    main()
