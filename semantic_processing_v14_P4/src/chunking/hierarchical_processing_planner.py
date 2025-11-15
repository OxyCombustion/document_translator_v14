#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hierarchical Processing Planner

Creates processing plans from document structure, determining which sections
need subdivision and calculating optimal chunk sizes.

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

import math
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml

try:
    from .data_structures import (
        LogicalSection,
        ProcessingUnit,
        DocumentStructure,
        ProcessingPlan
    )
except ImportError:
    # Running as main - use absolute import
    from data_structures import (
        LogicalSection,
        ProcessingUnit,
        DocumentStructure,
        ProcessingPlan
    )


class PlanningError(Exception):
    """Custom exception for planning failures."""
    pass


class HierarchicalProcessingPlanner:
    """
    Creates processing plans from document structure.

    Determines which sections need subdivision based on memory constraints
    and creates optimally-sized processing units.

    Attributes:
        config (Dict[str, Any]): Configuration from semantic_chunking.yaml
        version (str): Planner version
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize processing planner.

        Args:
            config_path: Path to configuration file (default: config/semantic_chunking.yaml)
        """
        self.version = "1.0.0"
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config file

        Returns:
            Configuration dictionary

        Raises:
            PlanningError: If config file not found or invalid
        """
        if config_path is None:
            # Default location
            config_path = Path(__file__).parent.parent.parent / "config" / "semantic_chunking.yaml"

        if not config_path.exists():
            raise PlanningError(f"Config file not found: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            raise PlanningError(f"Failed to load config: {e}")

    def create_plan(
        self,
        structure: DocumentStructure,
        output_base_dir: Optional[Path] = None
    ) -> ProcessingPlan:
        """
        Create processing plan from document structure.

        Args:
            structure: Detected document structure
            output_base_dir: Base directory for output (default: results/)

        Returns:
            Complete processing plan with all units

        Raises:
            PlanningError: If plan creation fails
        """
        if output_base_dir is None:
            output_base_dir = Path("results")

        # Get configuration parameters
        max_unit_pages = self.config['memory']['max_unit_pages']
        enable_parallel = self.config['processing']['enable_parallel']

        # Create processing units for each section
        processing_units: List[ProcessingUnit] = []
        unit_id_counter = 1

        for section in structure.sections:
            units = self._create_units_for_section(
                section,
                output_base_dir,
                max_unit_pages,
                unit_id_counter
            )
            processing_units.extend(units)
            unit_id_counter += len(units)

        # Calculate optimal worker count
        optimal_workers = self._calculate_optimal_workers(
            processing_units,
            enable_parallel
        )

        # Estimate processing time (rough estimate)
        estimated_time = self._estimate_processing_time(processing_units)

        # Create processing plan
        plan = ProcessingPlan(
            document_structure=structure,
            processing_units=processing_units,
            max_unit_pages=max_unit_pages,
            enable_parallel=enable_parallel,
            optimal_workers=optimal_workers,
            estimated_processing_time_seconds=estimated_time
        )

        return plan

    def _create_units_for_section(
        self,
        section: LogicalSection,
        output_base_dir: Path,
        max_unit_pages: int,
        unit_id_start: int
    ) -> List[ProcessingUnit]:
        """
        Create processing units for a logical section.

        Args:
            section: Logical section to process
            output_base_dir: Base output directory
            max_unit_pages: Maximum pages per unit
            unit_id_start: Starting unit ID number

        Returns:
            List of processing units (1 if no subdivision, multiple if subdivided)
        """
        # Create output directory path
        section_dir = self._create_section_directory_path(
            section,
            output_base_dir
        )

        # Check if subdivision needed
        if section.page_count <= max_unit_pages:
            # No subdivision - create single unit for entire section
            unit = ProcessingUnit(
                unit_id=f"unit_{unit_id_start:03d}",
                unit_type="chapter" if section.section_type.value == "chapter" else "section",
                logical_section=section,
                start_page=section.start_page,
                end_page=section.end_page,
                output_dir=section_dir
            )
            return [unit]
        else:
            # Subdivision needed - create multiple balanced chunks
            return self._subdivide_section(
                section,
                section_dir,
                max_unit_pages,
                unit_id_start
            )

    def _subdivide_section(
        self,
        section: LogicalSection,
        section_dir: Path,
        max_unit_pages: int,
        unit_id_start: int
    ) -> List[ProcessingUnit]:
        """
        Subdivide large section into balanced chunks.

        Args:
            section: Section to subdivide
            section_dir: Output directory for section
            max_unit_pages: Maximum pages per unit
            unit_id_start: Starting unit ID

        Returns:
            List of chunk processing units
        """
        subdivision_method = self.config['processing']['subdivision_method']

        if subdivision_method == 'balanced':
            return self._subdivide_balanced(
                section,
                section_dir,
                max_unit_pages,
                unit_id_start
            )
        else:  # 'fixed_size'
            return self._subdivide_fixed_size(
                section,
                section_dir,
                max_unit_pages,
                unit_id_start
            )

    def _subdivide_balanced(
        self,
        section: LogicalSection,
        section_dir: Path,
        max_unit_pages: int,
        unit_id_start: int
    ) -> List[ProcessingUnit]:
        """
        Subdivide section into balanced chunks.

        Calculates number of chunks needed and distributes pages evenly.

        Args:
            section: Section to subdivide
            section_dir: Output directory
            max_unit_pages: Maximum pages per chunk
            unit_id_start: Starting unit ID

        Returns:
            List of balanced chunk units
        """
        # Calculate number of chunks needed
        num_chunks = math.ceil(section.page_count / max_unit_pages)

        # Calculate balanced chunk size
        base_chunk_size = section.page_count // num_chunks
        extra_pages = section.page_count % num_chunks

        units = []
        current_page = section.start_page

        for chunk_num in range(1, num_chunks + 1):
            # Calculate chunk size (distribute extra pages to first chunks)
            chunk_size = base_chunk_size + (1 if chunk_num <= extra_pages else 0)

            # Create chunk unit
            chunk_start = current_page
            chunk_end = current_page + chunk_size - 1

            # Create chunk directory
            chunk_dir = section_dir / f"chunk_{chunk_num:03d}"

            unit = ProcessingUnit(
                unit_id=f"unit_{unit_id_start + chunk_num - 1:03d}",
                unit_type="chunk",
                logical_section=section,
                start_page=chunk_start,
                end_page=chunk_end,
                chunk_number=chunk_num,
                total_chunks=num_chunks,
                output_dir=chunk_dir
            )

            units.append(unit)
            current_page += chunk_size

        return units

    def _subdivide_fixed_size(
        self,
        section: LogicalSection,
        section_dir: Path,
        max_unit_pages: int,
        unit_id_start: int
    ) -> List[ProcessingUnit]:
        """
        Subdivide section into fixed-size chunks.

        Creates chunks of exactly max_unit_pages (except possibly last chunk).

        Args:
            section: Section to subdivide
            section_dir: Output directory
            max_unit_pages: Chunk size
            unit_id_start: Starting unit ID

        Returns:
            List of fixed-size chunk units
        """
        units = []
        current_page = section.start_page
        chunk_num = 1

        while current_page <= section.end_page:
            chunk_start = current_page
            chunk_end = min(current_page + max_unit_pages - 1, section.end_page)

            chunk_dir = section_dir / f"chunk_{chunk_num:03d}"

            unit = ProcessingUnit(
                unit_id=f"unit_{unit_id_start + chunk_num - 1:03d}",
                unit_type="chunk",
                logical_section=section,
                start_page=chunk_start,
                end_page=chunk_end,
                chunk_number=chunk_num,
                total_chunks=0,  # Will be updated after loop
                output_dir=chunk_dir
            )

            units.append(unit)
            current_page = chunk_end + 1
            chunk_num += 1

        # Update total_chunks for all units
        total_chunks = len(units)
        for unit in units:
            unit.total_chunks = total_chunks

        return units

    def _create_section_directory_path(
        self,
        section: LogicalSection,
        base_dir: Path
    ) -> Path:
        """
        Create output directory path for section.

        Args:
            section: Logical section
            base_dir: Base output directory

        Returns:
            Path for section output directory
        """
        # Get directory format from config
        if section.section_type.value == "chapter":
            dir_format = self.config['output']['chapter_dir_format']
        else:
            dir_format = f"{section.section_type.value}_{{num}}_{{title_slug}}"

        # Create slug from title
        title_slug = self._create_slug(section.title) if section.title else "untitled"

        # Convert section number to integer for formatting
        try:
            section_num = int(section.section_number) if section.section_number else 0
        except (ValueError, TypeError):
            # If it's roman numerals or other format, use as-is
            section_num = section.section_number or "0"

        # Format directory name
        # Use simple format if section_num is string, otherwise use :02d format
        if isinstance(section_num, str):
            dir_name = dir_format.replace("{num:02d}", "{num}").format(
                num=section_num,
                title_slug=title_slug
            )
        else:
            dir_name = dir_format.format(
                num=section_num,
                title_slug=title_slug
            )

        return base_dir / dir_name

    def _create_slug(self, title: str) -> str:
        """
        Create URL-safe slug from title.

        Args:
            title: Section title

        Returns:
            Slugified title
        """
        # Convert to lowercase
        slug = title.lower()

        # Replace spaces with underscores
        slug = slug.replace(' ', '_')

        # Remove non-alphanumeric characters (except underscores and hyphens)
        slug = ''.join(c for c in slug if c.isalnum() or c in ('_', '-'))

        # Limit length
        slug = slug[:50]

        return slug

    def _calculate_optimal_workers(
        self,
        units: List[ProcessingUnit],
        enable_parallel: bool
    ) -> int:
        """
        Calculate optimal number of parallel workers.

        Args:
            units: List of processing units
            enable_parallel: Whether parallel processing is enabled

        Returns:
            Optimal worker count
        """
        if not enable_parallel:
            return 1

        # Get configuration
        auto_detect = self.config['processing']['auto_detect_workers']
        min_workers = self.config['processing']['min_workers']
        max_workers = self.config['processing']['max_workers']

        if auto_detect:
            # Use number of units, capped by min/max
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()

            # Optimal is min(units, cpu_count/2, max_workers)
            optimal = min(len(units), cpu_count // 2, max_workers)
            optimal = max(optimal, min_workers)

            return optimal
        else:
            # Use configured default (4)
            return min(4, max_workers)

    def _estimate_processing_time(self, units: List[ProcessingUnit]) -> float:
        """
        Estimate processing time in seconds.

        Rough estimate based on page count and historical performance.

        Args:
            units: List of processing units

        Returns:
            Estimated time in seconds
        """
        # Rough estimate: 5 seconds per page (conservative)
        total_pages = sum(unit.page_count for unit in units)
        return total_pages * 5.0


# Testing
if __name__ == "__main__":
    print("Testing Hierarchical Processing Planner...")
    print("=" * 70)

    # Test 1: Small chapter (no subdivision)
    print("\n1. Small Chapter (34 pages, no subdivision)")
    try:
        from .data_structures import SectionType
    except ImportError:
        from data_structures import SectionType

    small_section = LogicalSection(
        section_type=SectionType.CHAPTER,
        section_number="4",
        title="Heat Transfer",
        start_page=0,
        end_page=33,
        confidence=0.95,
        detection_method="pattern_numbered_chapter"
    )

    small_structure = DocumentStructure(
        document_path=Path("Ch-04_Heat_Transfer.pdf"),
        total_pages=34,
        sections=[small_section],
        root_sections=["chapter_4"],
        has_hierarchical_structure=True
    )

    planner = HierarchicalProcessingPlanner()
    plan = planner.create_plan(small_structure)

    print(f"   Units created: {plan.total_units}")
    print(f"   Units with subdivision: {plan.units_requiring_subdivision}")
    print(f"   Optimal workers: {plan.optimal_workers}")
    print(f"   Estimated time: {plan.estimated_processing_time_seconds:.1f}s")

    assert plan.total_units == 1, "Should create 1 unit"
    assert plan.units_requiring_subdivision == 0, "No subdivision needed"
    assert plan.processing_units[0].is_complete_section, "Should be complete section"
    print("   ✅ Small chapter test passed")

    # Test 2: Large chapter (needs subdivision)
    print("\n2. Large Chapter (300 pages, needs subdivision)")

    large_section = LogicalSection(
        section_type=SectionType.CHAPTER,
        section_number="5",
        title="Large Topic",
        start_page=0,
        end_page=299,
        confidence=0.95,
        detection_method="pattern_numbered_chapter"
    )

    large_structure = DocumentStructure(
        document_path=Path("Large_Chapter.pdf"),
        total_pages=300,
        sections=[large_section],
        root_sections=["chapter_5"],
        has_hierarchical_structure=True
    )

    plan_large = planner.create_plan(large_structure)

    print(f"   Units created: {plan_large.total_units}")
    print(f"   Units with subdivision: {plan_large.units_requiring_subdivision}")
    print(f"   Optimal workers: {plan_large.optimal_workers}")
    print(f"   Estimated time: {plan_large.estimated_processing_time_seconds:.1f}s")

    for i, unit in enumerate(plan_large.processing_units, 1):
        print(f"   Chunk {i}: pages {unit.start_page}-{unit.end_page} ({unit.page_count} pages)")

    assert plan_large.total_units == 3, "Should create 3 chunks"
    assert plan_large.units_requiring_subdivision == 3, "All units are chunks"
    assert all(not unit.is_complete_section for unit in plan_large.processing_units), "All should be chunks"

    # Check balanced distribution
    chunk_sizes = [unit.page_count for unit in plan_large.processing_units]
    print(f"   Chunk sizes: {chunk_sizes}")
    assert all(size == 100 for size in chunk_sizes), "Should be balanced 100-page chunks"
    print("   ✅ Large chapter test passed")

    # Test 3: Multiple sections
    print("\n3. Multiple Sections (mixed sizes)")

    section1 = LogicalSection(
        section_type=SectionType.CHAPTER,
        section_number="1",
        title="Introduction",
        start_page=0,
        end_page=19,
        confidence=0.95,
        detection_method="pattern_numbered_chapter"
    )

    section2 = LogicalSection(
        section_type=SectionType.CHAPTER,
        section_number="2",
        title="Methodology",
        start_page=20,
        end_page=169,
        confidence=0.95,
        detection_method="pattern_numbered_chapter"
    )

    multi_structure = DocumentStructure(
        document_path=Path("Multi_Chapter.pdf"),
        total_pages=170,
        sections=[section1, section2],
        root_sections=["chapter_1", "chapter_2"],
        has_hierarchical_structure=True
    )

    plan_multi = planner.create_plan(multi_structure)

    print(f"   Units created: {plan_multi.total_units}")
    print(f"   Chapter 1 (20 pages): {len(plan_multi.get_units_for_section('chapter_1'))} unit(s)")
    print(f"   Chapter 2 (150 pages): {len(plan_multi.get_units_for_section('chapter_2'))} unit(s)")

    assert plan_multi.total_units == 3, "Should create 3 units (1 + 2)"
    assert len(plan_multi.get_units_for_section('chapter_1')) == 1, "Chapter 1: 1 unit"
    assert len(plan_multi.get_units_for_section('chapter_2')) == 2, "Chapter 2: 2 chunks"
    print("   ✅ Multiple sections test passed")

    print("\n" + "=" * 70)
    print("✅ All planner tests passed!")
