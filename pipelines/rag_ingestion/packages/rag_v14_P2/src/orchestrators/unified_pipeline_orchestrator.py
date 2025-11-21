# -*- coding: utf-8 -*-
"""
Unified Pipeline Orchestrator - Thin Coordination Layer

This orchestrator coordinates the complete extraction pipeline:
1. Phase 1: Parallel detection (DocLayout-YOLO + Docling)
2. Phase 2: Parallel extraction (existing RAG agents)

Design Principles:
------------------
- **Thin Layer**: NO extraction logic - pure coordination
- **Reuse**: Calls existing working agents unchanged
- **Parallel**: Maximizes throughput with parallel execution
- **Clean Interface**: Simple input/output contract

Author: Claude Code
Date: 2025-01-16
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
from typing import Dict, List, Any
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import json
import shutil

# Import detection modules (absolute imports from package root)
# YOLO module with PyTorch 2.9+ compatibility fix
from pipelines.extraction.packages.detection_v14_P14.src.yolo.unified_detection_module import UnifiedDetectionModule
from pipelines.extraction.packages.detection_v14_P14.src.docling.docling_table_detector import DoclingTableDetector
from pipelines.extraction.packages.detection_v14_P14.src.docling.docling_figure_detector import DoclingFigureDetector
from pipelines.extraction.packages.detection_v14_P14.src.docling.docling_text_detector import DoclingTextDetector

# Import existing RAG agents (absolute imports from package root)
from pipelines.rag_ingestion.packages.rag_extraction_v14_P16.src.equations.equation_extraction_agent import EquationExtractionAgent
from pipelines.rag_ingestion.packages.rag_extraction_v14_P16.src.tables.table_extraction_agent import TableExtractionAgent
from pipelines.rag_ingestion.packages.rag_extraction_v14_P16.src.figures.figure_extraction_agent import FigureExtractionAgent
from pipelines.rag_ingestion.packages.rag_extraction_v14_P16.src.text.text_extraction_agent import TextExtractionAgent

# Import new validation and coordination agents
from pipelines.rag_ingestion.packages.analysis_validation_v14_P19.src.validation.document_reference_inventory_agent import DocumentReferenceInventoryAgent
from pipelines.extraction.packages.specialized_extraction_v14_P15.src.coordination.object_numbering_coordinator import ObjectNumberingCoordinator
from pipelines.rag_ingestion.packages.analysis_validation_v14_P19.src.validation.completeness_validation_agent import CompletenessValidationAgent
from pipelines.data_management.packages.metadata_v14_P13.src.bibliography.bibliography_extraction_agent import BibliographyExtractionAgent
from pipelines.extraction.packages.extraction_v14_P1.src.agents.table.table_export_agent import TableExportAgent

# Import structured output manager
from pipelines.extraction.packages.extraction_v14_P1.src.output.structured_output_manager import StructuredOutputManager


class UnifiedPipelineOrchestrator:
    """
    Thin orchestrator for coordinating complete extraction pipeline.

    This class has NO extraction logic - it only coordinates:
    - Parallel detection phase
    - Zone merging
    - Calling existing agents
    - Result aggregation
    """

    def __init__(self, model_path: str, output_dir: Path, clean_before_run: bool = True,
                 enable_structured_output: bool = True):
        """
        Initialize orchestrator.

        Args:
            model_path: Path to DocLayout-YOLO model
            output_dir: Base output directory for all extractions
            clean_before_run: If True, remove old extraction files before processing (default: True)
            enable_structured_output: If True, create hierarchical output structure (default: True)
        """
        self.model_path = model_path
        self.output_dir = Path(output_dir)
        self.clean_before_run = clean_before_run
        self.enable_structured_output = enable_structured_output
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _clean_output_directories(self):
        """
        Clean old extraction files from previous runs.

        This prevents accumulation of stale files from multiple test runs.
        Old files are removed, but the directory structure is preserved.
        """
        subdirs = ['equations', 'tables', 'figures', 'text']

        total_removed = 0
        for subdir in subdirs:
            dir_path = self.output_dir / subdir
            if dir_path.exists():
                # Count files before removal
                files = list(dir_path.glob('*'))
                count = len(files)

                # Remove directory and recreate
                shutil.rmtree(dir_path)
                dir_path.mkdir(parents=True, exist_ok=True)

                if count > 0:
                    print(f"  🧹 Cleaned {subdir}/: {count} old files removed")
                    total_removed += count

        if total_removed > 0:
            print(f"  ✅ Total cleanup: {total_removed} old files removed\n")
        else:
            print(f"  ✅ No old files found (clean start)\n")

    def process_document(self, pdf_path: Path, num_workers: int = 8) -> Dict[str, Any]:
        """
        Process complete document through unified pipeline.

        Workflow:
        ---------
        1. Phase 1: Parallel detection
           - DocLayout-YOLO (equations, figures, text)
           - Docling (tables)
        2. Zone merging
        3. Phase 2: Parallel extraction
           - EquationExtractionAgent (EXISTING)
           - TableExtractionAgent (EXISTING)
           - FigureExtractionAgent (EXISTING)
           - TextExtractionAgent (EXISTING)
        4. Result aggregation

        Args:
            pdf_path: Path to PDF file
            num_workers: Number of parallel workers for detection

        Returns:
            Dictionary with extracted objects by type
        """
        print(f"\n{'='*80}")
        print(f"UNIFIED PIPELINE ORCHESTRATOR")
        print(f"{'='*80}")
        print(f"PDF: {pdf_path}")
        print(f"Output: {self.output_dir}")
        print()

        # Clean old files if requested
        if self.clean_before_run:
            print("Cleaning old extraction files...")
            self._clean_output_directories()

        overall_start = datetime.now()

        # ==================================================================
        # PHASE 0: DOCUMENT REFERENCE INVENTORY
        # ==================================================================
        print(f"{'='*80}")
        print(f"PHASE 0: DOCUMENT REFERENCE INVENTORY")
        print(f"{'='*80}")
        print()

        inventory_start = datetime.now()

        # Scan document for all object references to establish expectations
        print("Scanning document for object references...")
        inventory_agent = DocumentReferenceInventoryAgent(pdf_path)
        inventory = inventory_agent.scan_document()

        # Save inventory for later comparison
        inventory_path = self.output_dir / "reference_inventory.json"
        inventory_agent.save_inventory(inventory, inventory_path)

        inventory_duration = (datetime.now() - inventory_start).total_seconds()
        print(f"Inventory phase complete in {inventory_duration:.1f}s")
        print()

        # ==================================================================
        # PHASE 1: DETECTION (Parallel)
        # ==================================================================
        print(f"{'='*80}")
        print(f"PHASE 1: PARALLEL DETECTION")
        print(f"{'='*80}")
        print()

        detection_start = datetime.now()

        # Initialize detectors
        unified_detector = UnifiedDetectionModule(self.model_path)
        docling_table_detector = DoclingTableDetector()
        docling_figure_detector = DoclingFigureDetector()
        docling_text_detector = DoclingTextDetector()

        # Run detections: YOLO in parallel, Docling sequentially (unpicklable results)
        print("Launching detection...")
        print("  - DocLayout-YOLO: equations (YOLO figures/text DISABLED)")
        print("  - Docling: tables + figures + text (semantic understanding)")
        print()

        # First: Run Docling once (for tables, figures, AND text)
        print("Running Docling conversion (tables + figures + text)...")
        docling_result = docling_table_detector.converter.convert(pdf_path)

        # Extract tables, figures, and text from same Docling result (sequential, can't pickle)
        print("Extracting Docling zones (tables + figures + text)...")
        docling_table_zones = docling_table_detector.detect_tables(pdf_path, docling_result)
        docling_figure_zones = docling_figure_detector.detect_figures(pdf_path, docling_result)
        docling_text_zones = docling_text_detector.detect_text(pdf_path, docling_result)

        # YOLO detection (can run separately, no dependency on Docling)
        print("Running YOLO detection (equations only)...")
        doclayout_zones = unified_detector.detect_all_objects(pdf_path, num_workers)

        detection_duration = (datetime.now() - detection_start).total_seconds()

        # Filter out YOLO figure and text zones (use Docling instead for better semantic understanding)
        doclayout_zones_filtered = [z for z in doclayout_zones if z.type == "equation"]

        print()
        print(f"YOLO zones (equations only): {len(doclayout_zones_filtered)}")
        print(f"  (Removed {len(doclayout_zones) - len(doclayout_zones_filtered)} YOLO figure/text zones)")
        print(f"Docling table zones: {len(docling_table_zones)}")
        print(f"Docling figure zones: {len(docling_figure_zones)}")
        print(f"Docling text zones: {len(docling_text_zones)}")
        print()

        # Merge zones (YOLO equations + Docling tables/figures/text)
        all_zones = doclayout_zones_filtered + docling_table_zones + docling_figure_zones + docling_text_zones

        print()
        print(f"Detection phase complete in {detection_duration:.1f}s")
        print(f"Total zones detected: {len(all_zones)}")
        print()

        # ==================================================================
        # PHASE 2: EXTRACTION (Existing Agents)
        # ==================================================================
        print(f"{'='*80}")
        print(f"PHASE 2: EXTRACTION (Existing RAG Agents)")
        print(f"{'='*80}")
        print()

        extraction_start = datetime.now()

        # Separate zones by type
        equation_zones = [z for z in all_zones if z.type == "equation"]
        table_zones = [z for z in all_zones if z.type == "table"]
        figure_zones = [z for z in all_zones if z.type == "figure"]
        text_zones = [z for z in all_zones if z.type == "text"]

        print(f"Zones by type:")
        print(f"  Equations: {len(equation_zones)}")
        print(f"  Tables: {len(table_zones)}")
        print(f"  Figures: {len(figure_zones)}")
        print(f"  Text: {len(text_zones)}")
        print()

        # Call existing agents (reuse working code!)
        results = {}

        # Equations
        if equation_zones:
            print("Calling EquationExtractionAgent (EXISTING)...")
            eq_agent = EquationExtractionAgent(pdf_path, self.output_dir)
            results['equations'] = eq_agent.process_zones(equation_zones)
            print()

        # Tables
        if table_zones:
            print("Calling TableExtractionAgent (EXISTING)...")
            tbl_agent = TableExtractionAgent(pdf_path, self.output_dir)
            results['tables'] = tbl_agent.process_zones(table_zones)
            print()

        # Figures
        if figure_zones:
            print("Calling FigureExtractionAgent (EXISTING)...")
            fig_agent = FigureExtractionAgent(pdf_path, self.output_dir)
            results['figures'] = fig_agent.process_zones(figure_zones)
            print()

        # Text
        if text_zones:
            print("Calling TextExtractionAgent (EXISTING)...")
            txt_agent = TextExtractionAgent(pdf_path, self.output_dir)
            results['text'] = txt_agent.process_zones(text_zones)
            print()

        extraction_duration = (datetime.now() - extraction_start).total_seconds()

        # ==================================================================
        # PHASE 2.5: OBJECT NUMBERING + BIBLIOGRAPHY
        # ==================================================================
        print(f"{'='*80}")
        print(f"PHASE 2.5: OBJECT NUMBERING + BIBLIOGRAPHY")
        print(f"{'='*80}")
        print()

        numbering_start = datetime.now()

        # Assign actual object numbers from captions
        print("Assigning actual object numbers from captions...")
        coordinator = ObjectNumberingCoordinator(pdf_path, document_title="Chapter 4")

        # Assign numbers to each type
        if table_zones:
            table_zones = coordinator.assign_table_numbers(table_zones)
        if figure_zones:
            figure_zones = coordinator.assign_figure_numbers(figure_zones)
        if equation_zones:
            equation_zones = coordinator.assign_equation_numbers(equation_zones)

        # Extract bibliography
        print("Extracting bibliographic references...")
        bib_agent = BibliographyExtractionAgent(grobid_url="http://localhost:8070")
        references = bib_agent.extract_bibliography(pdf_path)

        # Save bibliography
        bib_path = self.output_dir / "bibliography.json"
        bib_agent.save_bibliography(references, bib_path)

        numbering_duration = (datetime.now() - numbering_start).total_seconds()
        print(f"Numbering + bibliography phase complete in {numbering_duration:.1f}s")
        print()

        # ==================================================================
        # PHASE 3: EXPORT + VALIDATION
        # ==================================================================
        print(f"{'='*80}")
        print(f"PHASE 3: EXPORT + VALIDATION")
        print(f"{'='*80}")
        print()

        export_start = datetime.now()

        # Export tables to Excel with embedded images
        if results.get('tables'):
            print("Exporting tables to Excel with embedded images...")
            table_exporter = TableExportAgent(self.output_dir)
            export_results = table_exporter.export_all(results['tables'])
            print(f"  ✅ Exported {len(export_results.get('csv', []))} CSV files")
            print(f"  ✅ Exported {len(export_results.get('excel', []))} Excel files")
            print()

        # Validate completeness
        print("Validating extraction completeness...")
        validation_agent = CompletenessValidationAgent()

        # Build extracted zones dictionary for validation
        extracted_zones = {
            'tables': table_zones,
            'figures': figure_zones,
            'equations': equation_zones
        }

        # Run validation
        validation_reports = validation_agent.validate_completeness(inventory, extracted_zones)

        # Save validation reports
        validation_json_path = self.output_dir / "completeness_validation.json"
        validation_md_path = self.output_dir / "completeness_report.md"
        validation_agent.save_reports(validation_reports, validation_json_path)
        validation_agent.generate_actionable_report(validation_reports, validation_md_path)

        export_duration = (datetime.now() - export_start).total_seconds()
        print(f"Export + validation phase complete in {export_duration:.1f}s")
        print()

        overall_duration = (datetime.now() - overall_start).total_seconds()

        # ==================================================================
        # RESULTS SUMMARY
        # ==================================================================
        print(f"{'='*80}")
        print(f"PIPELINE COMPLETE")
        print(f"{'='*80}")
        print()

        print(f"Timing:")
        print(f"  Phase 0 (Inventory): {inventory_duration:.1f}s")
        print(f"  Phase 1 (Detection): {detection_duration:.1f}s")
        print(f"  Phase 2 (Extraction): {extraction_duration:.1f}s")
        print(f"  Phase 2.5 (Numbering + Bibliography): {numbering_duration:.1f}s")
        print(f"  Phase 3 (Export + Validation): {export_duration:.1f}s")
        print(f"  Total: {overall_duration:.1f}s")
        print()

        print(f"Results:")
        for obj_type, objects in results.items():
            print(f"  {obj_type}: {len(objects)} extracted")
        print(f"  bibliography: {len(references)} references")
        print()

        print(f"Completeness (expected vs found):")
        for obj_type, report in validation_reports.items():
            status_icon = "✅" if report.quality_grade in ['A', 'B'] else "⚠️" if report.quality_grade == 'C' else "❌"
            print(f"  {status_icon} {obj_type}: {report.found_count}/{report.expected_count} ({report.coverage_percent:.1f}% - Grade {report.quality_grade})")
        print()

        # Save summary
        summary = {
            'pdf': str(pdf_path),
            'output_dir': str(self.output_dir),
            'timing': {
                'detection_seconds': detection_duration,
                'extraction_seconds': extraction_duration,
                'total_seconds': overall_duration
            },
            'zones_detected': {
                'equations': len(equation_zones),
                'tables': len(table_zones),
                'figures': len(figure_zones),
                'text': len(text_zones),
                'total': len(all_zones)
            },
            'objects_extracted': {
                obj_type: len(objects)
                for obj_type, objects in results.items()
            },
            'timestamp': datetime.now().isoformat()
        }

        summary_file = self.output_dir / 'unified_pipeline_summary.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"Summary saved: {summary_file}")
        print()

        # ==================================================================
        # PHASE 4 (OPTIONAL): STRUCTURED OUTPUT ORGANIZATION
        # ==================================================================
        if self.enable_structured_output:
            print(f"{'='*80}")
            print(f"PHASE 4: HIERARCHICAL OUTPUT ORGANIZATION")
            print(f"{'='*80}")
            print()

            structured_start = datetime.now()

            try:
                # Create hierarchical view of outputs
                structured_output_dir = self.output_dir.parent / f"{self.output_dir.name}_structured"
                output_manager = StructuredOutputManager(
                    flat_output_dir=self.output_dir,
                    structured_output_dir=structured_output_dir,
                    pdf_path=pdf_path,
                    enable_structure_detection=True
                )

                organization_stats = output_manager.organize_outputs()

                structured_duration = (datetime.now() - structured_start).total_seconds()
                print(f"Hierarchical organization complete in {structured_duration:.1f}s")
                print(f"Structured output: {structured_output_dir}")
                print()

                # Add to summary
                summary['structured_output'] = {
                    'enabled': True,
                    'location': str(structured_output_dir),
                    'statistics': organization_stats
                }

            except Exception as e:
                print(f"⚠️  Structured output organization failed: {e}")
                print("   (Flat outputs are still available)")
                print()
                summary['structured_output'] = {
                    'enabled': False,
                    'error': str(e)
                }

            # Re-save summary with structured output info
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

        return {
            'results': results,
            'summary': summary
        }


def main():
    """Test unified pipeline on Chapter 4."""

    model_path = "E:/document_translator_v13/models/models/Layout/YOLO/doclayout_yolo_docstructbench_imgsz1280_2501.pt"
    pdf_path = Path("tests/test_data/Ch-04_Heat_Transfer.pdf")
    output_dir = Path("results/unified_pipeline")

    orchestrator = UnifiedPipelineOrchestrator(model_path, output_dir)
    result = orchestrator.process_document(pdf_path, num_workers=8)

    print(f"{'='*80}")
    print(f"TEST COMPLETE")
    print(f"{'='*80}")
    print()
    print("All extractions complete!")
    print(f"Check results in: {output_dir}")


if __name__ == "__main__":
    main()
