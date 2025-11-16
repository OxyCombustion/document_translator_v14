"""
Document Classification Package

Provides hybrid document type detection with auto-detection and user confirmation.
"""

from .document_classifier import (
    DocumentClassifier,
    ClassificationResult,
    DocumentStructure,
    ChunkingStrategy,
    ClassificationError,
    ConfigurationError,
    StructureDetectionError,
    UserConfirmationError
)

from .structure_detector import StructureDetector

__all__ = [
    'DocumentClassifier',
    'ClassificationResult',
    'DocumentStructure',
    'ChunkingStrategy',
    'StructureDetector',
    'ClassificationError',
    'ConfigurationError',
    'StructureDetectionError',
    'UserConfirmationError'
]

__version__ = '1.0.0'
