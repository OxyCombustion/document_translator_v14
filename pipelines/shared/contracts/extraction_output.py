# -*- coding: utf-8 -*-
"""
Extraction Pipeline Output Contract

Defines the data contract for outputs from the extraction pipeline (Pipeline 1).
All extraction outputs MUST conform to this schema before being passed to RAG.

This contract uses @dataclass (Python 3.7+) for zero additional dependencies,
consistent with existing v14 codebase patterns.

Version: 1.0.0
Author: Multi-AI Architecture Team
Date: 2025-11-18
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class BoundingBox:
    """
    Bounding box coordinates in PDF space.

    Coordinates are in points (1/72 inch), origin at bottom-left of page.
    Used for spatial location of extracted objects.
    """
    page: int  # Page number (1-indexed)
    x0: float  # Left edge X coordinate
    y0: float  # Bottom edge Y coordinate
    x1: float  # Right edge X coordinate
    y1: float  # Top edge Y coordinate

    def validate(self) -> bool:
        """Validate bounding box coordinates."""
        if self.page < 1:
            raise ValueError(f"Page number must be >= 1, got {self.page}")
        if self.x1 <= self.x0:
            raise ValueError(f"x1 ({self.x1}) must be > x0 ({self.x0})")
        if self.y1 <= self.y0:
            raise ValueError(f"y1 ({self.y1}) must be > y0 ({self.y0})")
        return True

    def area(self) -> float:
        """Calculate bounding box area in square points."""
        return (self.x1 - self.x0) * (self.y1 - self.y0)


@dataclass
class ExtractedObject:
    """
    Individual extracted content object.

    Represents a single extracted entity (equation, table, figure, or text block)
    with its location, content path, and confidence score.
    """
    object_id: str  # Unique ID: eq_1, tbl_1, fig_1, txt_1
    object_type: str  # equation | table | figure | text
    bbox: BoundingBox  # Spatial location
    file_path: str  # Path to extracted file (PNG, CSV, TXT, etc.)
    confidence: float  # Extraction confidence (0.0-1.0)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata

    def validate(self) -> bool:
        """Validate extracted object."""
        # Validate object_id format
        valid_prefixes = ('eq_', 'tbl_', 'fig_', 'txt_')
        if not any(self.object_id.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(
                f"object_id must start with {valid_prefixes}, got '{self.object_id}'"
            )

        # Validate object_type
        valid_types = ('equation', 'table', 'figure', 'text')
        if self.object_type not in valid_types:
            raise ValueError(
                f"object_type must be one of {valid_types}, got '{self.object_type}'"
            )

        # Validate prefix matches type
        type_to_prefix = {
            'equation': 'eq_',
            'table': 'tbl_',
            'figure': 'fig_',
            'text': 'txt_'
        }
        expected_prefix = type_to_prefix[self.object_type]
        if not self.object_id.startswith(expected_prefix):
            raise ValueError(
                f"object_id '{self.object_id}' must start with '{expected_prefix}' "
                f"for object_type '{self.object_type}'"
            )

        # Validate confidence
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0.0, 1.0], got {self.confidence}"
            )

        # Validate bounding box
        self.bbox.validate()

        # Validate file_path exists (if it's an absolute path)
        file_path_obj = Path(self.file_path)
        if file_path_obj.is_absolute() and not file_path_obj.exists():
            logger.warning(f"File path does not exist: {self.file_path}")

        return True


@dataclass
class ExtractionQuality:
    """
    Extraction quality metrics.

    Tracks what was extracted and provides overall quality score.
    """
    overall_score: float  # Overall quality (0.0-1.0)
    equations_extracted: int = 0
    tables_extracted: int = 0
    figures_extracted: int = 0
    text_blocks_extracted: int = 0

    def validate(self) -> bool:
        """Validate quality metrics."""
        if not 0.0 <= self.overall_score <= 1.0:
            raise ValueError(
                f"overall_score must be in [0.0, 1.0], got {self.overall_score}"
            )
        if self.equations_extracted < 0:
            raise ValueError("equations_extracted must be >= 0")
        if self.tables_extracted < 0:
            raise ValueError("tables_extracted must be >= 0")
        if self.figures_extracted < 0:
            raise ValueError("figures_extracted must be >= 0")
        if self.text_blocks_extracted < 0:
            raise ValueError("text_blocks_extracted must be >= 0")
        return True

    def total_objects(self) -> int:
        """Total number of extracted objects."""
        return (
            self.equations_extracted +
            self.tables_extracted +
            self.figures_extracted +
            self.text_blocks_extracted
        )


@dataclass
class ExtractionMetadata:
    """
    Extraction metadata and provenance.

    Tracks source document info, extraction timestamp, pipeline version, etc.
    """
    source_filename: str
    page_count: int
    extraction_quality: ExtractionQuality
    file_hash: Optional[str] = None  # SHA256 for version tracking
    doi: Optional[str] = None
    title: Optional[str] = None
    pipeline_version: str = "14.0.0"

    def validate(self) -> bool:
        """Validate metadata."""
        if self.page_count < 1:
            raise ValueError(f"page_count must be >= 1, got {self.page_count}")
        self.extraction_quality.validate()
        return True


@dataclass
class ExtractionOutput:
    """
    Complete extraction pipeline output contract.

    This is the PRIMARY contract between Extraction (Pipeline 1) and RAG (Pipeline 2).
    All extraction outputs MUST validate against this contract.

    Example Usage:
        >>> output = ExtractionOutput(
        ...     document_id="chapter4_heat_transfer",
        ...     extraction_timestamp=datetime.now().isoformat(),
        ...     objects=[...],
        ...     metadata=metadata
        ... )
        >>> output.validate()  # Raises ValueError if invalid
        >>> output.to_json_file(Path("extraction_output.json"))
    """
    document_id: str  # Unique document identifier
    extraction_timestamp: str  # ISO 8601 timestamp
    objects: List[ExtractedObject]  # All extracted objects
    metadata: ExtractionMetadata  # Extraction metadata

    def validate(self) -> bool:
        """
        Validate extraction output contract.

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails with reason
        """
        # Validate document_id
        if not self.document_id:
            raise ValueError("document_id cannot be empty")
        if not self.document_id.replace('_', '').replace('-', '').isalnum():
            raise ValueError(
                f"document_id must be alphanumeric with _ or -, got '{self.document_id}'"
            )

        # Validate timestamp
        try:
            datetime.fromisoformat(self.extraction_timestamp)
        except ValueError as e:
            raise ValueError(
                f"extraction_timestamp must be valid ISO 8601: {e}"
            )

        # Validate metadata
        self.metadata.validate()

        # Validate all objects
        for obj in self.objects:
            obj.validate()

        # Validate object count matches metadata
        counts_by_type = {
            'equation': 0,
            'table': 0,
            'figure': 0,
            'text': 0
        }
        for obj in self.objects:
            counts_by_type[obj.object_type] += 1

        quality = self.metadata.extraction_quality
        if counts_by_type['equation'] != quality.equations_extracted:
            raise ValueError(
                f"Equation count mismatch: {counts_by_type['equation']} objects vs "
                f"{quality.equations_extracted} in metadata"
            )
        if counts_by_type['table'] != quality.tables_extracted:
            raise ValueError(
                f"Table count mismatch: {counts_by_type['table']} objects vs "
                f"{quality.tables_extracted} in metadata"
            )
        if counts_by_type['figure'] != quality.figures_extracted:
            raise ValueError(
                f"Figure count mismatch: {counts_by_type['figure']} objects vs "
                f"{quality.figures_extracted} in metadata"
            )
        if counts_by_type['text'] != quality.text_blocks_extracted:
            raise ValueError(
                f"Text count mismatch: {counts_by_type['text']} objects vs "
                f"{quality.text_blocks_extracted} in metadata"
            )

        logger.info(
            f"Extraction output validation passed: {len(self.objects)} objects"
        )
        return True

    def validate_completeness(self) -> bool:
        """
        Validate extraction appears complete (basic sanity checks).

        Returns:
            True if extraction appears complete

        Raises:
            ValueError: If extraction appears incomplete
        """
        # Must have at least some content
        if len(self.objects) == 0:
            raise ValueError("No objects extracted - extraction appears empty")

        # Quality score should be reasonable
        if self.metadata.extraction_quality.overall_score < 0.3:
            logger.warning(
                f"Low quality score: {self.metadata.extraction_quality.overall_score}"
            )

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_json_file(self, path: Path, validate: bool = True) -> None:
        """
        Write to JSON file with optional validation.

        Args:
            path: Output file path
            validate: Whether to validate before writing (default: True)

        Raises:
            ValueError: If validation fails
        """
        if validate:
            self.validate()
            self.validate_completeness()

        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()

        with path.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Extraction output written to {path}")

    @classmethod
    def from_json_file(cls, path: Path, validate: bool = True) -> "ExtractionOutput":
        """
        Load from JSON file with optional validation.

        Args:
            path: Input file path
            validate: Whether to validate after loading (default: True)

        Returns:
            ExtractionOutput instance

        Raises:
            ValueError: If file doesn't match schema or validation fails
        """
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)

        # Reconstruct nested dataclasses
        metadata_data = data['metadata']
        quality_data = metadata_data['extraction_quality']
        metadata_data['extraction_quality'] = ExtractionQuality(**quality_data)
        metadata = ExtractionMetadata(**metadata_data)

        objects = []
        for obj_data in data['objects']:
            bbox_data = obj_data['bbox']
            bbox = BoundingBox(**bbox_data)
            obj_data['bbox'] = bbox
            objects.append(ExtractedObject(**obj_data))

        output = cls(
            document_id=data['document_id'],
            extraction_timestamp=data['extraction_timestamp'],
            objects=objects,
            metadata=metadata
        )

        if validate:
            output.validate()

        logger.info(f"Extraction output loaded from {path}")
        return output

    def summary(self) -> Dict[str, Any]:
        """Generate summary of extraction output."""
        return {
            "document_id": self.document_id,
            "timestamp": self.extraction_timestamp,
            "total_objects": len(self.objects),
            "objects_by_type": {
                "equations": self.metadata.extraction_quality.equations_extracted,
                "tables": self.metadata.extraction_quality.tables_extracted,
                "figures": self.metadata.extraction_quality.figures_extracted,
                "text": self.metadata.extraction_quality.text_blocks_extracted
            },
            "quality_score": self.metadata.extraction_quality.overall_score,
            "source": self.metadata.source_filename,
            "page_count": self.metadata.page_count
        }


# Export main contracts
__all__ = [
    'ExtractionOutput',
    'ExtractedObject',
    'BoundingBox',
    'ExtractionMetadata',
    'ExtractionQuality'
]
