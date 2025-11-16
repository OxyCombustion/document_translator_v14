#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Figure Extraction Agent - RAG-Ready Visual Content Extraction

Extracts figures/diagrams as images with captions for RAG systems.
Includes plot/image classification to distinguish data-extractable content.

CRITICAL WARNING - DO NOT BREAK THIS! (2025-10-17)
==================================================
This agent was FIXED after deduplication logic caused failures:
- BROKEN v1.1.0: MD5 hash deduplication saved only 7/45 figures (84% false positive rate)
- WORKING v2.0.0: Each zone gets own file + plot/image classification (from Oct 2025 working version)

DO NOT re-add deduplication logic without validating against PDF content!

Author: Claude Code
Date: 2025-10-17
Version: 2.0.0
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import re
import io

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
import cv2
import numpy as np
from PIL import Image

# Import base agent (proper package import, no sys.path manipulation)
from pipelines.shared.packages.common.src.base.base_extraction_agent import BaseExtractionAgent, Zone, ExtractedObject


class PlotImageClassifier:
    """
    Classify figures as plots (data-extractable) vs images (visual-only).

    Uses 5 computer vision features:
    - Grid line detection (35% weight) - plots have gridlines
    - Axes detection (30% weight) - x/y coordinate systems
    - Curve detection (25% weight) - data plots
    - Text density analysis - axis labels
    - Color complexity (10% weight) - plots simpler than images

    Ported from working extract_figures_doclayout.py (Oct 2025).
    """

    def classify(self, image_array: np.ndarray) -> Tuple[str, float, dict]:
        """
        Classify a figure as plot, image, or uncertain.

        Args:
            image_array: numpy array of image (RGB or grayscale)

        Returns:
            (classification, confidence, characteristics)
            - classification: "plot", "image", or "uncertain"
            - confidence: 0.0 to 1.0
            - characteristics: dict with individual feature scores
        """
        characteristics = {}

        # Convert to grayscale if needed
        if len(image_array.shape) == 3:
            gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
        else:
            gray = image_array.copy()

        # Feature 1: Grid line detection (strong plot indicator)
        characteristics['grid_score'] = self._detect_grid_lines(gray)

        # Feature 2: Axes detection (x/y axes with tick marks)
        characteristics['axes_score'] = self._detect_axes(gray)

        # Feature 3: Line/curve detection (data plots)
        characteristics['curves_score'] = self._detect_curves(gray)

        # Feature 4: Text density (plots have axis labels)
        characteristics['text_density'] = self._estimate_text_density(gray)

        # Feature 5: Color variety (plots simpler, images more complex)
        if len(image_array.shape) == 3:
            characteristics['color_complexity'] = self._color_complexity(image_array)
        else:
            characteristics['color_complexity'] = 0.0

        # Decision logic
        plot_score = (
            characteristics['grid_score'] * 0.35 +
            characteristics['axes_score'] * 0.30 +
            characteristics['curves_score'] * 0.25 +
            (1.0 - characteristics['color_complexity']) * 0.10
        )

        image_score = (
            characteristics['color_complexity'] * 0.40 +
            (1.0 - characteristics['grid_score']) * 0.30 +
            (1.0 - characteristics['axes_score']) * 0.30
        )

        # Classification
        if plot_score > 0.6 and plot_score > image_score:
            return "plot", plot_score, characteristics
        elif image_score > 0.6 and image_score > plot_score:
            return "image", image_score, characteristics
        else:
            return "uncertain", max(plot_score, image_score), characteristics

    def _detect_grid_lines(self, gray: np.ndarray) -> float:
        """Detect presence of grid lines (strong plot indicator)."""
        try:
            edges = cv2.Canny(gray, 50, 150)

            # Horizontal lines
            h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            h_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, h_kernel)

            # Vertical lines
            v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
            v_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, v_kernel)

            # Count line pixels
            h_pixels = np.sum(h_lines > 0)
            v_pixels = np.sum(v_lines > 0)
            total_pixels = gray.shape[0] * gray.shape[1]

            # Grid score based on both horizontal and vertical lines
            line_ratio = (h_pixels + v_pixels) / total_pixels

            # Normalize to 0-1 (typical plots have 0.5-2% line coverage)
            score = min(1.0, line_ratio * 100)
            return score
        except:
            return 0.0

    def _detect_axes(self, gray: np.ndarray) -> float:
        """Detect x/y axes (typical plot characteristic)."""
        try:
            edges = cv2.Canny(gray, 50, 150)
            h, w = gray.shape

            # Check left edge for y-axis
            left_edge = edges[:, :int(w*0.1)]
            left_score = np.sum(left_edge > 0) / (h * int(w*0.1))

            # Check bottom edge for x-axis
            bottom_edge = edges[int(h*0.9):, :]
            bottom_score = np.sum(bottom_edge > 0) / (int(h*0.1) * w)

            # Both axes present = high score
            axes_score = (left_score + bottom_score) * 50
            return min(1.0, axes_score)
        except:
            return 0.0

    def _detect_curves(self, gray: np.ndarray) -> float:
        """Detect data curves (edges minus straight lines)."""
        try:
            edges = cv2.Canny(gray, 50, 150)

            # Detect straight lines
            h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
            h_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, h_kernel)
            v_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, v_kernel)
            straight_lines = cv2.bitwise_or(h_lines, v_lines)

            # Curves = edges - straight lines
            curves = cv2.bitwise_and(edges, cv2.bitwise_not(straight_lines))

            total_pixels = gray.shape[0] * gray.shape[1]
            curve_ratio = np.sum(curves > 0) / total_pixels

            # Normalize
            score = min(1.0, curve_ratio * 200)
            return score
        except:
            return 0.0

    def _estimate_text_density(self, gray: np.ndarray) -> float:
        """Estimate text density (plots have axis labels)."""
        try:
            # Use high-frequency edges to find text
            edges = cv2.Canny(gray, 100, 200)

            # Small kernel for text-like patterns
            text_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            text_regions = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, text_kernel)

            total_pixels = gray.shape[0] * gray.shape[1]
            text_ratio = np.sum(text_regions > 0) / total_pixels

            return min(1.0, text_ratio * 50)
        except:
            return 0.0

    def _color_complexity(self, image_array: np.ndarray) -> float:
        """
        Estimate color complexity.
        Plots: simpler (< 50 unique colors)
        Images: complex (> 1000 unique colors)
        """
        try:
            # Downsample for speed
            small = cv2.resize(image_array, (100, 100))

            # Count unique colors
            pixels = small.reshape(-1, small.shape[-1])
            unique_colors = len(np.unique(pixels, axis=0))

            # Normalize (0 = simple, 1 = complex)
            # Plots typically < 50 colors, images > 1000
            if unique_colors < 50:
                return 0.0
            elif unique_colors > 1000:
                return 1.0
            else:
                return (unique_colors - 50) / 950
        except:
            return 0.5


class FigureExtractionAgent(BaseExtractionAgent):
    """
    Specialized agent for extracting figures/diagrams with plot/image classification.

    Features:
    ---------
    - Computer vision-based classification: Distinguishes plots (data-extractable) from images (visual-only)
    - High resolution rendering: 300 DPI for clear visualization
    - 5-feature classification: Grid lines, axes, curves, text density, color complexity

    Classification Types:
    --------------------
    - "plot": Data-extractable figures (graphs, charts) with gridlines/axes
    - "image": Visual-only figures (photos, diagrams) without extractable data
    - "uncertain": Borderline cases requiring manual review

    Usage Example:
    --------------
    >>> agent = FigureExtractionAgent(pdf_path=Path("doc.pdf"), output_dir=Path("results/rag_extractions"))
    >>> zones = [Zone(id="fig_1", type="figure", page=4, bbox=[...])]
    >>> results = agent.process_zones(zones)
    """

    def __init__(self, pdf_path: Path, output_dir: Path):
        super().__init__(pdf_path, output_dir)
        self.agent_type = "figure_extraction"
        self.agent_version = "2.0.0"  # Fixed version - removed broken deduplication, added classification

        self.figures_dir = self.output_dir / "figures"
        self.figures_dir.mkdir(parents=True, exist_ok=True)

        self.doc = fitz.open(str(self.pdf_path))

        # Initialize classifier
        self.classifier = PlotImageClassifier()

    def extract_from_zone(self, zone: Zone) -> Optional[ExtractedObject]:
        """Extract figure: crop image + classify + extract caption."""
        try:
            # Crop image and classify
            result = self._crop_figure(zone)
            if not result:
                return None

            image_path, fig_type, confidence, characteristics = result

            # Extract caption
            caption = self._extract_caption(zone)

            return ExtractedObject(
                id=zone.zone_id,
                type="figure",
                page=zone.page,
                bbox=zone.bbox,
                content={
                    "image_path": str(image_path.relative_to(self.output_dir.parent)),
                    "caption": caption,
                    "figure_type": fig_type,
                    "classification_confidence": confidence
                },
                context={
                    "caption": caption,
                    "description": "",
                    "figure_type": fig_type
                },
                references={
                    "mentioned_in_text": [],
                    "related_equations": [],
                    "related_tables": []
                },
                metadata={
                    "extraction_method": "pymupdf_crop_with_classification",
                    "image_format": "PNG",
                    "resolution_dpi": 300,
                    "figure_type": fig_type,
                    "classification_confidence": confidence,
                    "classification_characteristics": characteristics,
                    "confidence": confidence
                },
                document_id=self.document_metadata.get("document_id"),
                zotero_key=self.document_metadata.get("zotero_key")
            )
        except Exception as e:
            print(f"    ❌ Exception: {e}")
            return None

    def _crop_figure(self, zone: Zone) -> Optional[tuple]:
        """
        Crop figure image using bbox and classify as plot vs image.

        CRITICAL: Use YOLO's zone.bbox directly - don't re-detect!
        (Same lesson as equation extraction - trust the detection phase)

        Returns:
            Tuple of (image_path, fig_type, confidence, characteristics) or None
            - image_path: Path to saved PNG file
            - fig_type: "plot", "image", or "uncertain"
            - confidence: 0.0 to 1.0
            - characteristics: dict with feature scores
        """
        try:
            page = self.doc[zone.page - 1]
            page_height = float(page.rect.height)

            # Convert bbox (Docling bottom-left origin)
            x0, y0, x1, y1 = zone.bbox
            y0_flip = page_height - y0
            y1_flip = page_height - y1
            y0_flip, y1_flip = min(y0_flip, y1_flip), max(y0_flip, y1_flip)

            # Render at 300 DPI for clear visualization (like working October version)
            rect = fitz.Rect(x0, y0_flip, x1, y1_flip)
            mat = fitz.Matrix(300/72, 300/72)  # 300 DPI, not 150
            pix = page.get_pixmap(matrix=mat, clip=rect)

            # Convert PyMuPDF pixmap to numpy array for classification
            img_data = pix.tobytes("png")
            pil_img = Image.open(io.BytesIO(img_data))
            img_array = np.array(pil_img)

            # Classify as plot vs image
            fig_type, confidence, characteristics = self.classifier.classify(img_array)

            # Save figure image
            img_path = self.figures_dir / f"{zone.zone_id}.png"
            pix.save(str(img_path))

            return img_path, fig_type, confidence, characteristics

        except Exception as e:
            print(f"    ⚠️  Image crop/classification failed: {e}")
            return None

    def _extract_caption(self, zone: Zone) -> str:
        """Extract figure caption (Figure X: ...)."""
        try:
            page = self.doc[zone.page - 1]
            page_text = page.get_text()

            patterns = [
                r'(Figure\s+\d+[a-z]?[\s\.:][^\n]+)',
                r'(Fig\.\s+\d+[a-z]?[\s\.:][^\n]+)',
                r'(FIG\.\s+\d+[a-z]?[\s\.:][^\n]+)'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    return re.sub(r'\s+', ' ', matches[0].strip())

            return ""
        except Exception as e:
            return ""

    def _print_statistics(self):
        """Print extraction statistics with classification info."""
        super()._print_statistics()

        # Classification statistics
        if hasattr(self, 'results') and self.results:
            plot_count = sum(1 for r in self.results if r.metadata.get('figure_type') == 'plot')
            image_count = sum(1 for r in self.results if r.metadata.get('figure_type') == 'image')
            uncertain_count = sum(1 for r in self.results if r.metadata.get('figure_type') == 'uncertain')

            if plot_count + image_count + uncertain_count > 0:
                print(f"\n{'-'*70}")
                print(f"CLASSIFICATION STATISTICS")
                print(f"{'-'*70}")
                print(f"  Plots (data-extractable): {plot_count}")
                print(f"  Images (visual-only): {image_count}")
                print(f"  Uncertain (needs review): {uncertain_count}")
                print(f"{'='*70}\n")

    def __del__(self):
        if hasattr(self, 'doc'):
            self.doc.close()
