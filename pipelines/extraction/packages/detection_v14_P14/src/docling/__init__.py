"""
Docling-based detection agents.

Equation, figure, table, and text detection using Docling library.
"""

from .docling_equation_detector import DoclingEquationDetector
from .docling_table_detector import DoclingTableDetector
from .docling_figure_detector import DoclingFigureDetector
from .docling_text_detector import DoclingTextDetector

__all__ = [
    'DoclingEquationDetector',
    'DoclingTableDetector',
    'DoclingFigureDetector',
    'DoclingTextDetector'
]
