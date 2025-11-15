#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Table Processing Pipeline - Orchestrator for Complete Table Extraction

This pipeline orchestrates the complete table extraction workflow by composing
specialized agents and helper classes:

1. TableDetectionAgent: Hybrid Docling + YOLO detection → Zones
2. Enhanced TableExtractionAgent: Extraction with note/diagram helpers → ExtractedObjects
3. TableExportAgent: Professional export → CSV/Excel files

Design Rationale:
-----------------
- **Composition Over Inheritance**: Agents are composed, not extended
- **Single Responsibility**: Each component has one job
- **Flexible Configuration**: Can enable/disable strategies
- **Clear Data Flow**: Zone → ExtractedObject → Files

This is the main entry point for table extraction workflows.

Usage:
------
>>> from table_processing_pipeline import TableProcessingPipeline
>>> pipeline = TableProcessingPipeline(pdf_path="document.pdf")
>>> results = pipeline.process()
>>> # results contains paths to CSV, Excel files and extracted objects
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
import time

# MANDATORY UTF-8 SETUP
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')

# Import specialized agents and helpers
# Import using proper v14 package structure (no sys.path manipulation)
from common.src.base.base_extraction_agent import Zone, ExtractedObject
from ..detection.table_detection_agent import TableDetectionAgent
from .table_note_extractor import TableNoteExtractor
from .table_diagram_extractor import TableDiagramExtractor
from .table_export_agent import TableExportAgent

# TODO: vision_table_extractor will be migrated in future phase
# from .vision_table_extractor import VisionTableExtractor
# Stubbed for now - vision extraction not critical for basic pipeline
VisionTableExtractor = None  # type: ignore

# Import pandas for data handling
import pandas as pd


class EnhancedTableExtractionAgent:
    """
    Enhanced table extraction using specialized helper classes.

    This is a refactored version that uses:
    - TableNoteExtractor for multi-strategy note detection
    - TableDiagramExtractor for embedded diagram extraction
    - Clean separation of concerns

    Unlike BaseExtractionAgent, this is a simple processing class
    focused solely on table extraction logic.
    """

    def __init__(self, pdf_path: Path, output_dir: Path):
        """
        Initialize enhanced table extraction.

        Args:
            pdf_path: Path to PDF
            output_dir: Output directory for extracted content
        """
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Open PDF
        self.pdf_doc = fitz.open(str(pdf_path))

        # Initialize helper classes
        self.note_extractor = TableNoteExtractor(pdf_path, self.pdf_doc)
        self.diagram_extractor = TableDiagramExtractor(pdf_path, self.pdf_doc, output_dir)
        self.vision_extractor = VisionTableExtractor(pdf_path, self.pdf_doc)

    def extract_from_zone(self, zone: Zone) -> Optional[ExtractedObject]:
        """
        Extract table data from zone using helper classes.

        Args:
            zone: Table zone from detection

        Returns:
            ExtractedObject with table data, notes, and diagrams
        """
        try:
            # Get markdown from zone metadata (if from Docling)
            markdown = zone.metadata.get('markdown', '')

            # If no markdown or empty markdown, use vision OCR fallback
            if not markdown or len(markdown.strip()) == 0:
                print(f"      🔍 Vision OCR fallback for {zone.zone_id} (image-embedded table)")
                structured_data = self.vision_extractor.extract_from_image(zone, self.output_dir)
                if not structured_data:
                    print(f"      ⚠️  Skipping {zone.zone_id}: Vision extraction failed")
                    return None
                markdown = ""  # No markdown for vision-extracted tables
            else:
                # Parse markdown to structured data
                structured_data = self._markdown_to_structured(markdown)

            # Extract notes using multi-strategy approach
            notes = self.note_extractor.extract_notes(zone)

            # Extract diagrams
            diagrams = self.diagram_extractor.extract_diagrams(zone)

            # Crop table image
            image_path = self._crop_table_image(zone)

            # Build ExtractedObject
            return ExtractedObject(
                id=zone.zone_id,
                type='table',
                page=zone.page,
                bbox=zone.bbox,
                content={
                    'structured_data': structured_data,
                    'markdown': markdown,
                    'notes': notes,
                    'diagrams': diagrams,
                    'image_path': str(image_path) if image_path else None
                },
                context={
                    'rows': len(structured_data['rows']),
                    'columns': len(structured_data['headers']),
                    'has_notes': len(notes) > 0,
                    'has_diagrams': len(diagrams) > 0
                },
                references={},
                metadata={
                    'source': zone.metadata.get('source', 'unknown'),
                    'confidence': zone.metadata.get('confidence', 0.0),
                    'extraction_method': structured_data.get('extraction_method', 'enhanced_pipeline_v1.0')
                }
            )

        except Exception as e:
            print(f"      ❌ Extraction failed for {zone.zone_id}: {e}")
            return None

    def _markdown_to_structured(self, markdown: str) -> Dict[str, Any]:
        """
        Convert markdown table to structured data.

        Args:
            markdown: Markdown table string

        Returns:
            Dictionary with 'headers' and 'rows'
        """
        try:
            # Use pandas to parse markdown
            from io import StringIO
            df = pd.read_csv(StringIO(markdown), sep='|', skipinitialspace=True)

            # Remove first/last empty columns (markdown table artifacts)
            df = df.iloc[:, 1:-1]

            # Clean column names
            df.columns = [str(col).strip() for col in df.columns]

            # Remove separator row (if present)
            df = df[~df.iloc[:, 0].astype(str).str.contains('^-+$', regex=True)]

            return {
                'headers': df.columns.tolist(),
                'rows': df.values.tolist()
            }

        except Exception as e:
            print(f"        Warning: Markdown parsing failed: {e}")
            # Fallback: return raw data
            return {
                'headers': ['Column 1'],
                'rows': [[markdown]]
            }

    def _crop_table_image(self, zone: Zone) -> Optional[Path]:
        """
        Crop table region as image.

        Args:
            zone: Table zone

        Returns:
            Path to cropped image
        """
        try:
            page = self.pdf_doc[zone.page - 1]
            x0, y0, x1, y1 = zone.bbox

            # Render at 300 DPI for quality
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat, clip=(x0, y0, x1, y1))

            # Save
            image_path = self.output_dir / f"{zone.zone_id}.png"
            pix.save(str(image_path))

            return image_path

        except Exception as e:
            print(f"        Warning: Image crop failed: {e}")
            return None

    def close(self):
        """Close PDF document."""
        if self.pdf_doc:
            self.pdf_doc.close()


class TableProcessingPipeline:
    """
    Complete table processing pipeline orchestrator.

    Composes specialized agents to provide end-to-end table extraction.
    """

    def __init__(
        self,
        pdf_path: Path,
        output_dir: Optional[Path] = None,
        docling_enabled: bool = True,
        yolo_enabled: bool = True,
        export_csv: bool = True,
        export_excel: bool = True
    ):
        """
        Initialize table processing pipeline.

        Args:
            pdf_path: Path to PDF document
            output_dir: Output directory (auto-generated if None)
            docling_enabled: Enable Docling detection
            yolo_enabled: Enable YOLO detection
            export_csv: Export CSV files
            export_excel: Export Excel file
        """
        self.pdf_path = Path(pdf_path)

        if output_dir is None:
            output_dir = Path("results/table_extraction") / self.pdf_path.stem

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.docling_enabled = docling_enabled
        self.yolo_enabled = yolo_enabled
        self.export_csv = export_csv
        self.export_excel = export_excel

        # Statistics
        self.stats = {
            'tables_detected': 0,
            'tables_extracted': 0,
            'tables_with_notes': 0,
            'tables_with_diagrams': 0,
            'csv_files': 0,
            'excel_files': 0,
            'total_time': 0.0
        }

    def process(self) -> Dict[str, Any]:
        """
        Run complete table processing pipeline.

        Returns:
            Results dictionary with:
            - extracted_objects: List[ExtractedObject]
            - csv_files: List[Path]
            - excel_files: List[Path]
            - statistics: Dict
        """
        start_time = time.time()

        print("\n" + "="*80)
        print("TABLE PROCESSING PIPELINE")
        print("="*80)
        print(f"PDF: {self.pdf_path.name}")
        print()

        # Step 1: Detection
        print("STEP 1: TABLE DETECTION")
        print("-" * 80)
        detector = TableDetectionAgent(
            pdf_path=self.pdf_path,
            docling_enabled=self.docling_enabled,
            yolo_enabled=self.yolo_enabled
        )
        zones = detector.detect_tables()
        self.stats['tables_detected'] = len(zones)
        print()

        # Step 2: Extraction
        print("STEP 2: TABLE EXTRACTION")
        print("-" * 80)
        extraction_dir = self.output_dir / "extractions"
        extractor = EnhancedTableExtractionAgent(self.pdf_path, extraction_dir)

        extracted_objects = []
        for zone in zones:
            print(f"  Processing {zone.zone_id} (page {zone.page})...")
            obj = extractor.extract_from_zone(zone)

            if obj:
                extracted_objects.append(obj)
                self.stats['tables_extracted'] += 1

                if obj.content.get('notes'):
                    self.stats['tables_with_notes'] += 1

                if obj.content.get('diagrams'):
                    self.stats['tables_with_diagrams'] += 1

                print(f"    ✅ Extracted ({obj.context['rows']} rows, {obj.context['columns']} cols)")
            else:
                print(f"    ⚠️  Skipped (no extractable data)")

        extractor.close()
        print()

        # Step 3: Export
        print("STEP 3: TABLE EXPORT")
        print("-" * 80)
        exporter = TableExportAgent(output_dir=self.output_dir)

        csv_files = []
        excel_files = []

        if self.export_csv:
            for obj in extracted_objects:
                csv_path = exporter.export_to_csv(obj)
                csv_files.append(csv_path)
                self.stats['csv_files'] += 1
            print(f"  ✅ Exported {len(csv_files)} CSV file(s)")

        if self.export_excel and extracted_objects:
            excel_path = exporter.export_to_excel(
                extracted_objects,
                excel_filename=f"{self.pdf_path.stem}_tables.xlsx"
            )
            excel_files.append(excel_path)
            self.stats['excel_files'] += 1
            print(f"  ✅ Exported Excel: {excel_path.name}")

        print()

        # Calculate total time
        self.stats['total_time'] = time.time() - start_time

        # Print summary
        self._print_summary()

        return {
            'extracted_objects': extracted_objects,
            'csv_files': csv_files,
            'excel_files': excel_files,
            'statistics': self.stats
        }

    def _print_summary(self):
        """Print processing summary."""
        print("="*80)
        print("PIPELINE SUMMARY")
        print("="*80)
        print(f"  Tables detected: {self.stats['tables_detected']}")
        print(f"  Tables extracted: {self.stats['tables_extracted']}")
        print(f"  Tables with notes: {self.stats['tables_with_notes']}")
        print(f"  Tables with diagrams: {self.stats['tables_with_diagrams']}")
        print(f"  CSV files created: {self.stats['csv_files']}")
        print(f"  Excel files created: {self.stats['excel_files']}")
        print(f"  Total time: {self.stats['total_time']:.1f}s")
        print("="*80)
        print()


if __name__ == "__main__":
    # Test on Chapter 4
    pdf_path = Path("tests/test_data/Ch-04_Heat_Transfer.pdf")

    if not pdf_path.exists():
        print(f"ERROR: Test PDF not found: {pdf_path}")
        sys.exit(1)

    # Run complete pipeline
    pipeline = TableProcessingPipeline(pdf_path)
    results = pipeline.process()

    # Show file locations
    print("OUTPUT FILES:")
    print(f"  Excel: {results['excel_files'][0] if results['excel_files'] else 'None'}")
    print(f"  CSV files: {len(results['csv_files'])} files in results/table_extraction/*/csv/")
    print()
