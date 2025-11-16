#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Data Structures for Semantic-Aware Hierarchical Chunking

Defines core data structures for representing document logical structure.

Author: Claude Code
Date: 2025-01-27
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

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path
from enum import Enum


class SectionType(Enum):
    """Types of logical sections in a document."""
    PART = "part"                      # Book part (highest level)
    CHAPTER = "chapter"                # Chapter
    SECTION = "section"                # Numbered section (4.1)
    SUBSECTION = "subsection"          # Subsection (4.1.2)
    APPENDIX = "appendix"              # Appendix
    UNKNOWN = "unknown"                # Unknown structure


@dataclass
class LogicalSection:
    """
    Represents a logical section of a document.

    A logical section is a semantically coherent unit like a chapter,
    section, or part that has clear boundaries in the document structure.
    """
    # Identification
    section_type: SectionType
    section_number: Optional[str] = None    # e.g., "4", "IV", "A"
    title: Optional[str] = None

    # Page boundaries
    start_page: int = 0                     # 0-indexed
    end_page: int = 0                       # 0-indexed, inclusive
    page_count: int = 0

    # Hierarchy
    parent_section: Optional[str] = None    # Parent section ID
    subsections: List[str] = field(default_factory=list)  # Child section IDs
    level: int = 0                          # Nesting level (0 = top)

    # Detection metadata
    confidence: float = 1.0                 # Detection confidence
    detection_method: str = "unknown"       # How it was detected

    # Processing metadata
    requires_subdivision: bool = False      # Too large for single unit?
    subdivision_plan: Optional[List[Dict[str, Any]]] = None

    def __post_init__(self):
        """Calculate derived fields."""
        if self.page_count == 0:
            self.page_count = self.end_page - self.start_page + 1

    @property
    def section_id(self) -> str:
        """Generate unique section ID."""
        if self.section_number:
            return f"{self.section_type.value}_{self.section_number}"
        else:
            return f"{self.section_type.value}_{self.start_page}"

    @property
    def display_name(self) -> str:
        """Human-readable section name."""
        parts = []

        if self.section_type != SectionType.UNKNOWN:
            parts.append(self.section_type.value.capitalize())

        if self.section_number:
            parts.append(self.section_number)

        if self.title:
            parts.append(f": {self.title}")

        return " ".join(parts) if parts else f"Pages {self.start_page}-{self.end_page}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['section_type'] = self.section_type.value
        result['section_id'] = self.section_id
        result['display_name'] = self.display_name
        return result


@dataclass
class ProcessingUnit:
    """
    Represents a unit of work for processing.

    May be an entire logical section (chapter) or a subdivision
    of a large section (chunk).
    """
    # Identification
    unit_id: str
    unit_type: str                          # 'chapter', 'chunk', 'section'

    # Content
    logical_section: LogicalSection         # Parent logical section
    start_page: int                         # 0-indexed
    end_page: int                           # 0-indexed, inclusive
    page_count: int = 0

    # Processing metadata
    chunk_number: Optional[int] = None      # If subdivided, chunk number
    total_chunks: Optional[int] = None      # Total chunks in section

    # Output
    output_dir: Optional[Path] = None

    def __post_init__(self):
        """Calculate derived fields."""
        if self.page_count == 0:
            self.page_count = self.end_page - self.start_page + 1

    @property
    def is_complete_section(self) -> bool:
        """True if this unit represents the entire logical section."""
        return (self.start_page == self.logical_section.start_page and
                self.end_page == self.logical_section.end_page)

    @property
    def display_name(self) -> str:
        """Human-readable unit name."""
        if self.is_complete_section:
            return self.logical_section.display_name
        else:
            return f"{self.logical_section.display_name} - Chunk {self.chunk_number}/{self.total_chunks}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['logical_section'] = self.logical_section.to_dict()
        result['output_dir'] = str(self.output_dir) if self.output_dir else None
        result['is_complete_section'] = self.is_complete_section
        result['display_name'] = self.display_name
        return result


@dataclass
class DocumentStructure:
    """
    Complete document structure with logical sections.
    """
    # Document metadata
    document_path: Path
    total_pages: int

    # Structure
    sections: List[LogicalSection] = field(default_factory=list)
    root_sections: List[str] = field(default_factory=list)  # Top-level section IDs

    # Detection metadata
    detection_method: str = "unknown"
    detection_confidence: float = 0.0
    has_hierarchical_structure: bool = False

    def get_section(self, section_id: str) -> Optional[LogicalSection]:
        """Get section by ID."""
        for section in self.sections:
            if section.section_id == section_id:
                return section
        return None

    def get_sections_by_type(self, section_type: SectionType) -> List[LogicalSection]:
        """Get all sections of a specific type."""
        return [s for s in self.sections if s.section_type == section_type]

    def get_top_level_sections(self) -> List[LogicalSection]:
        """Get top-level sections (chapters, parts)."""
        return [self.get_section(sid) for sid in self.root_sections if self.get_section(sid)]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'document_path': str(self.document_path),
            'total_pages': self.total_pages,
            'sections': [s.to_dict() for s in self.sections],
            'root_sections': self.root_sections,
            'detection_method': self.detection_method,
            'detection_confidence': self.detection_confidence,
            'has_hierarchical_structure': self.has_hierarchical_structure,
            'section_count': len(self.sections),
            'chapter_count': len(self.get_sections_by_type(SectionType.CHAPTER)),
            'part_count': len(self.get_sections_by_type(SectionType.PART))
        }


@dataclass
class ProcessingPlan:
    """
    Complete processing plan for a document.
    """
    # Source
    document_structure: DocumentStructure
    processing_units: List[ProcessingUnit] = field(default_factory=list)

    # Configuration
    max_unit_pages: int = 100
    enable_parallel: bool = True
    optimal_workers: int = 4

    # Statistics
    total_units: int = 0
    units_requiring_subdivision: int = 0
    estimated_processing_time_seconds: float = 0.0

    def __post_init__(self):
        """Calculate statistics."""
        self.total_units = len(self.processing_units)
        self.units_requiring_subdivision = sum(
            1 for unit in self.processing_units
            if unit.chunk_number is not None
        )

    def get_units_for_section(self, section_id: str) -> List[ProcessingUnit]:
        """Get all processing units for a logical section."""
        return [u for u in self.processing_units
                if u.logical_section.section_id == section_id]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'document_structure': self.document_structure.to_dict(),
            'processing_units': [u.to_dict() for u in self.processing_units],
            'max_unit_pages': self.max_unit_pages,
            'enable_parallel': self.enable_parallel,
            'optimal_workers': self.optimal_workers,
            'total_units': self.total_units,
            'units_requiring_subdivision': self.units_requiring_subdivision,
            'estimated_processing_time_seconds': self.estimated_processing_time_seconds
        }


# Testing
if __name__ == "__main__":
    print("Testing Semantic Chunking Data Structures...")
    print("=" * 70)

    # Test 1: LogicalSection
    print("\n1. LogicalSection")
    section = LogicalSection(
        section_type=SectionType.CHAPTER,
        section_number="4",
        title="Heat Transfer",
        start_page=0,
        end_page=33,
        confidence=0.95,
        detection_method="regex_pattern"
    )
    print(f"   ID: {section.section_id}")
    print(f"   Display: {section.display_name}")
    print(f"   Pages: {section.page_count}")
    assert section.page_count == 34
    assert section.section_id == "chapter_4"
    print("   ✅ LogicalSection working")

    # Test 2: ProcessingUnit (complete section)
    print("\n2. ProcessingUnit (Complete Section)")
    unit = ProcessingUnit(
        unit_id="unit_001",
        unit_type="chapter",
        logical_section=section,
        start_page=0,
        end_page=33,
        output_dir=Path("results/chapter_04")
    )
    print(f"   ID: {unit.unit_id}")
    print(f"   Display: {unit.display_name}")
    print(f"   Complete: {unit.is_complete_section}")
    assert unit.is_complete_section == True
    assert unit.page_count == 34
    print("   ✅ ProcessingUnit (complete) working")

    # Test 3: ProcessingUnit (chunk)
    print("\n3. ProcessingUnit (Chunk)")
    large_section = LogicalSection(
        section_type=SectionType.CHAPTER,
        section_number="5",
        title="Large Chapter",
        start_page=0,
        end_page=299
    )
    chunk_unit = ProcessingUnit(
        unit_id="unit_002",
        unit_type="chunk",
        logical_section=large_section,
        start_page=0,
        end_page=99,
        chunk_number=1,
        total_chunks=3,
        output_dir=Path("results/chapter_05/chunk_001")
    )
    print(f"   Display: {chunk_unit.display_name}")
    print(f"   Complete: {chunk_unit.is_complete_section}")
    assert chunk_unit.is_complete_section == False
    assert chunk_unit.page_count == 100
    print("   ✅ ProcessingUnit (chunk) working")

    # Test 4: DocumentStructure
    print("\n4. DocumentStructure")
    doc_structure = DocumentStructure(
        document_path=Path("test.pdf"),
        total_pages=334,
        sections=[section, large_section],
        root_sections=["chapter_4", "chapter_5"],
        has_hierarchical_structure=True
    )
    chapters = doc_structure.get_sections_by_type(SectionType.CHAPTER)
    print(f"   Chapters: {len(chapters)}")
    print(f"   Total pages: {doc_structure.total_pages}")
    assert len(chapters) == 2
    print("   ✅ DocumentStructure working")

    # Test 5: ProcessingPlan
    print("\n5. ProcessingPlan")
    plan = ProcessingPlan(
        document_structure=doc_structure,
        processing_units=[unit, chunk_unit],
        max_unit_pages=100
    )
    print(f"   Total units: {plan.total_units}")
    print(f"   Units with subdivision: {plan.units_requiring_subdivision}")
    assert plan.total_units == 2
    assert plan.units_requiring_subdivision == 1
    print("   ✅ ProcessingPlan working")

    print("\n" + "=" * 70)
    print("✅ All data structure tests passed!")
