#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Equation Context Extraction Agent

Extracts descriptive text and variable definitions surrounding equations in PDF documents.
Uses spatial proximity, sentence parsing, and pattern matching to provide rich context.

Key Features:
    - Spatial context window (200px radius around equation)
    - Variable definition extraction ("where k is...")
    - Sentence boundary detection
    - Reference text matching ("Equation (N) shows...")
    - Preceding and following text extraction

Performance:
    - Target: >85% context extraction success
    - Handles 108 equations from Chapter 4 test document
    - Multi-pattern variable definition matching

Author: V11 Development Team
Created: 2025-10-10
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
import re
from datetime import datetime

# Set UTF-8 encoding for Windows console
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

# Third-party imports
import fitz  # PyMuPDF


class EquationContextExtractor:
    """Extracts descriptive context and variable definitions for equations.

    Uses spatial proximity and text analysis to extract rich context surrounding
    mathematical equations, including variable definitions, physical meaning, and
    related text.

    Attributes:
        pdf_path (Path): Path to PDF document
        spatial_window (int): Radius in pixels for context extraction (default: 200)
        min_confidence (float): Minimum confidence score for context (default: 0.5)
    """

    def __init__(
        self,
        pdf_path: Path,
        spatial_window: int = 200,
        min_confidence: float = 0.5
    ):
        """Initialize equation context extractor.

        Args:
            pdf_path: Path to PDF document
            spatial_window: Pixel radius for text extraction around equations
            min_confidence: Minimum confidence threshold for context extraction

        Raises:
            FileNotFoundError: If PDF file does not exist
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        self.spatial_window = spatial_window
        self.min_confidence = min_confidence

        # Variable definition patterns
        self.var_patterns = [
            re.compile(r'where\s+([A-Za-z_][A-Za-z0-9_]*)\s+is\s+(.+?)(?:[.,;]|$)', re.IGNORECASE),
            re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)(?:\(|$)'),
            re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\s+(?:represents?|denotes?)\s+(.+?)(?:[.,;]|$)', re.IGNORECASE),
        ]

        # Open PDF document
        self.doc = fitz.open(str(self.pdf_path))

    def extract_all_contexts(
        self,
        equation_metadata: List[Dict]
    ) -> Dict[str, Dict]:
        """Extract context for all equations in metadata.

        Args:
            equation_metadata: List of equation dicts with 'equation_number', 'page', 'filename'

        Returns:
            Dictionary mapping equation numbers to context data:
            {
                "1": {
                    "preceding_text": "...",
                    "following_text": "...",
                    "variable_definitions": {...},
                    "references": [...],
                    "confidence": 0.85,
                    "page": 2
                }
            }
        """
        results = {}

        for eq in equation_metadata:
            eq_number = eq['equation_number']
            page_num = eq['page']

            print(f"  Extracting context for Equation {eq_number} (page {page_num})...")

            context = self.extract_context_for_equation(
                eq_number,
                page_num,
                eq.get('filename')
            )

            if context:
                results[eq_number] = context
                conf = context['confidence']
                vars_count = len(context.get('variable_definitions', {}))
                print(f"    ✅ Confidence: {conf:.2f}, Variables: {vars_count}")
            else:
                print(f"    ⚠️  Limited context found")

        return results

    def extract_context_for_equation(
        self,
        eq_number: str,
        page_num: int,
        filename: Optional[str] = None
    ) -> Optional[Dict]:
        """Extract context for a specific equation.

        Args:
            eq_number: Equation identifier
            page_num: Page number (0-indexed)
            filename: Optional equation image filename

        Returns:
            Context data dictionary or None if extraction failed
        """
        if page_num < 0 or page_num >= len(self.doc):
            return None

        # Get equation bbox from filename if available
        eq_bbox = self._infer_equation_bbox(eq_number, page_num, filename)

        # Extract spatial window text
        window_text = self._extract_spatial_window(page_num, eq_bbox)

        if not window_text:
            return None

        # Parse context components
        context = {
            "equation_number": eq_number,
            "page": page_num,
            "preceding_text": self._extract_preceding_text(window_text, eq_bbox, page_num),
            "following_text": self._extract_following_text(window_text, eq_bbox, page_num),
            "variable_definitions": self._extract_variable_definitions(window_text),
            "references": self._extract_references(eq_number, window_text),
            "confidence": 0.0
        }

        # Calculate confidence based on extracted components
        context['confidence'] = self._calculate_confidence(context)

        return context if context['confidence'] >= self.min_confidence else context

    def _infer_equation_bbox(
        self,
        eq_number: str,
        page_num: int,
        filename: Optional[str] = None
    ) -> Optional[List[float]]:
        """Infer equation bounding box from page or filename.

        Args:
            eq_number: Equation number
            page_num: Page number
            filename: Equation image filename (may contain bbox info)

        Returns:
            Bounding box [x0, y0, x1, y1] or None
        """
        # Search for equation number on page to get approximate location
        page = self.doc[page_num]
        text_blocks = page.get_text("dict")["blocks"]

        # Look for equation number pattern "(N)"
        pattern = re.compile(rf'\({eq_number}\)')

        for block in text_blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    if pattern.search(span["text"]):
                        # Found equation number - return bbox
                        # Expand bbox to left for equation content
                        bbox = span["bbox"]
                        return [
                            max(0, bbox[0] - 180),  # 180px left of number
                            bbox[1] - 20,           # 20px above
                            bbox[2] + 20,           # 20px right
                            bbox[3] + 20            # 20px below
                        ]

        return None

    def _extract_spatial_window(
        self,
        page_num: int,
        eq_bbox: Optional[List[float]]
    ) -> str:
        """Extract text within spatial window around equation.

        Args:
            page_num: Page number
            eq_bbox: Equation bounding box

        Returns:
            Text within window
        """
        page = self.doc[page_num]

        if eq_bbox:
            # Define search window
            search_bbox = fitz.Rect(
                max(0, eq_bbox[0] - self.spatial_window),
                max(0, eq_bbox[1] - self.spatial_window),
                min(page.rect.width, eq_bbox[2] + self.spatial_window),
                min(page.rect.height, eq_bbox[3] + self.spatial_window)
            )

            # Extract text within window
            window_text = page.get_textbox(search_bbox)
        else:
            # Fallback: entire page text
            window_text = page.get_text()

        return window_text

    def _extract_preceding_text(
        self,
        window_text: str,
        eq_bbox: Optional[List[float]],
        page_num: int
    ) -> str:
        """Extract text immediately preceding the equation.

        Args:
            window_text: Text within spatial window
            eq_bbox: Equation bounding box
            page_num: Page number

        Returns:
            Preceding text (1-2 sentences)
        """
        # Split into sentences
        sentences = self._split_sentences(window_text)

        if not sentences:
            return ""

        # Return last 1-2 sentences (up to 200 chars)
        preceding = ""
        for sent in reversed(sentences[:len(sentences)//2]):  # First half
            if len(preceding) + len(sent) < 200:
                preceding = sent + " " + preceding
            else:
                break

        return preceding.strip()

    def _extract_following_text(
        self,
        window_text: str,
        eq_bbox: Optional[List[float]],
        page_num: int
    ) -> str:
        """Extract text immediately following the equation.

        Args:
            window_text: Text within spatial window
            eq_bbox: Equation bounding box
            page_num: Page number

        Returns:
            Following text (1-2 sentences)
        """
        # Split into sentences
        sentences = self._split_sentences(window_text)

        if not sentences:
            return ""

        # Return first 1-2 sentences from second half (up to 200 chars)
        following = ""
        for sent in sentences[len(sentences)//2:]:  # Second half
            if len(following) + len(sent) < 200:
                following += sent + " "
            else:
                break

        return following.strip()

    def _extract_variable_definitions(
        self,
        text: str
    ) -> Dict[str, str]:
        """Extract variable definitions from text.

        Args:
            text: Context text

        Returns:
            Dictionary mapping variables to their definitions
        """
        definitions = {}

        for pattern in self.var_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                var_name = match.group(1)
                var_def = match.group(2).strip()

                # Clean up definition
                var_def = var_def.rstrip('.,;')

                definitions[var_name] = var_def

        return definitions

    def _extract_references(
        self,
        eq_number: str,
        text: str
    ) -> List[str]:
        """Extract text that references this equation.

        Args:
            eq_number: Equation number
            text: Context text

        Returns:
            List of sentences referencing this equation
        """
        references = []

        # Patterns for equation references
        ref_patterns = [
            rf'Equation\s*\({eq_number}\)',
            rf'Eq\.\s*\({eq_number}\)',
            rf'equation\s*{eq_number}',
        ]

        for pattern_str in ref_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            if pattern.search(text):
                # Find sentence containing this reference
                sentences = self._split_sentences(text)
                for sent in sentences:
                    if pattern.search(sent):
                        references.append(sent.strip())

        return references

    def _split_sentences(
        self,
        text: str
    ) -> List[str]:
        """Split text into sentences.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Simple sentence splitting (can be improved)
        text = text.replace('\n', ' ')
        text = re.sub(r'\s+', ' ', text)

        # Split on period, question mark, exclamation
        sentences = re.split(r'[.!?]+\s+', text)

        return [s.strip() for s in sentences if s.strip()]

    def _calculate_confidence(
        self,
        context: Dict
    ) -> float:
        """Calculate confidence score for extracted context.

        Args:
            context: Context dictionary

        Returns:
            Confidence score (0-1)
        """
        score = 0.0

        # Preceding text (20%)
        if context.get('preceding_text'):
            score += 0.20

        # Following text (20%)
        if context.get('following_text'):
            score += 0.20

        # Variable definitions (40%)
        var_count = len(context.get('variable_definitions', {}))
        if var_count > 0:
            score += min(0.40, var_count * 0.10)

        # References (20%)
        if context.get('references'):
            score += 0.20

        return min(1.0, score)

    def save_results(
        self,
        results: Dict[str, Dict],
        output_path: Path
    ) -> None:
        """Save equation context results to JSON file.

        Args:
            results: Context data from extract_all_contexts()
            output_path: Path to output JSON file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Add metadata
        output_data = {
            "total_equations": len(results),
            "extraction_timestamp": datetime.now().isoformat(),
            "pdf_source": str(self.pdf_path),
            "contexts": results
        }

        with output_path.open('w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved equation contexts to: {output_path}")

    def __del__(self):
        """Clean up PDF document handle."""
        if hasattr(self, 'doc'):
            self.doc.close()
