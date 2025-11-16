#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Figure Extraction Data Structures
Shared data models for the figure extraction system
"""

import sys
import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum

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

class FigureType(Enum):
    """Figure classification types"""
    DIAGRAM = "diagram"
    CHART = "chart"
    PHOTOGRAPH = "photograph"
    SCHEMATIC = "schematic"
    MIXED = "mixed"
    UNKNOWN = "unknown"

class DetectionMethod(Enum):
    """Figure detection methods"""
    EMBEDDED_IMAGE = "embedded_image"
    VECTOR_GRAPHICS = "vector_graphics"
    CAPTION_BASED = "caption_based"
    WHITESPACE_ANALYSIS = "whitespace_analysis"
    HYBRID = "hybrid"

@dataclass
class BoundingBox:
    """Represents a rectangular bounding box"""
    x0: float
    y0: float
    x1: float
    y1: float
    
    @property
    def width(self) -> float:
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        return self.y1 - self.y0
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)

@dataclass
class QualityMetrics:
    """Figure quality assessment metrics"""
    resolution_dpi: Optional[float] = None
    width_pixels: Optional[int] = None
    height_pixels: Optional[int] = None
    clarity_score: Optional[float] = None
    completeness_score: Optional[float] = None
    content_density: Optional[float] = None

@dataclass
class ExtractionParams:
    """Parameters for figure extraction optimization"""
    target_dpi: int = 300
    output_format: str = "PNG"  # PNG, SVG, PDF
    preserve_vector: bool = True
    quality_threshold: float = 0.7
    crop_padding: int = 10

@dataclass
class FigureCandidate:
    """A potential figure detected in the PDF"""
    bbox: BoundingBox
    page_number: int
    detection_method: DetectionMethod
    confidence_score: float
    metadata: Dict[str, Any]
    
    # Optional fields populated during analysis
    figure_type: Optional[FigureType] = None
    quality_metrics: Optional[QualityMetrics] = None
    extraction_params: Optional[ExtractionParams] = None
    caption_text: Optional[str] = None
    figure_number: Optional[str] = None

@dataclass
class ExtractedFigure:
    """A successfully extracted figure"""
    figure_id: str
    original_candidate: FigureCandidate
    output_path: str
    extraction_timestamp: str
    file_size_bytes: int
    actual_dpi: float
    success: bool
    error_message: Optional[str] = None

@dataclass
class FigureCatalog:
    """Complete catalog of extracted figures"""
    extraction_date: str
    pdf_path: str
    total_figures_found: int
    successful_extractions: int
    success_rate: float
    figures: List[ExtractedFigure]
    detection_summary: Dict[DetectionMethod, int]
    type_distribution: Dict[FigureType, int]
    quality_distribution: Dict[str, int]

# Type aliases for better readability
ImageCandidate = FigureCandidate
VectorCandidate = FigureCandidate
CaptionCandidate = FigureCandidate
BoundaryCandidate = FigureCandidate

class FigureDetectionError(Exception):
    """Custom exception for figure detection errors"""
    pass

class FigureExtractionError(Exception):
    """Custom exception for figure extraction errors"""
    pass

class FigureAnalysisError(Exception):
    """Custom exception for figure analysis errors"""
    pass