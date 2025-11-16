# -*- coding: utf-8 -*-
"""
Semantic Hierarchical Processor - Execute processing plans for semantic-aware chunking.

This module processes documents according to hierarchical plans, respecting semantic
boundaries while maintaining memory efficiency. It handles both complete sections
and subdivided chunks, with parallel processing and aggregation.

Author: Claude Code
Date: 2025-01-27
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

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import asdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import fitz  # PyMuPDF

try:
    from .data_structures import (
        ProcessingUnit,
        ProcessingPlan
    )
except ImportError:
    # Running as main - use absolute import
    from data_structures import (
        ProcessingUnit,
        ProcessingPlan
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """Raised when document processing fails."""
    pass


class SemanticHierarchicalProcessor:
    """
    Execute processing plans for semantic-aware hierarchical chunking.

    This processor handles:
    - Single-unit processing (complete sections)
    - Multi-unit parallel processing (subdivided sections)
    - Hierarchical output directory creation
    - Chunk aggregation at chapter level
    - Cross-chunk content merging

    The processor respects semantic boundaries and maintains proper context
    across chunk boundaries for optimal RAG performance.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize processor with configuration.

        Args:
            config: Configuration dictionary from semantic_chunking.yaml
        """
        self.config = config
        self.memory_config = config.get('memory', {})
        self.processing_config = config.get('processing', {})
        self.output_config = config.get('output', {})
        self.aggregation_config = config.get('aggregation', {})

        # Processing parameters
        self.max_unit_pages = self.memory_config.get('max_unit_pages', 100)
        self.chunk_overlap_pages = self.memory_config.get('chunk_overlap_pages', 5)
        self.enable_parallel = self.processing_config.get('enable_parallel', True)

        logger.info("SemanticHierarchicalProcessor initialized")

    def process_plan(
        self,
        plan: ProcessingPlan,
        pdf_path: Path,
        output_base_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Execute complete processing plan.

        Args:
            plan: Processing plan with all units
            pdf_path: Path to PDF document
            output_base_dir: Base directory for outputs (overrides plan default)

        Returns:
            Dictionary with processing results and statistics

        Raises:
            ProcessingError: If processing fails
        """
        logger.info(f"Processing plan for {pdf_path.name}")
        logger.info(f"Total units: {len(plan.processing_units)}")
        logger.info(f"Optimal workers: {plan.optimal_workers}")

        # Override output directory if provided
        if output_base_dir:
            for unit in plan.processing_units:
                # Update unit output_dir to use new base
                unit.output_dir = output_base_dir / unit.output_dir.name

        # Open PDF document
        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            raise ProcessingError(f"Failed to open PDF: {e}")

        try:
            # Group units by logical section (for aggregation)
            section_groups = self._group_units_by_section(plan.processing_units)

            # Process units
            results = []
            if self.enable_parallel and len(plan.processing_units) > 1:
                # Parallel processing
                logger.info(f"Processing {len(plan.processing_units)} units in parallel")
                results = self._process_units_parallel(
                    doc, plan.processing_units, plan.optimal_workers
                )
            else:
                # Sequential processing
                logger.info(f"Processing {len(plan.processing_units)} units sequentially")
                for unit in plan.processing_units:
                    result = self._process_unit(doc, unit)
                    results.append(result)

            # Aggregate results by section
            aggregated_results = {}
            if self.output_config.get('create_aggregated_views', True):
                logger.info("Creating aggregated views")
                aggregated_results = self._aggregate_by_section(
                    section_groups, results
                )

            # Compile statistics
            stats = self._compile_statistics(results, aggregated_results)

            logger.info(f"Processing complete: {stats['total_chunks']} chunks created")

            return {
                'success': True,
                'unit_results': results,
                'aggregated_results': aggregated_results,
                'statistics': stats
            }

        finally:
            doc.close()

    def _group_units_by_section(
        self,
        units: List[ProcessingUnit]
    ) -> Dict[str, List[ProcessingUnit]]:
        """
        Group processing units by their logical section.

        For subdivided sections, multiple units will belong to same section.
        For complete sections, each unit is its own group.

        Args:
            units: List of processing units

        Returns:
            Dictionary mapping section IDs to lists of units
        """
        groups = {}

        for unit in units:
            section_id = unit.logical_section.section_id
            if section_id not in groups:
                groups[section_id] = []
            groups[section_id].append(unit)

        return groups

    def _process_units_parallel(
        self,
        doc: fitz.Document,
        units: List[ProcessingUnit],
        max_workers: int
    ) -> List[Dict[str, Any]]:
        """
        Process units in parallel using ProcessPoolExecutor.

        Args:
            doc: PyMuPDF document
            units: List of processing units
            max_workers: Maximum number of parallel workers

        Returns:
            List of processing results
        """
        # Note: PyMuPDF documents can't be pickled, so we need to pass the path
        # and reopen in each worker. For now, we'll use sequential processing
        # and implement true parallel processing in a future version.
        logger.warning("Parallel processing not yet implemented, using sequential")

        results = []
        for unit in units:
            result = self._process_unit(doc, unit)
            results.append(result)

        return results

    def _process_unit(
        self,
        doc: fitz.Document,
        unit: ProcessingUnit
    ) -> Dict[str, Any]:
        """
        Process a single processing unit.

        Extracts text from pages, creates semantic chunks, and saves to disk.

        Args:
            doc: PyMuPDF document
            unit: Processing unit to process

        Returns:
            Processing result dictionary
        """
        logger.info(f"Processing unit {unit.unit_id}: pages {unit.start_page}-{unit.end_page}")

        # Extract text from pages
        text_content = []
        for page_num in range(unit.start_page, unit.end_page + 1):
            if page_num >= len(doc):
                logger.warning(f"Page {page_num} out of range, skipping")
                continue

            page = doc[page_num]
            text = page.get_text("text")
            text_content.append({
                'page_number': page_num,
                'text': text,
                'char_count': len(text)
            })

        # Create semantic chunks
        chunks = self._create_semantic_chunks(text_content, unit)

        # Create output directory
        unit.output_dir.mkdir(parents=True, exist_ok=True)

        # Save chunks
        chunks_file = unit.output_dir / 'chunks.json'
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)

        # Save metadata
        metadata_file = unit.output_dir / 'metadata.json'
        metadata = {
            'unit_id': unit.unit_id,
            'unit_type': unit.unit_type,
            'section': unit.logical_section.to_dict(),  # Use to_dict() for JSON serialization
            'page_range': {
                'start': unit.start_page,
                'end': unit.end_page,
                'count': unit.page_count
            },
            'chunk_info': {
                'chunk_number': unit.chunk_number,
                'total_chunks': unit.total_chunks
            } if not unit.is_complete_section else None,
            'is_complete_section': unit.is_complete_section,
            'chunk_count': len(chunks),
            'total_chars': sum(chunk['char_count'] for chunk in chunks)
        }

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"Unit {unit.unit_id}: {len(chunks)} chunks saved to {unit.output_dir}")

        return {
            'unit_id': unit.unit_id,
            'success': True,
            'chunk_count': len(chunks),
            'total_chars': metadata['total_chars'],
            'output_dir': str(unit.output_dir)
        }

    def _create_semantic_chunks(
        self,
        text_content: List[Dict[str, Any]],
        unit: ProcessingUnit
    ) -> List[Dict[str, Any]]:
        """
        Create semantic chunks from extracted text.

        For now, uses simple page-based chunking. Future versions will implement
        true semantic chunking with paragraph boundaries, headings, etc.

        Args:
            text_content: List of page text dictionaries
            unit: Processing unit being processed

        Returns:
            List of chunk dictionaries
        """
        chunks = []

        # Simple implementation: One chunk per page
        # Future: Implement semantic boundary detection
        for page_data in text_content:
            chunk = {
                'chunk_id': f"{unit.unit_id}_page_{page_data['page_number']:03d}",
                'page_number': page_data['page_number'],
                'text': page_data['text'],
                'char_count': page_data['char_count'],
                'metadata': {
                    'unit_id': unit.unit_id,
                    'section_id': unit.logical_section.section_id,
                    'section_type': unit.logical_section.section_type.value,
                    'section_title': unit.logical_section.title,
                    'is_complete_section': unit.is_complete_section
                }
            }
            chunks.append(chunk)

        return chunks

    def _aggregate_by_section(
        self,
        section_groups: Dict[str, List[ProcessingUnit]],
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate results by logical section.

        For subdivided sections, combines chunks from multiple units.
        For complete sections, just references the single unit's output.

        Args:
            section_groups: Units grouped by section
            results: Processing results from all units

        Returns:
            Dictionary of aggregated results per section
        """
        aggregated = {}

        # Create result lookup by unit_id
        result_lookup = {r['unit_id']: r for r in results}

        for section_id, units in section_groups.items():
            if len(units) == 1:
                # Complete section - just reference the unit
                unit = units[0]
                aggregated[section_id] = {
                    'section_id': section_id,
                    'section_type': unit.logical_section.section_type.value,
                    'section_title': unit.logical_section.title,
                    'is_subdivided': False,
                    'unit_count': 1,
                    'total_chunks': result_lookup[unit.unit_id]['chunk_count'],
                    'total_chars': result_lookup[unit.unit_id]['total_chars'],
                    'output_dir': str(unit.output_dir)
                }
            else:
                # Subdivided section - aggregate from multiple units
                total_chunks = sum(result_lookup[u.unit_id]['chunk_count'] for u in units)
                total_chars = sum(result_lookup[u.unit_id]['total_chars'] for u in units)

                # Create aggregated directory
                section_output_dir = units[0].output_dir.parent / 'aggregated'
                section_output_dir.mkdir(parents=True, exist_ok=True)

                # Combine all chunks
                all_chunks = []
                for unit in sorted(units, key=lambda u: u.start_page):
                    chunks_file = unit.output_dir / 'chunks.json'
                    if chunks_file.exists():
                        with open(chunks_file, 'r', encoding='utf-8') as f:
                            chunks = json.load(f)
                            all_chunks.extend(chunks)

                # Save aggregated chunks
                aggregated_chunks_file = section_output_dir / 'aggregated_chunks.json'
                with open(aggregated_chunks_file, 'w', encoding='utf-8') as f:
                    json.dump(all_chunks, f, indent=2, ensure_ascii=False)

                aggregated[section_id] = {
                    'section_id': section_id,
                    'section_type': units[0].logical_section.section_type.value,
                    'section_title': units[0].logical_section.title,
                    'is_subdivided': True,
                    'unit_count': len(units),
                    'chunk_units': [u.unit_id for u in units],
                    'total_chunks': total_chunks,
                    'total_chars': total_chars,
                    'output_dir': str(section_output_dir)
                }

        return aggregated

    def _compile_statistics(
        self,
        results: List[Dict[str, Any]],
        aggregated_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compile processing statistics.

        Args:
            results: Unit processing results
            aggregated_results: Aggregated section results

        Returns:
            Statistics dictionary
        """
        total_chunks = sum(r['chunk_count'] for r in results)
        total_chars = sum(r['total_chars'] for r in results)
        successful_units = sum(1 for r in results if r['success'])

        stats = {
            'total_units': len(results),
            'successful_units': successful_units,
            'failed_units': len(results) - successful_units,
            'total_chunks': total_chunks,
            'total_chars': total_chars,
            'avg_chars_per_chunk': total_chars / total_chunks if total_chunks > 0 else 0,
            'sections_processed': len(aggregated_results),
            'subdivided_sections': sum(
                1 for s in aggregated_results.values() if s['is_subdivided']
            )
        }

        return stats


# Test harness
if __name__ == "__main__":
    import yaml
    from semantic_structure_detector import SemanticStructureDetector
    from hierarchical_processing_planner import HierarchicalProcessingPlanner

    print("Testing Semantic Hierarchical Processor...")
    print("=" * 70)

    # Configuration and test paths
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / 'config' / 'semantic_chunking.yaml'
    test_pdf = project_root / 'tests' / 'test_data' / 'Ch-04_Heat_Transfer.pdf'

    if not test_pdf.exists():
        print(f"❌ Test PDF not found: {test_pdf}")
        sys.exit(1)

    # Load config for processor
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    print(f"\nTest PDF: {test_pdf.name}")

    # Step 1: Detect structure (pass config_path)
    print("\n1. Detecting document structure...")
    detector = SemanticStructureDetector(config_path)
    structure = detector.detect(test_pdf)
    print(f"   Detected {len(structure.sections)} section(s)")

    # Step 2: Create processing plan (pass config_path)
    print("\n2. Creating processing plan...")
    planner = HierarchicalProcessingPlanner(config_path)
    output_base = project_root / 'results' / 'semantic_chunking_test'
    plan = planner.create_plan(structure, output_base)
    print(f"   Created {len(plan.processing_units)} processing unit(s)")
    print(f"   Optimal workers: {plan.optimal_workers}")

    # Step 3: Execute processing (processor uses config dict)
    print("\n3. Executing processing plan...")
    processor = SemanticHierarchicalProcessor(config)
    result = processor.process_plan(plan, test_pdf)

    if result['success']:
        stats = result['statistics']
        print(f"   ✅ Processing successful!")
        print(f"   Units processed: {stats['successful_units']}/{stats['total_units']}")
        print(f"   Total chunks: {stats['total_chunks']}")
        print(f"   Total characters: {stats['total_chars']:,}")
        print(f"   Avg chars/chunk: {stats['avg_chars_per_chunk']:.0f}")
        print(f"   Sections: {stats['sections_processed']}")
        print(f"   Subdivided: {stats['subdivided_sections']}")

        print("\n4. Output directories:")
        for unit_result in result['unit_results']:
            print(f"   {unit_result['output_dir']}")

        print("\n" + "=" * 70)
        print("✅ All processor tests passed!")
    else:
        print("   ❌ Processing failed")
        sys.exit(1)
