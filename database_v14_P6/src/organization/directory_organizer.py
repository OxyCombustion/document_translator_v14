# -*- coding: utf-8 -*-
"""
Directory Organization System

Creates and manages hierarchical directory structure for document extractions.

Structure:
results/
├── books/
│   └── steam_generation_and_use_babcock_wilcox_41ed/
│       ├── book_metadata.json
│       ├── ch_01_introduction/
│       ├── ch_04_heat_transfer/
│       │   ├── extraction_metadata.json
│       │   ├── equations/
│       │   ├── tables/
│       │   ├── figures/
│       │   ├── text/
│       │   └── bibliography/
│       └── ...
├── papers/
├── manuals/
└── standards/

Author: Claude Code
Date: 2025-01-21
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

from pathlib import Path
from typing import Dict, Optional, Any
import json
import shutil


class DirectoryOrganizer:
    """Manage hierarchical directory structure for document extractions."""

    def __init__(self, base_path: Path = Path("results")):
        """
        Initialize directory organizer.

        Args:
            base_path: Base directory for all results
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_document_directory(self,
                              doc_type: str,
                              doc_id: str) -> Path:
        """
        Get directory path for a document.

        Args:
            doc_type: Document type ('book', 'paper', 'manual', 'standard')
            doc_id: Document ID slug

        Returns:
            Path to document directory
        """
        # Pluralize doc_type for directory name
        type_dir = f"{doc_type}s"

        doc_dir = self.base_path / type_dir / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)

        return doc_dir

    def get_extraction_directory(self,
                                doc_type: str,
                                doc_id: str,
                                chapter_number: Optional[int] = None,
                                chapter_title: Optional[str] = None,
                                section_id: Optional[str] = None) -> Path:
        """
        Get directory path for an extraction.

        Args:
            doc_type: Document type
            doc_id: Document ID
            chapter_number: Chapter number (for books)
            chapter_title: Chapter title (for books)
            section_id: Section identifier (for papers/manuals)

        Returns:
            Path to extraction directory
        """
        doc_dir = self.get_document_directory(doc_type, doc_id)

        # Determine extraction subdirectory
        if chapter_number is not None:
            # Book chapter
            if chapter_title:
                # Clean chapter title for directory name
                clean_title = self._sanitize_dirname(chapter_title)
                extr_dirname = f"ch_{chapter_number:02d}_{clean_title}"
            else:
                extr_dirname = f"ch_{chapter_number:02d}"

        elif section_id:
            # Paper/manual section
            extr_dirname = f"section_{section_id}"

        else:
            # Whole document (no subdivision)
            extr_dirname = "complete"

        extr_dir = doc_dir / extr_dirname
        extr_dir.mkdir(parents=True, exist_ok=True)

        return extr_dir

    def create_extraction_structure(self, extraction_dir: Path) -> Dict[str, Path]:
        """
        Create standard extraction directory structure.

        Args:
            extraction_dir: Base extraction directory

        Returns:
            Dictionary of subdirectory paths
        """
        subdirs = {
            'equations': extraction_dir / 'equations',
            'tables': extraction_dir / 'tables',
            'figures': extraction_dir / 'figures',
            'text': extraction_dir / 'text',
            'bibliography': extraction_dir / 'bibliography',
            'validation': extraction_dir / 'validation'
        }

        for subdir in subdirs.values():
            subdir.mkdir(parents=True, exist_ok=True)

        return subdirs

    def save_document_metadata(self,
                               doc_type: str,
                               doc_id: str,
                               metadata: Dict[str, Any]):
        """
        Save document metadata to JSON file.

        Args:
            doc_type: Document type
            doc_id: Document ID
            metadata: Complete document metadata
        """
        doc_dir = self.get_document_directory(doc_type, doc_id)
        metadata_file = doc_dir / f"{doc_type}_metadata.json"

        with metadata_file.open('w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved document metadata: {metadata_file}")

    def save_extraction_metadata(self,
                                extraction_dir: Path,
                                metadata: Dict[str, Any]):
        """
        Save extraction metadata to JSON file.

        Args:
            extraction_dir: Extraction directory
            metadata: Extraction metadata
        """
        metadata_file = extraction_dir / 'extraction_metadata.json'

        with metadata_file.open('w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved extraction metadata: {metadata_file}")

    def move_extraction_files(self,
                             source_dir: Path,
                             extraction_dir: Path,
                             file_types: Optional[Dict[str, str]] = None):
        """
        Move extraction files from source to organized directory.

        Args:
            source_dir: Source directory (e.g., results/unified_pipeline)
            extraction_dir: Target organized directory
            file_types: Mapping of source subdirs to target subdirs
        """
        if file_types is None:
            file_types = {
                'equations': 'equations',
                'tables': 'tables',
                'figures': 'figures',
                'text': 'text',
                'bibliography': 'bibliography'
            }

        subdirs = self.create_extraction_structure(extraction_dir)

        for source_name, target_name in file_types.items():
            source_subdir = source_dir / source_name
            target_subdir = subdirs[target_name]

            if source_subdir.exists():
                # Copy all files from source to target
                for file_path in source_subdir.iterdir():
                    if file_path.is_file():
                        target_path = target_subdir / file_path.name
                        shutil.copy2(file_path, target_path)

                print(f"✅ Moved {source_name}/ → {target_subdir.name}/")

        # Also copy top-level files (summaries, validation reports)
        for pattern in ['*.json', '*.md', '*.txt']:
            for file_path in source_dir.glob(pattern):
                if file_path.is_file():
                    target_path = extraction_dir / file_path.name
                    shutil.copy2(file_path, target_path)

    @staticmethod
    def _sanitize_dirname(name: str) -> str:
        """
        Sanitize string for use as directory name.

        Args:
            name: Original name

        Returns:
            Sanitized name (lowercase, underscores, alphanumeric)
        """
        import re

        # Convert to lowercase
        name = name.lower()

        # Replace special chars with underscore
        name = re.sub(r'[^\w\s-]', '', name)

        # Replace spaces and hyphens with underscores
        name = re.sub(r'[-\s]+', '_', name)

        # Remove leading/trailing underscores
        name = name.strip('_')

        # Limit length
        if len(name) > 50:
            name = name[:50]

        return name

    def get_directory_tree(self, doc_type: Optional[str] = None) -> str:
        """
        Generate tree view of directory structure.

        Args:
            doc_type: Filter by document type (None = all)

        Returns:
            String representation of directory tree
        """
        lines = []
        lines.append(str(self.base_path))

        if doc_type:
            type_dirs = [self.base_path / f"{doc_type}s"]
        else:
            type_dirs = [d for d in self.base_path.iterdir() if d.is_dir()]

        for type_dir in sorted(type_dirs):
            if not type_dir.is_dir():
                continue

            lines.append(f"├── {type_dir.name}/")

            # List documents
            doc_dirs = [d for d in type_dir.iterdir() if d.is_dir()]
            for i, doc_dir in enumerate(sorted(doc_dirs)):
                is_last_doc = (i == len(doc_dirs) - 1)
                prefix = "└──" if is_last_doc else "├──"

                lines.append(f"│   {prefix} {doc_dir.name}/")

                # List extractions (chapters/sections)
                extr_dirs = [d for d in doc_dir.iterdir() if d.is_dir()]
                for j, extr_dir in enumerate(sorted(extr_dirs)):
                    is_last_extr = (j == len(extr_dirs) - 1)
                    extr_prefix = "    └──" if is_last_extr else "    ├──"

                    if is_last_doc:
                        lines.append(f"    {extr_prefix} {extr_dir.name}/")
                    else:
                        lines.append(f"│   {extr_prefix} {extr_dir.name}/")

        return '\n'.join(lines)


if __name__ == "__main__":
    # Test directory organizer
    organizer = DirectoryOrganizer()

    # Test: Create book structure
    doc_dir = organizer.get_extraction_directory(
        doc_type='book',
        doc_id='steam_generation_and_use_babcock_wilcox_41ed',
        chapter_number=4,
        chapter_title='Heat Transfer'
    )

    subdirs = organizer.create_extraction_structure(doc_dir)

    print(f"\n✅ Created directory structure:")
    print(f"   {doc_dir}")
    for name, path in subdirs.items():
        print(f"   ├── {name}/")

    print(f"\n📁 Directory tree:")
    print(organizer.get_directory_tree(doc_type='book'))
