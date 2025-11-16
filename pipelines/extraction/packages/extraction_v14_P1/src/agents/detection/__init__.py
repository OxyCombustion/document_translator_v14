"""
Detection agents for identifying document objects.
"""

from .unified_detection_module import *
from .docling_table_detector import *

__all__ = [
    'unified_detection_module',
    'docling_table_detector',
    'docling_figure_detector',
    'docling_text_detector',
    'frame_box_detector',
    'formula_detector_agent',
    'table_detection_agent',
]
