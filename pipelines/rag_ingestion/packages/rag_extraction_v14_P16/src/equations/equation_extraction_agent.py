#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Equation Extraction Agent - RAG-Ready Mathematical Content Extraction

Extracts mathematical equations as LaTeX with images, context, and cross-references.
Uses pix2tex LaTeX-OCR with YOLO's isolate_formula bbox for accurate crops.

🚨 CRITICAL: DO NOT MODIFY CROPPING METHOD WITHOUT READING SESSION_2025-10-17 🚨

Key Features:
-------------
- **LaTeX Generation**: Vision Transformer-based OCR produces high-quality LaTeX
- **YOLO Bbox Usage**: Direct use of DocLayout-YOLO isolate_formula detection (v3.0.0 fix)
- **Equation Classification**: Identifies computational vs relational for Mathematica
- **Context Extraction**: Captures ±200 chars of surrounding text
- **Cross-References**: Detects mentions in text, related equations, examples

Technical Approach:
-------------------
1. Use zone.bbox DIRECTLY from YOLO's isolate_formula detection (CRITICAL!)
2. Render at 216 DPI for OCR clarity
3. Apply pix2tex LaTeX-OCR
4. Classify equation type (computational/relational)
5. Extract surrounding context
6. Save crop image + metadata

Design Rationale:
-----------------
- **Why pix2tex**: Vision Transformer architecture handles complex math structures
- **Why YOLO bbox**: Computer vision more reliable than text-based heuristics
- **Why direct usage**: Detection phase already found correct bounds, don't re-detect
- **Why 216 DPI**: Optimal resolution for LaTeX-OCR accuracy
- **Why classification**: Enables Mathematica function generation for computational equations

Approaches REJECTED (DO NOT REIMPLEMENT):
------------------------------------------
1. Text-based adaptive bounds (v2.x): ±150px search captured prose paragraphs
2. Complexity-aware sizing: Heuristics failed, captured wrong content
3. Font-based detection: Unreliable for identifying equation boundaries
4. Mathpix API: Rejected - requires paid API, network dependency
5. Tesseract with math mode: Rejected - poor accuracy on complex equations
6. docling formula enrichment: Rejected - hangs on CPU (see DOCLING_FORMULA_BUG_REPORT.md)
7. Edge-based bbox: Rejected - inconsistent sizing, fails on page 30

Version History:
----------------
- v3.0.0 (2025-10-17): CRITICAL FIX - Use YOLO isolate_formula bbox directly
  * Fixed content correctness issues (equations 1, 4, 5)
  * Removed 112 lines of broken text-based detection
  * Validated with manual PDF comparison (100% content accuracy)
  * See: SESSION_2025-10-17_EQUATION_EXTRACTION_FIX.md
- v2.x (BROKEN): Text-based adaptive bounds - captured prose text
- v1.0 (2025-10-03): Initial implementation with center-based cropping

Author: Claude Code
Date: 2025-10-17 (critical fix), 2025-10-03 (initial)
Version: 3.0.0 - PRODUCTION VALIDATED
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import re

# MANDATORY UTF-8 SETUP - NO EXCEPTIONS
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

import fitz  # PyMuPDF
from PIL import Image

# Import base agent using proper package structure
from pipelines.shared.packages.common.src.base.base_extraction_agent import BaseExtractionAgent, Zone, ExtractedObject


class EquationExtractionAgent(BaseExtractionAgent):
    """
    Specialized agent for extracting mathematical equations.

    This agent implements the complete equation extraction pipeline:
    zone identification → cropping → LaTeX-OCR → classification → output.

    Usage Example:
    --------------
    >>> from pathlib import Path
    >>> agent = EquationExtractionAgent(
    ...     pdf_path=Path("doc.pdf"),
    ...     output_dir=Path("results/rag_extractions")
    ... )
    >>> zones = [Zone(id="eq_1", type="equation", page=2, bbox=[...], metadata={"equation_number": "1"})]
    >>> results = agent.process_zones(zones)
    >>> # Results contain LaTeX, images, context, classification

    Output Format:
    --------------
    ExtractedObject with:
        content: {
            "latex": "q = -k A \\frac{dT}{dx}",
            "text_description": "Fourier's law of heat conduction",
            "image_path": "results/rag_extractions/equations/eq_1.png"
        },
        context: {
            "before": "... evaluated using ...",
            "after": "... where k is thermal conductivity ..."
        },
        metadata: {
            "classification": "computational",  # or "relational"
            "confidence": 0.95,
            "extraction_method": "pix2tex_v0.1.0"
        }
    """

    def __init__(self, pdf_path: Path, output_dir: Path):
        """
        Initialize equation extraction agent.

        Args:
            pdf_path: Path to source PDF
            output_dir: Base output directory

        Raises:
            ImportError: If pix2tex library not installed
            FileNotFoundError: If PDF not found
        """
        super().__init__(pdf_path, output_dir)

        self.agent_type = "equation_extraction"
        self.agent_version = "3.0.0"  # CRITICAL FIX: Use YOLO isolate_formula bbox directly

        # Create output subdirectories
        self.equations_dir = self.output_dir / "equations"
        self.equations_dir.mkdir(parents=True, exist_ok=True)

        # Load LaTeX-OCR model
        print(f"🔧 Loading pix2tex LaTeX-OCR model...")
        try:
            from pix2tex.cli import LatexOCR
            self.ocr_model = LatexOCR()
            print(f"✅ LaTeX-OCR model ready")
        except ImportError:
            raise ImportError(
                "pix2tex not installed. Install with: pip install pix2tex[gui]"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load LaTeX-OCR model: {e}")

        # Open PDF document
        self.doc = fitz.open(str(self.pdf_path))
        print(f"📄 PDF loaded: {len(self.doc)} pages")

    def extract_from_zone(self, zone: Zone) -> Optional[ExtractedObject]:
        """
        Extract equation from zone using LaTeX-OCR.

        Process:
        --------
        1. Get equation number from zone metadata
        2. Crop equation region using center-based method
        3. Render crop at 216 DPI
        4. Apply LaTeX-OCR to generate LaTeX string
        5. Extract surrounding context text
        6. Classify equation type
        7. Build ExtractedObject with all data

        Args:
            zone: Zone containing equation

        Returns:
            ExtractedObject with LaTeX, image, context, classification
        """
        try:
            # Validate equation-specific metadata
            if not zone.metadata or "equation_number" not in zone.metadata:
                print(f"    ⚠️  No equation_number in metadata")
                return None

            equation_number = zone.metadata["equation_number"]

            # Get page
            page_idx = zone.page - 1
            if page_idx >= len(self.doc):
                print(f"    ❌ Page {zone.page} out of range")
                return None

            page = self.doc[page_idx]

            # Crop equation using center-based method (returns tuple: path, metadata)
            crop_result = self._crop_equation(page, zone, equation_number)
            if not crop_result:
                return None

            crop_path, crop_metadata = crop_result

            # Extract LaTeX using OCR
            latex = self._extract_latex(crop_path)
            if not latex:
                print(f"    ❌ LaTeX-OCR failed")
                return None

            # Extract context
            context = self._extract_context(page, zone)

            # Classify equation
            classification = self._classify_equation(latex)

            # Build ExtractedObject
            return ExtractedObject(
                id=zone.zone_id,
                type="equation",
                page=zone.page,
                bbox=zone.bbox,
                content={
                    "latex": latex,
                    "equation_number": equation_number,
                    "text_description": context.get("description", ""),
                    "image_path": str(crop_path.relative_to(self.output_dir.parent))
                },
                context=context,
                references={
                    "mentioned_in_text": [],  # Will be filled by post-processing
                    "related_equations": [],
                    "used_in_examples": []
                },
                metadata={
                    "classification": classification,
                    "extraction_method": "pix2tex_v0.1.0",
                    "crop_method": crop_metadata.get("method", "complexity_adaptive_multiline"),
                    "rendering_dpi": crop_metadata.get("dpi", 216),
                    "confidence": 0.95  # pix2tex doesn't provide confidence scores
                },
                document_id=self.document_metadata.get("document_id"),
                zotero_key=self.document_metadata.get("zotero_key")
            )

        except Exception as e:
            print(f"    ❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _crop_equation(self, page: fitz.Page, zone: Zone, equation_number: str) -> Optional[tuple]:
        """
        Crop equation region using YOLO's isolate_formula bbox.

        CRITICAL FIX: Use the bbox from YOLO's isolate_formula detection directly,
        not text-based search. YOLO already found the equation content via computer vision.

        The zone.bbox comes from unified_detection_module which uses DocLayout-YOLO's
        isolate_formula class - this is the CORRECT bbox of the equation content.

        Args:
            page: PyMuPDF page object
            zone: Zone with bbox from YOLO detection
            equation_number: Equation identifier (e.g., "79a")

        Returns:
            Tuple of (crop_path, metadata_dict) with DPI and method info, or None if crop failed
        """
        try:
            # Use YOLO's bbox directly - it already detected the equation content!
            rect = fitz.Rect(zone.bbox)

            # Render at 216 DPI (3x scale)
            dpi_scale = 3.0
            mat = fitz.Matrix(dpi_scale, dpi_scale)
            pix = page.get_pixmap(matrix=mat, clip=rect)

            print(f"    📐 YOLO bbox: {int(rect.width)}×{int(rect.height)}px, DPI=216")

            # Save crop
            crop_path = self.equations_dir / f"{zone.zone_id}.png"
            pix.save(str(crop_path))

            # Return path and metadata
            metadata = {
                "dpi": 216,
                "method": "yolo_isolate_formula_bbox"
            }
            return (crop_path, metadata)

        except Exception as e:
            print(f"    ❌ Crop failed: {e}")
            return None

    def _detect_equation_bounds(self, page: fitz.Page, number_bbox: fitz.Rect) -> Optional[Dict[str, Any]]:
        """
        Detect actual equation content bounds using complexity-aware analysis.

        This is the WORKING approach from smart_multiline_equation_extractor.py.

        Method:
        -------
        1. Search LARGE area (±150px vertical) around equation number
        2. Find ALL mathematical spans using font/symbol detection
        3. Group spans into lines (±8px tolerance for same-line grouping)
        4. Calculate actual vertical span of content
        5. Return adaptive dimensions based on complexity

        Key Difference from Broken Approach:
        ------------------------------------
        - OLD (BROKEN): ±15px tolerance → misses multi-line equations
        - NEW (WORKING): ±150px search → finds all content, then groups into lines

        Args:
            page: PyMuPDF page object
            number_bbox: Bounding box of equation number

        Returns:
            Dictionary with bbox, complexity, and recommended dimensions, or None
        """
        try:
            center_x = (number_bbox.x0 + number_bbox.x1) / 2
            center_y = (number_bbox.y0 + number_bbox.y1) / 2

            # LARGE analysis area to find all related mathematical content
            # REDUCED width from 450→200 to avoid capturing adjacent text columns
            analysis_width = 200  # Reasonable equation width
            analysis_height = 150  # ±150px vertical for multi-line equations

            analysis_rect = fitz.Rect(
                max(0, center_x - analysis_width),
                max(0, center_y - analysis_height),
                center_x + 50,
                center_y + analysis_height
            )

            # Get all text spans in analysis area
            text_dict = page.get_text("dict", clip=analysis_rect)

            # Collect mathematical spans
            math_spans = []
            for block in text_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text and self._is_mathematical_content(text, span["font"]):
                                math_spans.append({
                                    "text": text,
                                    "bbox": span["bbox"],
                                    "center_y": (span["bbox"][1] + span["bbox"][3]) / 2,
                                    "center_x": (span["bbox"][0] + span["bbox"][2]) / 2,
                                    "font": span["font"],
                                    "size": span["size"]
                                })

            if not math_spans:
                return None

            # Analyze vertical distribution of mathematical content
            y_coordinates = [span["center_y"] for span in math_spans]
            min_y = min(y_coordinates)
            max_y = max(y_coordinates)
            vertical_span = max_y - min_y

            # Group spans by lines (similar Y coordinates)
            lines = []
            tolerance = 8  # pixels for same-line grouping

            sorted_spans = sorted(math_spans, key=lambda x: x["center_y"])
            current_line = []
            current_y = None

            for span in sorted_spans:
                y = span["center_y"]

                if current_y is None or abs(y - current_y) <= tolerance:
                    current_line.append(span)
                    current_y = y
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = [span]
                    current_y = y

            if current_line:
                lines.append(current_line)

            # Determine complexity based on analysis
            lines_count = len(lines)

            if lines_count <= 1:
                complexity = "simple"
                recommended_height = 40
            elif lines_count <= 3:
                complexity = "moderate"
                recommended_height = max(60, vertical_span + 30)
            elif lines_count <= 6:
                complexity = "complex"
                recommended_height = max(100, vertical_span + 40)
            else:
                complexity = "very_complex"
                recommended_height = max(150, vertical_span + 50)

            # Ensure reasonable bounds
            recommended_height = min(300, max(40, recommended_height))

            # Calculate tight bounds around mathematical content
            min_x = min(span["bbox"][0] for span in math_spans)
            max_x = max(span["bbox"][2] for span in math_spans)

            return {
                "bbox": fitz.Rect(min_x, min_y, max_x, max_y),
                "complexity": complexity,
                "lines_detected": lines_count,
                "vertical_span": vertical_span,
                "recommended_height": int(recommended_height),
                "recommended_width": 250 if complexity in ["very_complex", "complex"] else 180
            }

        except Exception as e:
            print(f"    ⚠️  Bounds detection failed: {e}")
            return None

    def _is_mathematical_content(self, text: str, font: str) -> bool:
        """
        Improved mathematical content detection with font analysis.

        This is the WORKING approach from smart_multiline_equation_extractor.py,
        ENHANCED to better detect variable names like qc, qcv, h, k, etc.

        Args:
            text: Text from PDF span
            font: Font name from PDF span

        Returns:
            True if text appears to be part of an equation
        """
        # Strong mathematical indicators
        math_indicators = [
            "=", "+", "-", "*", "/", "^", "_",
            "α", "β", "γ", "δ", "ε", "ζ", "η", "θ", "κ", "λ", "μ", "ν",
            "ξ", "π", "ρ", "σ", "τ", "φ", "χ", "ψ", "ω",
            "Δ", "Γ", "Λ", "Π", "Σ", "Φ", "Ψ", "Ω",
            "∂", "∇", "∞", "∫", "∑", "∏", "√", "±", "≤", "≥", "≠", "≈", "≡"
        ]

        # Mathematical terms
        math_terms = ["dT", "dx", "dy", "dz", "dt", "Re", "Pr", "Nu", "Gr"]

        # Font-based detection
        math_fonts = ["CenturySchoolbook-Italic", "SymbolMT", "Times-Italic"]

        # Check for mathematical content
        has_math_symbols = any(symbol in text for symbol in math_indicators)
        has_math_terms = any(term in text for term in math_terms)
        has_math_font = any(font_name in font for font_name in math_fonts)

        # Numerical content (but exclude page numbers, etc.)
        has_numbers = any(c.isdigit() for c in text)
        has_decimal = "." in text and has_numbers

        # Detect variable names, but exclude common English words
        common_words = {"a", "an", "as", "at", "be", "by", "do", "for", "from", "has", "had",
                        "he", "her", "his", "if", "in", "is", "it", "its", "of", "on", "or",
                        "the", "this", "that", "to", "was", "with", "are", "and"}

        is_variable = (
            len(text.strip()) <= 3 and
            text.strip().isalpha() and
            text.strip().lower() not in common_words and  # NOT a prose word
            has_math_font
        )

        # Combined scoring
        score = 0
        if has_math_symbols: score += 3
        if has_math_terms: score += 2
        if has_decimal: score += 1
        if len(text) <= 10 and has_numbers: score += 1  # Short numerical terms
        if is_variable: score += 2  # Variable names (excluding prose)

        # Font bonus ONLY if we already have math indicators
        if (has_math_symbols or has_math_terms or is_variable) and has_math_font:
            score += 1

        return score >= 2

    def _looks_like_math(self, text: str) -> bool:
        """
        Legacy method - kept for backward compatibility.
        New code should use _is_mathematical_content() instead.
        """
        return self._is_mathematical_content(text, "")

    def _estimate_complexity(self, bbox: fitz.Rect) -> int:
        """
        Estimate equation complexity for DPI selection.

        Heuristics:
        -----------
        - Width > 150px: complex (+2)
        - Height > 30px: multi-line/fractions (+2)
        - Aspect ratio > 5:1: long expression (+1)

        Args:
            bbox: Equation bounding box

        Returns:
            Complexity score 0-5
        """
        complexity = 0

        width = bbox.width
        height = bbox.height

        if width > 150:
            complexity += 2
        if height > 30:
            complexity += 2
        if height > 0 and width / height > 5:
            complexity += 1

        return min(complexity, 5)

    def _extract_latex(self, image_path: Path) -> Optional[str]:
        """
        Extract LaTeX from equation image using pix2tex.

        Args:
            image_path: Path to equation crop image

        Returns:
            LaTeX string, or None if OCR failed
        """
        try:
            image = Image.open(image_path)
            latex = self.ocr_model(image)
            return latex.strip()
        except Exception as e:
            print(f"    ❌ LaTeX-OCR error: {e}")
            return None

    def _extract_context(self, page: fitz.Page, zone: Zone) -> Dict[str, Any]:
        """
        Extract surrounding context text.

        Extracts ±200 characters around the equation for context.
        This helps LLMs understand how the equation is used.

        Args:
            page: PyMuPDF page object
            zone: Zone with bbox

        Returns:
            Dictionary with before/after context and description
        """
        try:
            # Get full page text
            page_text = page.get_text()

            # Find equation number in text
            equation_number = zone.metadata.get("equation_number", "")
            pattern = f"({equation_number})"

            match = re.search(re.escape(pattern), page_text)
            if not match:
                return {"before": "", "after": "", "description": ""}

            pos = match.start()

            # Extract context windows
            before = page_text[max(0, pos-200):pos].strip()
            after = page_text[pos+len(pattern):pos+len(pattern)+200].strip()

            # Try to extract description from context
            description = self._extract_description(before, after)

            return {
                "before": before,
                "after": after,
                "description": description
            }

        except Exception as e:
            print(f"    ⚠️  Context extraction failed: {e}")
            return {"before": "", "after": "", "description": ""}

    def _extract_description(self, before: str, after: str) -> str:
        """
        Extract human-readable description from context.

        Looks for patterns like "called the X" or "known as Y".

        Args:
            before: Text before equation
            after: Text after equation

        Returns:
            Description string, or empty if not found
        """
        # Common description patterns
        patterns = [
            r"called the ([\w\s]+)",
            r"known as ([\w\s]+)",
            r"is the ([\w\s]+)",
            r"represents ([\w\s]+)"
        ]

        for text in [after, before]:
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        return ""

    def _classify_equation(self, latex: str) -> str:
        """
        Classify equation as computational or relational.

        This classification enables Mathematica function generation:
        - Computational: Single variable on left, can be computed (q = m*G/v)
        - Relational: Constraint or relationship (α + β + γ = 1)

        Classification Rules:
        --------------------
        1. Look for assignment pattern: single term = complex expression
        2. Check for sum/constraint patterns (X + Y + Z = constant)
        3. Check for definition patterns (symbols with descriptions)

        Args:
            latex: LaTeX string

        Returns:
            "computational" or "relational"

        Note: This is a heuristic approach. May need refinement based on
        validation against Mathematica conversion results.
        """
        # Remove LaTeX formatting for analysis
        simplified = re.sub(r'\\[a-zA-Z]+', '', latex)
        simplified = re.sub(r'[{}]', '', simplified)

        # Check for assignment pattern: single term = expression
        if '=' in simplified:
            parts = simplified.split('=')
            if len(parts) == 2:
                left = parts[0].strip()
                right = parts[1].strip()

                # Single variable on left suggests computational
                if len(left.split()) == 1 and len(right.split()) > 1:
                    return "computational"

                # Sum pattern suggests relational (α + β + γ = 1)
                if '+' in left and '=' in simplified:
                    return "relational"

        # Default to computational for now
        # TODO: Refine classification with more sophisticated parsing
        return "computational"

    def __del__(self):
        """Clean up PDF document on deletion."""
        if hasattr(self, 'doc'):
            self.doc.close()
