# -*- coding: utf-8 -*-
"""
Contract Validation Utilities

Provides validation functions for data contracts between pipelines.
Ensures pipeline outputs meet requirements before being passed to next pipeline.

Version: 1.0.0
Author: Multi-AI Architecture Team
Date: 2025-11-18
"""

import logging
from typing import Optional
from pathlib import Path

from .extraction_output import ExtractionOutput
from .rag_output import RAGOutput

logger = logging.getLogger(__name__)


class ContractValidationError(Exception):
    """
    Raised when contract validation fails.

    This is a specific exception type to distinguish contract failures
    from other ValueError exceptions.
    """
    pass


def validate_extraction_output(
    extraction_output: ExtractionOutput,
    min_quality_score: float = 0.5,
    require_content: bool = True
) -> bool:
    """
    Validate extraction pipeline output.

    Args:
        extraction_output: ExtractionOutput instance to validate
        min_quality_score: Minimum acceptable quality score (default: 0.5)
        require_content: Whether to require at least one extracted object (default: True)

    Returns:
        True if valid

    Raises:
        ContractValidationError: If validation fails with reason
    """
    try:
        # Run standard validation
        extraction_output.validate()

        # Check quality score
        quality_score = extraction_output.metadata.extraction_quality.overall_score
        if quality_score < min_quality_score:
            raise ContractValidationError(
                f"Extraction quality too low: {quality_score:.2f} < {min_quality_score:.2f}"
            )

        # Check content requirement
        if require_content and len(extraction_output.objects) == 0:
            raise ContractValidationError(
                "Extraction output contains no objects"
            )

        # Check for missing file paths
        missing_files = []
        for obj in extraction_output.objects:
            file_path = Path(obj.file_path)
            if file_path.is_absolute() and not file_path.exists():
                missing_files.append(str(file_path))

        if missing_files:
            logger.warning(
                f"Extraction output references {len(missing_files)} missing files"
            )

        logger.info(
            f"Extraction output validation passed: {len(extraction_output.objects)} objects, "
            f"quality={quality_score:.2f}"
        )
        return True

    except ValueError as e:
        raise ContractValidationError(f"Extraction output validation failed: {e}")


def validate_rag_output(
    rag_output: RAGOutput,
    min_bundles: int = 1,
    require_relationships: bool = True,
    max_bundle_tokens: int = 1000
) -> bool:
    """
    Validate RAG pipeline output.

    Args:
        rag_output: RAGOutput instance to validate
        min_bundles: Minimum number of bundles required (default: 1)
        require_relationships: Whether to require relationships (default: True)
        max_bundle_tokens: Maximum tokens per bundle (default: 1000)

    Returns:
        True if valid

    Raises:
        ContractValidationError: If validation fails with reason
    """
    try:
        # Run standard validation
        rag_output.validate()

        # Check minimum bundles
        if len(rag_output.bundles) < min_bundles:
            raise ContractValidationError(
                f"RAG output has too few bundles: {len(rag_output.bundles)} < {min_bundles}"
            )

        # Check relationships requirement
        if require_relationships and rag_output.metadata.total_relationships == 0:
            logger.warning("RAG output has no relationships - knowledge graph may be empty")

        # Check bundle token counts
        oversized_bundles = []
        for bundle in rag_output.bundles:
            token_count = bundle.estimate_token_count()
            if token_count > max_bundle_tokens:
                oversized_bundles.append((bundle.bundle_id, token_count))

        if oversized_bundles:
            logger.warning(
                f"{len(oversized_bundles)} bundles exceed {max_bundle_tokens} tokens"
            )
            for bundle_id, tokens in oversized_bundles[:5]:  # Show first 5
                logger.warning(f"  - {bundle_id}: {tokens} tokens")

        logger.info(
            f"RAG output validation passed: {len(rag_output.bundles)} bundles, "
            f"{rag_output.metadata.total_relationships} relationships"
        )
        return True

    except ValueError as e:
        raise ContractValidationError(f"RAG output validation failed: {e}")


def validate_extraction_to_rag_handoff(
    extraction_output: ExtractionOutput,
    min_quality_score: float = 0.5
) -> bool:
    """
    Validate extraction output is suitable for RAG ingestion.

    This is a specialized validation for the Extraction → RAG pipeline handoff.

    Args:
        extraction_output: ExtractionOutput instance to validate
        min_quality_score: Minimum acceptable quality score (default: 0.5)

    Returns:
        True if valid for RAG ingestion

    Raises:
        ContractValidationError: If validation fails with reason
    """
    try:
        # Validate as extraction output
        validate_extraction_output(
            extraction_output,
            min_quality_score=min_quality_score,
            require_content=True
        )

        # Check for source document info (required for RAG provenance)
        if not extraction_output.metadata.source_filename:
            raise ContractValidationError(
                "Missing source_filename in metadata - required for RAG provenance"
            )

        # Check for reasonable page count
        if extraction_output.metadata.page_count < 1:
            raise ContractValidationError(
                f"Invalid page_count: {extraction_output.metadata.page_count}"
            )

        # Warn if no equations extracted (unusual for technical documents)
        if extraction_output.metadata.extraction_quality.equations_extracted == 0:
            logger.warning(
                "No equations extracted - may not be a technical document"
            )

        logger.info(
            f"Extraction→RAG handoff validation passed: {extraction_output.document_id}"
        )
        return True

    except ContractValidationError:
        raise
    except ValueError as e:
        raise ContractValidationError(f"Extraction→RAG handoff validation failed: {e}")


def validate_rag_to_database_handoff(
    rag_output: RAGOutput,
    min_bundles: int = 1
) -> bool:
    """
    Validate RAG output is suitable for database ingestion.

    This is a specialized validation for the RAG → Database pipeline handoff.

    Args:
        rag_output: RAGOutput instance to validate
        min_bundles: Minimum number of bundles required (default: 1)

    Returns:
        True if valid for database ingestion

    Raises:
        ContractValidationError: If validation fails with reason
    """
    try:
        # Validate as RAG output
        validate_rag_output(
            rag_output,
            min_bundles=min_bundles,
            require_relationships=False,  # Relationships optional for DB
            max_bundle_tokens=1000
        )

        # Check all bundles have embedding metadata
        missing_metadata = []
        for bundle in rag_output.bundles:
            if not bundle.embedding_metadata:
                missing_metadata.append(bundle.bundle_id)

        if missing_metadata:
            logger.warning(
                f"{len(missing_metadata)} bundles missing embedding_metadata"
            )

        # Check all bundles have semantic tags (important for retrieval)
        missing_tags = []
        for bundle in rag_output.bundles:
            if not bundle.semantic_tags or len(bundle.semantic_tags) == 0:
                missing_tags.append(bundle.bundle_id)

        if missing_tags:
            logger.warning(
                f"{len(missing_tags)} bundles missing semantic_tags - "
                f"retrieval may be degraded"
            )

        logger.info(
            f"RAG→Database handoff validation passed: {rag_output.document_id}"
        )
        return True

    except ContractValidationError:
        raise
    except ValueError as e:
        raise ContractValidationError(f"RAG→Database handoff validation failed: {e}")


def validate_pipeline_handoff(
    source_path: Path,
    target_pipeline: str,
    min_quality_score: float = 0.5,
    min_bundles: int = 1
) -> bool:
    """
    Validate pipeline handoff from file path.

    Convenience function that loads the contract file and validates
    for the target pipeline.

    Args:
        source_path: Path to contract file (JSON)
        target_pipeline: Target pipeline ('rag' or 'database')
        min_quality_score: Minimum quality score for extraction (default: 0.5)
        min_bundles: Minimum bundles for RAG (default: 1)

    Returns:
        True if valid

    Raises:
        ContractValidationError: If validation fails
        FileNotFoundError: If source_path doesn't exist
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Contract file not found: {source_path}")

    if target_pipeline == 'rag':
        # Validate Extraction → RAG handoff
        extraction_output = ExtractionOutput.from_json_file(source_path, validate=False)
        return validate_extraction_to_rag_handoff(
            extraction_output,
            min_quality_score=min_quality_score
        )

    elif target_pipeline == 'database':
        # Validate RAG → Database handoff
        rag_output = RAGOutput.from_json_file(source_path, validate=False)
        return validate_rag_to_database_handoff(
            rag_output,
            min_bundles=min_bundles
        )

    else:
        raise ValueError(
            f"Unknown target pipeline: '{target_pipeline}'. "
            f"Must be 'rag' or 'database'"
        )


# Export validation functions and exceptions
__all__ = [
    'ContractValidationError',
    'validate_extraction_output',
    'validate_rag_output',
    'validate_extraction_to_rag_handoff',
    'validate_rag_to_database_handoff',
    'validate_pipeline_handoff'
]
