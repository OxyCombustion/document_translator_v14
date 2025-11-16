#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Structure Detector - PDF Document Structure Heuristics

Detects document structure by scanning PDF content for:
- Chapters (Chapter 1, Chapter 2, etc.)
- Sections (4.1, 4.2, 4.1.1, etc.)
- Paper sections (Abstract, Methods, Results, Discussion)
- Table of contents
- References

Uses configurable regex patterns and scoring weights.

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

import re
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Import from document_classifier
try:
    from .document_classifier import DocumentStructure, StructureDetectionError
except ImportError:
    # Running as main - use absolute import
    from document_classifier import DocumentStructure, StructureDetectionError


class StructureDetector:
    """
    Detects document structure using content heuristics.

    Scans first/last pages of PDF for structural markers:
    - Chapter headers
    - Section numbering patterns
    - Paper structure (abstract, methods, results)
    - References section
    - Table of contents

    Scoring:
    - Each detected feature adds confidence
    - Multiple matches increase confidence
    - Weighted by importance
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize structure detector.

        Args:
            config: Configuration dictionary from YAML
        """
        self.config = config
        self.patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """
        Compile regex patterns from configuration.

        Returns:
            Dictionary of compiled patterns
        """
        pattern_config = self.config['structure_detection']['patterns']

        compiled = {}
        for name, pattern_str in pattern_config.items():
            try:
                compiled[name] = re.compile(pattern_str, re.MULTILINE | re.IGNORECASE)
            except re.error as e:
                print(f"   ⚠️  Invalid pattern '{name}': {e}")
                # Use fallback pattern
                compiled[name] = re.compile(r'(?!)', re.MULTILINE)  # Never matches

        return compiled

    def detect(self, pdf_path: Path) -> DocumentStructure:
        """
        Detect document structure from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            DocumentStructure with detected features

        Raises:
            StructureDetectionError: If PDF cannot be read
        """
        if not pdf_path.exists():
            raise StructureDetectionError(f"PDF not found: {pdf_path}")

        try:
            doc = fitz.open(str(pdf_path))

            # Get configuration
            scan_first = self.config['structure_detection']['scan_first_pages']
            scan_last = self.config['structure_detection']['scan_last_pages']

            # Extract text from relevant pages
            text_first = self._extract_text_from_pages(doc, 0, scan_first)
            text_last = self._extract_text_from_pages(
                doc,
                max(0, len(doc) - scan_last),
                len(doc)
            )
            combined_text = text_first + "\n\n" + text_last

            # Detect features
            structure = DocumentStructure()
            structure.page_count = len(doc)

            # Chapters
            chapter_matches = self.patterns['chapter'].findall(combined_text)
            structure.has_chapters = len(chapter_matches) > 0
            structure.chapter_count = len(set(chapter_matches))  # Unique chapters
            structure.chapter_matches = list(set(chapter_matches))[:5]  # First 5 unique

            # Sections (numbered like "4.1" or "4.1.2")
            section_matches = self.patterns['section'].findall(combined_text)
            structure.has_sections = len(section_matches) >= 3  # Need at least 3
            structure.section_count = len(set(section_matches))
            structure.section_matches = list(set(section_matches))[:10]  # First 10 unique

            # Subsections (3-level numbering like "4.1.2")
            subsection_matches = self.patterns['subsection'].findall(combined_text)
            structure.has_subsections = len(subsection_matches) >= 2

            # Paper structure elements
            structure.has_abstract = bool(self.patterns['abstract'].search(text_first))
            structure.has_references = bool(self.patterns['references'].search(text_last))
            structure.has_introduction = bool(self.patterns['introduction'].search(combined_text))
            structure.has_methods = bool(self.patterns['methods'].search(combined_text))
            structure.has_results = bool(self.patterns['results'].search(combined_text))
            structure.has_discussion = bool(self.patterns['discussion'].search(combined_text))
            structure.has_conclusion = bool(self.patterns['conclusion'].search(combined_text))

            doc.close()

            return structure

        except Exception as e:
            raise StructureDetectionError(f"Error detecting structure: {e}")

    def _extract_text_from_pages(
        self,
        doc: fitz.Document,
        start_page: int,
        end_page: int
    ) -> str:
        """
        Extract text from page range.

        Args:
            doc: PyMuPDF document
            start_page: Start page (0-indexed)
            end_page: End page (exclusive)

        Returns:
            Concatenated text from pages
        """
        text_parts = []

        for page_num in range(start_page, min(end_page, len(doc))):
            try:
                page = doc[page_num]
                text = page.get_text("text")
                text_parts.append(text)
            except Exception as e:
                print(f"   ⚠️  Error reading page {page_num + 1}: {e}")
                continue

        return "\n\n".join(text_parts)

    def calculate_confidence(self, structure: DocumentStructure) -> float:
        """
        Calculate confidence score for structure detection.

        Uses weighted scoring from configuration.

        Args:
            structure: Detected structure

        Returns:
            Confidence score (0.0 to 1.0)
        """
        weights = self.config['structure_detection']['scoring_weights']

        score = 0.0

        # Chapter detection (strong signal)
        if structure.has_chapters:
            score += weights['chapter_found']

        # Section detection (medium signal)
        if structure.has_sections:
            score += weights['section_found']

        # Abstract (paper indicator)
        if structure.has_abstract:
            score += weights['abstract_found']

        # References (completeness indicator)
        if structure.has_references:
            score += weights['references_found']

        # Table of contents (book indicator)
        # Note: TOC detection not yet implemented
        # if structure.has_toc:
        #     score += weights['toc_found']

        # Normalize to 0.0-1.0 range
        return min(1.0, score)


# Testing function
def main():
    """Test structure detector."""
    print("Testing Structure Detector...")
    print("=" * 70)

    # Load configuration
    import yaml
    config_path = Path(__file__).parent.parent.parent / "config" / "document_classification.yaml"

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Test 1: Pattern compilation
    print("\n1. Pattern Compilation")
    detector = StructureDetector(config)
    print(f"   Compiled {len(detector.patterns)} patterns")
    assert 'chapter' in detector.patterns, "Missing chapter pattern"
    assert 'section' in detector.patterns, "Missing section pattern"
    print("   ✅ Patterns compiled successfully")

    # Test 2: Structure detection (needs a real PDF)
    print("\n2. Structure Detection")

    # Try to find Chapter 4 PDF for testing
    test_pdf = Path("data/Ch-04_Heat_Transfer.pdf")
    if not test_pdf.exists():
        # Try alternative location
        test_pdf = Path("inputs/Chapter4_Heat_Transfer.pdf")

    if test_pdf.exists():
        print(f"   Testing with: {test_pdf.name}")

        try:
            structure = detector.detect(test_pdf)

            print(f"\n   Detected Structure:")
            print(f"   - Pages: {structure.page_count}")
            print(f"   - Chapters: {structure.has_chapters} (count: {structure.chapter_count})")
            print(f"   - Sections: {structure.has_sections} (count: {structure.section_count})")
            print(f"   - Abstract: {structure.has_abstract}")
            print(f"   - References: {structure.has_references}")
            print(f"   - Methods: {structure.has_methods}")

            if structure.chapter_matches:
                print(f"   - Chapter matches: {structure.chapter_matches}")
            if structure.section_matches:
                print(f"   - Section matches: {structure.section_matches[:5]}...")

            # Calculate confidence
            confidence = detector.calculate_confidence(structure)
            print(f"\n   Confidence: {confidence:.2f}")

            print("   ✅ Structure detection working")

        except StructureDetectionError as e:
            print(f"   ❌ Detection error: {e}")

    else:
        print(f"   ⚠️  No test PDF found at {test_pdf}")
        print("   ⏭️  Skipping structure detection test")

    # Test 3: Confidence calculation
    print("\n3. Confidence Calculation")

    # Test case: book with chapters
    structure = DocumentStructure(
        has_chapters=True,
        chapter_count=12,
        has_sections=True,
        section_count=45,
        has_references=True
    )
    confidence = detector.calculate_confidence(structure)
    print(f"   Book structure confidence: {confidence:.2f}")
    assert confidence >= 0.70, "Expected high confidence for book"

    # Test case: paper structure
    structure = DocumentStructure(
        has_abstract=True,
        has_methods=True,
        has_results=True,
        has_references=True,
        has_sections=True,
        section_count=8
    )
    confidence = detector.calculate_confidence(structure)
    print(f"   Paper structure confidence: {confidence:.2f}")
    assert confidence >= 0.60, "Expected medium-high confidence for paper"

    print("   ✅ Confidence calculation working")

    print("\n" + "=" * 70)
    print("✅ Structure detector tests passed!")


if __name__ == "__main__":
    main()
