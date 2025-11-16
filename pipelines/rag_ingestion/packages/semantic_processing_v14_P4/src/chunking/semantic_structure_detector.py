#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Semantic Structure Detector

Scans PDF documents to detect logical structure (chapters, sections, parts)
using regex patterns and font analysis.

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
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import yaml
import fitz  # PyMuPDF

try:
    from .data_structures import (
        SectionType,
        LogicalSection,
        DocumentStructure
    )
except ImportError:
    # Running as main - use absolute import
    from data_structures import (
        SectionType,
        LogicalSection,
        DocumentStructure
    )


class StructureDetectionError(Exception):
    """Custom exception for structure detection failures."""
    pass


class SemanticStructureDetector:
    """
    Detects logical document structure (chapters, sections, parts).

    Uses multiple detection methods:
    - Regex pattern matching on text
    - Font size/weight analysis
    - Position-based detection (top of page)
    - Confidence scoring

    Attributes:
        config (Dict[str, Any]): Configuration from semantic_chunking.yaml
        patterns (Dict[str, List[Dict]]): Compiled regex patterns
        version (str): Detector version
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize structure detector.

        Args:
            config_path: Path to configuration file (default: config/semantic_chunking.yaml)
        """
        self.version = "1.0.0"
        self.config = self._load_config(config_path)
        self.patterns = self._compile_patterns()

    def _load_config(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config file

        Returns:
            Configuration dictionary

        Raises:
            StructureDetectionError: If config file not found or invalid
        """
        if config_path is None:
            # Default location
            config_path = Path(__file__).parent.parent.parent / "config" / "semantic_chunking.yaml"

        if not config_path.exists():
            raise StructureDetectionError(f"Config file not found: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            raise StructureDetectionError(f"Failed to load config: {e}")

    def _compile_patterns(self) -> Dict[str, List[Dict]]:
        """
        Compile regex patterns from configuration.

        Returns:
            Dictionary of compiled patterns by type
        """
        patterns = {
            'chapter': [],
            'section': []
        }

        # Compile chapter patterns
        for pattern_config in self.config['structure_detection']['chapter_patterns']:
            patterns['chapter'].append({
                'regex': re.compile(pattern_config['pattern'], re.MULTILINE),
                'confidence': pattern_config['confidence'],
                'type': pattern_config['type']
            })

        # Compile section patterns
        for pattern_config in self.config['structure_detection']['section_patterns']:
            patterns['section'].append({
                'regex': re.compile(pattern_config['pattern'], re.MULTILINE),
                'confidence': pattern_config['confidence'],
                'type': pattern_config['type']
            })

        return patterns

    def detect(self, pdf_path: Path) -> DocumentStructure:
        """
        Detect document structure from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            DocumentStructure with detected logical sections

        Raises:
            StructureDetectionError: If PDF cannot be opened or processed
        """
        if not pdf_path.exists():
            raise StructureDetectionError(f"PDF file not found: {pdf_path}")

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            raise StructureDetectionError(f"Failed to open PDF: {e}")

        total_pages = len(doc)
        sections: List[LogicalSection] = []

        # Scan all pages if configured
        if self.config['structure_detection']['scan_entire_document']:
            sections = self._scan_all_pages(doc)
        else:
            # Scan only first/last pages (faster, less accurate)
            sections = self._scan_partial(doc)

        # Build document structure
        structure = DocumentStructure(
            document_path=pdf_path,
            total_pages=total_pages,
            sections=sections,
            root_sections=[s.section_id for s in sections if s.level == 0],
            detection_method="semantic_pattern_matching",
            detection_confidence=self._calculate_overall_confidence(sections),
            has_hierarchical_structure=len(sections) > 0
        )

        doc.close()
        return structure

    def _scan_all_pages(self, doc: fitz.Document) -> List[LogicalSection]:
        """
        Scan all pages for structure.

        Args:
            doc: PyMuPDF document

        Returns:
            List of detected logical sections
        """
        # First pass: detect all potential sections
        candidates: List[Tuple[int, LogicalSection]] = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Try pattern-based detection
            detected = self._detect_on_page(page, page_num)

            if detected:
                candidates.append((page_num, detected))

            # Try font-based detection if pattern failed
            if not detected and self.config['structure_detection']['font_detection']['enabled']:
                font_detected = self._detect_by_font(page, page_num)
                if font_detected:
                    candidates.append((page_num, font_detected))

        # Second pass: filter out headers/footers (repeated low-confidence text)
        filtered_candidates = self._filter_repeated_headers(candidates)

        # Third pass: keep only chapter-level sections (not subsections)
        # Only CHAPTER and PART are true section boundaries
        chapter_level_sections = []
        for page_num, section in filtered_candidates:
            if section.section_type in (SectionType.CHAPTER, SectionType.PART):
                chapter_level_sections.append((page_num, section))

        # Fourth pass: validate chapter sequence (remove unlikely chapters)
        chapter_level_sections = self._validate_chapter_sequence(
            chapter_level_sections,
            len(doc)
        )

        # If no chapters found, return single unknown section
        if not chapter_level_sections:
            return [
                LogicalSection(
                    section_type=SectionType.UNKNOWN,
                    section_number=None,
                    title="Complete Document",
                    start_page=0,
                    end_page=len(doc) - 1,
                    confidence=0.50,
                    detection_method="fallback_full_document"
                )
            ]

        # Build final sections with proper spans
        sections: List[LogicalSection] = []
        for i, (page_num, section) in enumerate(chapter_level_sections):
            # If first chapter detected within first 3 pages, extend back to page 0
            # (Common case: chapter PDFs where title page is separate)
            if i == 0 and page_num <= 3:
                section.start_page = 0
            else:
                section.start_page = page_num

            # End page is start of next section - 1, or end of document
            if i < len(chapter_level_sections) - 1:
                next_page = chapter_level_sections[i + 1][0]
                section.end_page = next_page - 1
            else:
                section.end_page = len(doc) - 1

            section.page_count = section.end_page - section.start_page + 1

            # Check if subdivision needed
            max_pages = self.config['memory']['max_unit_pages']
            section.requires_subdivision = section.page_count > max_pages

            sections.append(section)

        return sections

    def _filter_repeated_headers(
        self,
        candidates: List[Tuple[int, LogicalSection]]
    ) -> List[Tuple[int, LogicalSection]]:
        """
        Filter out repeated headers/footers.

        Args:
            candidates: List of (page_num, section) tuples

        Returns:
            Filtered list without repeated low-confidence sections
        """
        if len(candidates) <= 2:
            return candidates

        # Count occurrences of each title
        title_counts: Dict[str, int] = {}
        for _, section in candidates:
            title_key = section.title or section.section_number or "unknown"
            title_counts[title_key] = title_counts.get(title_key, 0) + 1

        # Filter: keep if high confidence (>=0.85) OR appears only once or twice
        filtered = []
        for page_num, section in candidates:
            title_key = section.title or section.section_number or "unknown"
            count = title_counts[title_key]

            # Keep if:
            # - High confidence (>=0.85) OR
            # - Appears on <= 2 pages (not a header/footer)
            if section.confidence >= 0.85 or count <= 2:
                filtered.append((page_num, section))

        return filtered

    def _validate_chapter_sequence(
        self,
        chapters: List[Tuple[int, LogicalSection]],
        total_pages: int
    ) -> List[Tuple[int, LogicalSection]]:
        """
        Validate chapter sequence and remove unlikely chapters.

        Args:
            chapters: List of (page_num, section) tuples
            total_pages: Total pages in document

        Returns:
            Filtered list with validated chapters
        """
        if len(chapters) <= 1:
            return chapters

        # For small documents (<100 pages), be very conservative
        # Only keep first chapter if multiple detected
        if total_pages < 100 and len(chapters) > 1:
            # Check if chapter numbers are sequential
            chapter_nums = []
            for _, section in chapters:
                if section.section_number:
                    try:
                        chapter_nums.append(int(section.section_number))
                    except ValueError:
                        pass

            # If chapter numbers jump (e.g., 4 then 17), keep only first
            if len(chapter_nums) >= 2:
                gap = chapter_nums[1] - chapter_nums[0]
                if gap > 5:  # Non-sequential (gap > 5 chapters)
                    # Keep only first chapter
                    return [chapters[0]]

        return chapters

    def _detect_on_page(self, page: fitz.Page, page_num: int) -> Optional[LogicalSection]:
        """
        Detect structure on a single page using patterns.

        Args:
            page: PyMuPDF page
            page_num: Page number (0-indexed)

        Returns:
            LogicalSection if detected, None otherwise
        """
        # Extract text from top 20% of page (where headers usually are)
        page_rect = page.rect
        top_rect = fitz.Rect(
            page_rect.x0,
            page_rect.y0,
            page_rect.x1,
            page_rect.y0 + page_rect.height * 0.2
        )

        text = page.get_text("text", clip=top_rect).strip()
        if not text:
            return None

        # Try chapter patterns first (higher priority)
        for pattern_info in self.patterns['chapter']:
            match = pattern_info['regex'].search(text)
            if match:
                return self._create_section_from_match(
                    match,
                    pattern_info,
                    page_num,
                    SectionType.CHAPTER
                )

        # Try section patterns
        for pattern_info in self.patterns['section']:
            match = pattern_info['regex'].search(text)
            if match:
                return self._create_section_from_match(
                    match,
                    pattern_info,
                    page_num,
                    SectionType.SECTION
                )

        return None

    def _create_section_from_match(
        self,
        match: re.Match,
        pattern_info: Dict,
        page_num: int,
        section_type: SectionType
    ) -> LogicalSection:
        """
        Create LogicalSection from regex match.

        Args:
            match: Regex match object
            pattern_info: Pattern configuration
            page_num: Starting page number
            section_type: Type of section

        Returns:
            LogicalSection object
        """
        # Extract section number and title from match groups
        groups = match.groups()
        section_number = groups[0] if len(groups) > 0 else None
        title = groups[1] if len(groups) > 1 else None

        # Clean title
        if title:
            title = title.strip()

        # Validate chapter number (filter out false positives like "see Chapter 17")
        confidence = pattern_info['confidence']
        if section_type == SectionType.CHAPTER and section_number:
            try:
                chapter_num = int(section_number)
                # If chapter number is way too high (>20) and late in document,
                # likely a false positive reference
                if chapter_num > 20 and page_num > 10:
                    confidence *= 0.5  # Reduce confidence
            except ValueError:
                pass  # Roman numerals or other formats, keep original confidence

        return LogicalSection(
            section_type=section_type,
            section_number=section_number,
            title=title,
            start_page=page_num,
            end_page=page_num,  # Will be updated when next section found
            confidence=confidence,
            detection_method=f"pattern_{pattern_info['type']}"
        )

    def _detect_by_font(self, page: fitz.Page, page_num: int) -> Optional[LogicalSection]:
        """
        Detect structure using font analysis.

        Args:
            page: PyMuPDF page
            page_num: Page number

        Returns:
            LogicalSection if detected, None otherwise
        """
        font_config = self.config['structure_detection']['font_detection']

        # Get text with font information
        blocks = page.get_text("dict")["blocks"]

        # Find largest font size on page
        font_sizes = []
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        font_sizes.append(span["size"])

        if not font_sizes:
            return None

        avg_font_size = sum(font_sizes) / len(font_sizes)
        max_font_size = max(font_sizes)

        # Check if max font is significantly larger (indicates heading)
        min_ratio = font_config['min_size_ratio']
        if max_font_size >= avg_font_size * min_ratio:
            # Extract text with largest font
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            if span["size"] == max_font_size:
                                text = span["text"].strip()

                                # Try to extract number from text
                                number_match = re.search(r'\d+', text)
                                section_number = number_match.group(0) if number_match else None

                                return LogicalSection(
                                    section_type=SectionType.CHAPTER,
                                    section_number=section_number,
                                    title=text,
                                    start_page=page_num,
                                    end_page=page_num,
                                    confidence=0.70,  # Lower confidence for font-based
                                    detection_method="font_analysis"
                                )

        return None

    def _scan_partial(self, doc: fitz.Document) -> List[LogicalSection]:
        """
        Scan only first/last pages (faster, less accurate).

        Args:
            doc: PyMuPDF document

        Returns:
            List of detected sections
        """
        # Fallback: treat entire document as single unknown section
        return [
            LogicalSection(
                section_type=SectionType.UNKNOWN,
                section_number=None,
                title="Complete Document",
                start_page=0,
                end_page=len(doc) - 1,
                confidence=0.50,
                detection_method="fallback_full_document"
            )
        ]

    def _calculate_overall_confidence(self, sections: List[LogicalSection]) -> float:
        """
        Calculate overall detection confidence.

        Args:
            sections: List of detected sections

        Returns:
            Average confidence score
        """
        if not sections:
            return 0.0

        return sum(s.confidence for s in sections) / len(sections)


# Testing
if __name__ == "__main__":
    print("Testing Semantic Structure Detector...")
    print("=" * 70)

    # Test configuration loading
    print("\n1. Configuration Loading")
    try:
        detector = SemanticStructureDetector()
        print(f"   ✅ Detector initialized (version {detector.version})")
        print(f"   Chapter patterns: {len(detector.patterns['chapter'])}")
        print(f"   Section patterns: {len(detector.patterns['section'])}")
    except Exception as e:
        print(f"   ❌ Failed to initialize: {e}")
        sys.exit(1)

    # Test pattern compilation
    print("\n2. Pattern Compilation")
    test_texts = [
        ("Chapter 4 Heat Transfer", "numbered_chapter"),
        ("CHAPTER IV THERMODYNAMICS", "roman_chapter"),
        ("4. Heat Transfer", "numbered_section"),
        ("Part III Advanced Topics", "part")
    ]

    for text, expected_type in test_texts:
        matched = False
        for pattern_info in detector.patterns['chapter']:
            if pattern_info['regex'].search(text):
                matched = True
                print(f"   ✅ Matched '{text}' as {pattern_info['type']}")
                break

        if not matched:
            print(f"   ⚠️  No match for '{text}'")

    # Test on actual PDF if available
    print("\n3. PDF Structure Detection")
    test_pdf = Path("Ch-04_Heat_Transfer.pdf")

    if test_pdf.exists():
        print(f"   Testing on: {test_pdf}")
        try:
            structure = detector.detect(test_pdf)
            print(f"   ✅ Detection complete")
            print(f"   Total pages: {structure.total_pages}")
            print(f"   Sections found: {len(structure.sections)}")
            print(f"   Confidence: {structure.detection_confidence:.2f}")

            for i, section in enumerate(structure.sections, 1):
                print(f"\n   Section {i}:")
                print(f"     Type: {section.section_type.value}")
                print(f"     Display: {section.display_name}")
                print(f"     Pages: {section.start_page}-{section.end_page} ({section.page_count} pages)")
                print(f"     Method: {section.detection_method}")
                print(f"     Confidence: {section.confidence:.2f}")
        except Exception as e:
            print(f"   ❌ Detection failed: {e}")
    else:
        print(f"   ⚠️  Test PDF not found: {test_pdf}")
        print(f"   Skipping PDF test")

    print("\n" + "=" * 70)
    print("✅ Detector testing complete!")
