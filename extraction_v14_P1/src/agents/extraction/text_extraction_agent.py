#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Text Extraction Agent - RAG-Ready Text with Cross-References

Extracts text blocks with semantic chunking and reference detection.
Identifies mentions of equations, tables, and figures for cross-linking.

Author: Claude Code
Date: 2025-10-03
Version: 1.0
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import re

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

import fitz  # PyMuPDF

# Import base agent
# Import using proper v14 package structure (no sys.path manipulation)
from common.src.base.base_extraction_agent import BaseExtractionAgent, Zone, ExtractedObject


class TextExtractionAgent(BaseExtractionAgent):
    """
    Specialized agent for extracting text with cross-references.

    Focuses on:
    - Semantic chunking (paragraph-level)
    - Reference detection (Equation X, Table Y, Figure Z)
    - Context preservation
    """

    def __init__(self, pdf_path: Path, output_dir: Path):
        super().__init__(pdf_path, output_dir)
        self.agent_type = "text_extraction"
        self.agent_version = "1.0.0"

        self.text_dir = self.output_dir / "text"
        self.text_dir.mkdir(parents=True, exist_ok=True)

        self.doc = fitz.open(str(self.pdf_path))

    def extract_from_zone(self, zone: Zone) -> Optional[ExtractedObject]:
        """Extract text block with reference detection."""
        try:
            # Get text from bbox
            page = self.doc[zone.page - 1]
            text = self._extract_text_from_bbox(page, zone.bbox)

            if not text or len(text.strip()) < 10:  # Skip very short text
                return None

            # Detect references
            refs = self._detect_references(text)

            # Save text to file
            text_file = self.text_dir / f"{zone.zone_id}.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text.strip())

            return ExtractedObject(
                id=zone.zone_id,
                type="text",
                page=zone.page,
                bbox=zone.bbox,
                content={
                    "text": text.strip(),
                    "length": len(text.strip()),
                    "chunk_type": "paragraph"
                },
                context={
                    "description": "Text block",
                    "semantic_type": "body"
                },
                references=refs,
                metadata={
                    "extraction_method": "pymupdf_bbox",
                    "confidence": 1.0,
                    "text_file": str(text_file.relative_to(self.output_dir))
                },
                document_id=self.document_metadata.get("document_id"),
                zotero_key=self.document_metadata.get("zotero_key")
            )
        except Exception as e:
            print(f"    ❌ Exception: {e}")
            return None

    def _extract_text_from_bbox(self, page: fitz.Page, bbox: List[float]) -> str:
        """Extract text from bounding box."""
        try:
            page_height = float(page.rect.height)
            x0, y0, x1, y1 = bbox

            # Convert coordinates if needed
            y0_flip = page_height - y0
            y1_flip = page_height - y1
            y0_flip, y1_flip = min(y0_flip, y1_flip), max(y0_flip, y1_flip)

            rect = fitz.Rect(x0, y0_flip, x1, y1_flip)
            text = page.get_text("text", clip=rect)

            return text
        except:
            return ""

    def _detect_references(self, text: str) -> Dict[str, List[str]]:
        """Detect mentions of equations, tables, figures."""
        refs = {
            "equations": [],
            "tables": [],
            "figures": []
        }

        # Detect equation references
        eq_patterns = [
            r'Equation\s+(\d+[a-z]?)',
            r'equation\s+(\d+[a-z]?)',
            r'Eq\.\s+(\d+[a-z]?)',
            r'\((\d+[a-z]?)\)'  # Equation numbers in parentheses
        ]
        for pattern in eq_patterns:
            matches = re.findall(pattern, text)
            refs["equations"].extend([f"eq_{m}" for m in matches])

        # Detect table references
        table_patterns = [
            r'Table\s+(\d+[a-z]?)',
            r'table\s+(\d+[a-z]?)'
        ]
        for pattern in table_patterns:
            matches = re.findall(pattern, text)
            refs["tables"].extend([f"table_{m}" for m in matches])

        # Detect figure references
        fig_patterns = [
            r'Figure\s+(\d+[a-z]?)',
            r'figure\s+(\d+[a-z]?)',
            r'Fig\.\s+(\d+[a-z]?)',
            r'fig\.\s+(\d+[a-z]?)'
        ]
        for pattern in fig_patterns:
            matches = re.findall(pattern, text)
            refs["figures"].extend([f"fig_{m}" for m in matches])

        # Remove duplicates
        refs["equations"] = list(set(refs["equations"]))
        refs["tables"] = list(set(refs["tables"]))
        refs["figures"] = list(set(refs["figures"]))

        return refs

    def __del__(self):
        if hasattr(self, 'doc'):
            self.doc.close()
