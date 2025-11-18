# -*- coding: utf-8 -*-
"""
Data Contracts for v14 Multi-AI Architecture

This module defines data contracts between pipelines:
- ExtractionOutput: Extraction → RAG interface
- RAGOutput: RAG → Database interface
- Validation utilities for contract enforcement

Version: 1.0.0
"""

from .extraction_output import (
    ExtractionOutput,
    ExtractedObject,
    BoundingBox,
    ExtractionMetadata,
    ExtractionQuality
)

from .rag_output import (
    RAGOutput,
    RAGBundle,
    RAGMetadata
)

from .validation import (
    validate_extraction_output,
    validate_rag_output,
    validate_extraction_to_rag_handoff,
    ContractValidationError
)

__all__ = [
    # Extraction contracts
    'ExtractionOutput',
    'ExtractedObject',
    'BoundingBox',
    'ExtractionMetadata',
    'ExtractionQuality',

    # RAG contracts
    'RAGOutput',
    'RAGBundle',
    'RAGMetadata',

    # Validation
    'validate_extraction_output',
    'validate_rag_output',
    'validate_extraction_to_rag_handoff',
    'ContractValidationError',
]

__version__ = '1.0.0'
