#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Structured Output Manager - Hierarchical File Organization

Organizes extraction outputs into a hierarchical structure for human verification:
Document → Chapter → Section → Page → Type (equations/tables/figures/text)

This is a POST-PROCESSING step that creates a human-readable view of the flat
extraction outputs WITHOUT affecting pipeline compatibility.

Design:
-------
- Flat structure: test_output/ (for pipeline compatibility)
- Hierarchical structure: test_output_structured/ (for human verification)
- Parallel outputs: Both maintained simultaneously
- Zero risk: Pipeline unchanged, hierarchical structure is optional

Author: Claude Code
Date: 2025-11-20
Version: 1.0.0
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

import shutil
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

# Import semantic structure detector for chapter/section detection
try:
    from pipelines.rag_ingestion.packages.semantic_processing_v14_P4.src.chunking.semantic_structure_detector import SemanticStructureDetector
    from pipelines.rag_ingestion.packages.semantic_processing_v14_P4.src.chunking.data_structures import DocumentStructure, LogicalSection
    STRUCTURE_DETECTION_AVAILABLE = True
except ImportError:
    STRUCTURE_DETECTION_AVAILABLE = False
    print("⚠️  Semantic structure detection not available. Using page-only organization.")


@dataclass
class FileMapping:
    """Maps a file from flat structure to hierarchical location."""
    source_path: Path
    dest_path: Path
    page_num: int
    content_type: str  # equation, table, figure, text
    metadata: Dict[str, Any]


class StructuredOutputManager:
    """
    Manages hierarchical organization of extraction outputs.

    Creates a parallel hierarchical view of flat extraction outputs:

    Flat (pipeline):                    Hierarchical (human verification):
    ----------------                    ----------------------------------
    test_output/                        test_output_structured/
    ├── equations/                      └── Ch-04_Heat_Transfer/
    │   ├── eq_1.png                        ├── metadata.json
    │   └── ...                             └── Chapter_4/
    ├── tables/                                 ├── Section_4.1_Conduction/
    │   ├── table_1.csv                         │   ├── Page_001/
    │   └── ...                                 │   │   ├── equations/
    └── summary.json                            │   │   │   └── eq_1.png
                                                │   │   ├── tables/
                                                │   │   └── metadata.json
                                                │   └── ...
                                                └── ...
    """

    def __init__(self, flat_output_dir: Path, structured_output_dir: Path,
                 pdf_path: Path, enable_structure_detection: bool = True):
        """
        Initialize structured output manager.

        Args:
            flat_output_dir: Source directory with flat extraction outputs
            structured_output_dir: Destination for hierarchical organization
            pdf_path: PDF being processed (for structure detection)
            enable_structure_detection: Use semantic structure detection (default: True)
        """
        self.flat_output_dir = Path(flat_output_dir)
        self.structured_output_dir = Path(structured_output_dir)
        self.pdf_path = Path(pdf_path)
        self.enable_structure_detection = enable_structure_detection and STRUCTURE_DETECTION_AVAILABLE

        # Document structure
        self.document_structure: Optional[DocumentStructure] = None
        self.document_name = pdf_path.stem

    def organize_outputs(self) -> Dict[str, Any]:
        """
        Organize flat outputs into hierarchical structure.

        Returns:
            Statistics about the organization process
        """
        print(f"\n{'='*80}")
        print(f"STRUCTURED OUTPUT ORGANIZATION")
        print(f"{'='*80}")
        print(f"Document: {self.document_name}")
        print(f"Source: {self.flat_output_dir}")
        print(f"Destination: {self.structured_output_dir}")
        print()

        # Step 1: Detect document structure
        if self.enable_structure_detection:
            print("Step 1: Detecting document structure...")
            self.document_structure = self._detect_structure()

            if self.document_structure and self.document_structure.sections:
                print(f"✅ Detected {len(self.document_structure.sections)} sections")
                for section in self.document_structure.sections:
                    print(f"   - {section.title} (pages {section.start_page+1}-{section.end_page+1})")
            else:
                print("ℹ️  No sections detected, using page-only organization")
            print()
        else:
            print("ℹ️  Structure detection disabled, using page-only organization")
            print()

        # Step 2: Create base directory structure
        print("Step 2: Creating directory structure...")
        self._create_directory_structure()
        print("✅ Directory structure created")
        print()

        # Step 3: Map files to hierarchical locations
        print("Step 3: Mapping files to hierarchical structure...")
        file_mappings = self._create_file_mappings()
        print(f"✅ Mapped {len(file_mappings)} files")
        print()

        # Step 4: Copy files to hierarchical locations
        print("Step 4: Copying files to structured locations...")
        copied_count = self._copy_files(file_mappings)
        print(f"✅ Copied {copied_count} files")
        print()

        # Step 5: Generate metadata files
        print("Step 5: Generating metadata files...")
        metadata_count = self._generate_metadata_files(file_mappings)
        print(f"✅ Generated {metadata_count} metadata files")
        print()

        # Summary
        stats = {
            'document_name': self.document_name,
            'total_files': len(file_mappings),
            'files_copied': copied_count,
            'metadata_files': metadata_count,
            'structure_detected': self.document_structure is not None,
            'sections': len(self.document_structure.sections) if self.document_structure else 0,
            'timestamp': datetime.now().isoformat()
        }

        # Save organization summary
        summary_path = self.structured_output_dir / "organization_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

        print(f"{'='*80}")
        print(f"ORGANIZATION COMPLETE")
        print(f"{'='*80}")
        print(f"Files organized: {copied_count}")
        print(f"Hierarchical view: {self.structured_output_dir}")
        print()

        return stats

    def _detect_structure(self) -> Optional[DocumentStructure]:
        """Detect document structure using SemanticStructureDetector."""
        try:
            config_path = Path("pipelines/rag_ingestion/config/semantic_chunking.yaml")
            if not config_path.exists():
                config_path = None

            detector = SemanticStructureDetector(config_path)
            structure = detector.detect(self.pdf_path)
            return structure
        except Exception as e:
            print(f"⚠️  Structure detection failed: {e}")
            return None

    def _create_directory_structure(self):
        """Create hierarchical directory structure."""
        # Base directory: document name
        doc_dir = self.structured_output_dir / self.document_name
        doc_dir.mkdir(parents=True, exist_ok=True)

        if self.document_structure and self.document_structure.sections:
            # Create chapter/section directories
            for section in self.document_structure.sections:
                section_name = self._sanitize_filename(section.title)
                section_dir = doc_dir / section_name

                # Create page directories within section
                for page_num in range(section.start_page, section.end_page + 1):
                    page_dir = section_dir / f"Page_{page_num+1:03d}"
                    page_dir.mkdir(parents=True, exist_ok=True)

                    # Create content type subdirectories
                    for content_type in ['equations', 'tables', 'figures', 'text']:
                        (page_dir / content_type).mkdir(exist_ok=True)
        else:
            # No structure detected, create simple page-based organization
            # Get total pages from PDF
            import fitz
            doc = fitz.open(self.pdf_path)
            total_pages = len(doc)
            doc.close()

            for page_num in range(total_pages):
                page_dir = doc_dir / f"Page_{page_num+1:03d}"
                page_dir.mkdir(parents=True, exist_ok=True)

                # Create content type subdirectories
                for content_type in ['equations', 'tables', 'figures', 'text']:
                    (page_dir / content_type).mkdir(exist_ok=True)

    def _create_file_mappings(self) -> List[FileMapping]:
        """Map files from flat structure to hierarchical locations."""
        mappings = []

        # Process each content type
        content_types = {
            'equations': 'equations',
            'tables': 'tables',
            'figures': 'figures',
            'text': 'text'
        }

        for flat_subdir, content_type in content_types.items():
            flat_dir = self.flat_output_dir / flat_subdir
            if not flat_dir.exists():
                continue

            # Process all files in this content type directory
            for file_path in flat_dir.iterdir():
                if file_path.is_file():
                    # Extract page number from filename
                    page_num = self._extract_page_number(file_path, content_type)
                    if page_num is None:
                        print(f"⚠️  Could not extract page number from {file_path.name}, skipping")
                        continue

                    # Find destination path
                    dest_path = self._get_destination_path(file_path, page_num, content_type)

                    mapping = FileMapping(
                        source_path=file_path,
                        dest_path=dest_path,
                        page_num=page_num,
                        content_type=content_type,
                        metadata={'original_name': file_path.name}
                    )
                    mappings.append(mapping)

        return mappings

    def _extract_page_number(self, file_path: Path, content_type: str) -> Optional[int]:
        """Extract page number from filename."""
        filename = file_path.stem

        # Equation pattern: eq_yolo_1_1 -> page 1 (first number)
        if content_type == 'equations':
            import re
            match = re.search(r'eq_(?:yolo_)?(\d+)', filename)
            if match:
                return int(match.group(1)) - 1  # Convert to 0-indexed

        # Table pattern: table_1 -> page number needs to be looked up from metadata
        # For now, we'll try to extract from filename
        elif content_type == 'tables':
            import re
            match = re.search(r'table_(\d+)', filename)
            if match:
                # Tables don't have page in filename, return 0 for now
                # TODO: Look up page from table metadata
                return 0

        # Figure pattern: similar to tables
        elif content_type == 'figures':
            import re
            match = re.search(r'fig(?:ure)?_(\d+)', filename)
            if match:
                return 0  # TODO: Look up from metadata

        return None

    def _get_destination_path(self, file_path: Path, page_num: int, content_type: str) -> Path:
        """Get destination path in hierarchical structure."""
        doc_dir = self.structured_output_dir / self.document_name

        if self.document_structure and self.document_structure.sections:
            # Find which section this page belongs to
            section = self._find_section_for_page(page_num)
            if section:
                section_name = self._sanitize_filename(section.title)
                page_dir = doc_dir / section_name / f"Page_{page_num+1:03d}" / content_type
            else:
                # Page not in any section, use top-level page directory
                page_dir = doc_dir / f"Page_{page_num+1:03d}" / content_type
        else:
            # No structure, simple page-based organization
            page_dir = doc_dir / f"Page_{page_num+1:03d}" / content_type

        return page_dir / file_path.name

    def _find_section_for_page(self, page_num: int) -> Optional[LogicalSection]:
        """Find which section a page belongs to."""
        if not self.document_structure or not self.document_structure.sections:
            return None

        for section in self.document_structure.sections:
            if section.start_page <= page_num <= section.end_page:
                return section

        return None

    def _copy_files(self, file_mappings: List[FileMapping]) -> int:
        """Copy files to hierarchical locations."""
        copied = 0
        for mapping in file_mappings:
            try:
                mapping.dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(mapping.source_path, mapping.dest_path)
                copied += 1
            except Exception as e:
                print(f"⚠️  Failed to copy {mapping.source_path.name}: {e}")

        return copied

    def _generate_metadata_files(self, file_mappings: List[FileMapping]) -> int:
        """Generate metadata.json files at each level of hierarchy."""
        metadata_files = 0

        # Document-level metadata
        doc_metadata = {
            'document_name': self.document_name,
            'source_pdf': str(self.pdf_path),
            'total_pages': self.document_structure.total_pages if self.document_structure else None,
            'structure_detected': self.document_structure is not None,
            'sections': [
                {
                    'title': s.title,
                    'type': s.section_type.value if hasattr(s.section_type, 'value') else str(s.section_type),
                    'start_page': s.start_page + 1,
                    'end_page': s.end_page + 1
                }
                for s in (self.document_structure.sections if self.document_structure else [])
            ],
            'generated': datetime.now().isoformat()
        }

        doc_dir = self.structured_output_dir / self.document_name
        with open(doc_dir / 'metadata.json', 'w', encoding='utf-8') as f:
            json.dump(doc_metadata, f, indent=2, ensure_ascii=False)
        metadata_files += 1

        # Page-level metadata (group by page)
        from collections import defaultdict
        pages = defaultdict(list)
        for mapping in file_mappings:
            pages[mapping.page_num].append(mapping)

        for page_num, mappings in pages.items():
            section = self._find_section_for_page(page_num)

            if self.document_structure and section:
                section_name = self._sanitize_filename(section.title)
                page_dir = doc_dir / section_name / f"Page_{page_num+1:03d}"
            else:
                page_dir = doc_dir / f"Page_{page_num+1:03d}"

            page_metadata = {
                'page_number': page_num + 1,
                'section': section.title if section else None,
                'files': {
                    'equations': [m.dest_path.name for m in mappings if m.content_type == 'equations'],
                    'tables': [m.dest_path.name for m in mappings if m.content_type == 'tables'],
                    'figures': [m.dest_path.name for m in mappings if m.content_type == 'figures'],
                    'text': [m.dest_path.name for m in mappings if m.content_type == 'text']
                }
            }

            with open(page_dir / 'metadata.json', 'w', encoding='utf-8') as f:
                json.dump(page_metadata, f, indent=2, ensure_ascii=False)
            metadata_files += 1

        return metadata_files

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize string for use as directory name."""
        # Remove or replace characters that are problematic in filenames
        import re
        # Replace spaces and special chars with underscores
        sanitized = re.sub(r'[^\w\s-]', '', name)
        sanitized = re.sub(r'[\s]+', '_', sanitized)
        return sanitized.strip('_')


# Example usage
if __name__ == "__main__":
    manager = StructuredOutputManager(
        flat_output_dir=Path("test_output_orchestrator"),
        structured_output_dir=Path("test_output_structured"),
        pdf_path=Path("test_data/Ch-04_Heat_Transfer.pdf"),
        enable_structure_detection=True
    )

    stats = manager.organize_outputs()
    print(f"\nOrganization statistics:")
    print(json.dumps(stats, indent=2))
