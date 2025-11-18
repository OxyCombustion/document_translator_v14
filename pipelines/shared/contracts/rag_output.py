# -*- coding: utf-8 -*-
"""
RAG Pipeline Output Contract

Defines the data contract for outputs from the RAG ingestion pipeline (Pipeline 2).
All RAG outputs MUST conform to this schema before being passed to Database Management.

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
class RAGBundle:
    """
    Self-contained RAG bundle (micro-bundle).

    Each bundle is optimized for embedding and contains everything needed
    to answer questions about an entity without requiring graph traversal.

    Consistent with existing MicroBundle structure in bundle_builders.py.
    """
    bundle_id: str  # Unique ID: bundle:eq9_complete, bundle:tbl3_complete
    bundle_type: str  # equation | table | concept | figure
    entity_id: str  # Source entity: eq:9, tbl:3, var:epsilon
    content: Dict[str, Any]  # Type-specific content (latex, markdown, etc.)
    usage_guidance: Dict[str, Any]  # How to use this entity
    semantic_tags: List[str]  # Keywords for retrieval
    embedding_metadata: Dict[str, Any]  # Metadata for vector databases
    relationships: List[Dict[str, Any]] = field(default_factory=list)  # Related entities

    def validate(self) -> bool:
        """Validate RAG bundle."""
        # Validate bundle_id format
        if not self.bundle_id.startswith('bundle:'):
            raise ValueError(
                f"bundle_id must start with 'bundle:', got '{self.bundle_id}'"
            )

        # Validate bundle_type
        valid_types = ('equation', 'table', 'concept', 'figure', 'text')
        if self.bundle_type not in valid_types:
            raise ValueError(
                f"bundle_type must be one of {valid_types}, got '{self.bundle_type}'"
            )

        # Validate entity_id format
        valid_prefixes = ('eq:', 'tbl:', 'fig:', 'var:', 'txt:', 'concept:')
        if not any(self.entity_id.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(
                f"entity_id must start with {valid_prefixes}, got '{self.entity_id}'"
            )

        # Validate content is not empty
        if not self.content:
            raise ValueError("content cannot be empty")

        # Validate semantic tags
        if not self.semantic_tags or len(self.semantic_tags) == 0:
            logger.warning(f"Bundle {self.bundle_id} has no semantic tags")

        return True

    def estimate_token_count(self) -> int:
        """
        Estimate token count for this bundle.
        Uses rough approximation: 4 chars per token.
        """
        json_str = json.dumps(self.to_dict())
        chars_per_token = 4
        return len(json_str) // chars_per_token

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class RAGMetadata:
    """
    RAG pipeline processing metadata.

    Tracks semantic processing stats, chunking results, relationship counts, etc.
    """
    source_document_id: str  # Links to ExtractionOutput.document_id
    processing_timestamp: str  # ISO 8601 timestamp
    pipeline_version: str = "14.0.0"
    total_bundles: int = 0
    bundles_by_type: Dict[str, int] = field(default_factory=dict)
    total_relationships: int = 0
    semantic_chunks_created: int = 0
    citations_extracted: int = 0
    average_bundle_tokens: float = 0.0
    quality_metrics: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """Validate RAG metadata."""
        if not self.source_document_id:
            raise ValueError("source_document_id cannot be empty")

        try:
            datetime.fromisoformat(self.processing_timestamp)
        except ValueError as e:
            raise ValueError(f"processing_timestamp must be valid ISO 8601: {e}")

        if self.total_bundles < 0:
            raise ValueError("total_bundles must be >= 0")

        if self.total_relationships < 0:
            raise ValueError("total_relationships must be >= 0")

        if self.semantic_chunks_created < 0:
            raise ValueError("semantic_chunks_created must be >= 0")

        if self.citations_extracted < 0:
            raise ValueError("citations_extracted must be >= 0")

        return True


@dataclass
class RAGOutput:
    """
    Complete RAG pipeline output contract.

    This is the PRIMARY contract between RAG (Pipeline 2) and Database (Pipeline 3).
    All RAG outputs MUST validate against this contract.

    Example Usage:
        >>> output = RAGOutput(
        ...     document_id="chapter4_heat_transfer",
        ...     bundles=[...],
        ...     metadata=metadata
        ... )
        >>> output.validate()  # Raises ValueError if invalid
        >>> output.to_jsonl_file(Path("rag_output.jsonl"))
    """
    document_id: str  # Unique document identifier (matches ExtractionOutput)
    bundles: List[RAGBundle]  # All RAG bundles
    metadata: RAGMetadata  # RAG processing metadata
    knowledge_graph: Optional[Dict[str, Any]] = None  # Optional graph data

    def validate(self) -> bool:
        """
        Validate RAG output contract.

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

        # Validate metadata
        self.metadata.validate()

        # Validate document_id matches metadata
        if self.document_id != self.metadata.source_document_id:
            raise ValueError(
                f"document_id mismatch: '{self.document_id}' != "
                f"'{self.metadata.source_document_id}' in metadata"
            )

        # Validate all bundles
        for bundle in self.bundles:
            bundle.validate()

        # Validate bundle count matches metadata
        if len(self.bundles) != self.metadata.total_bundles:
            raise ValueError(
                f"Bundle count mismatch: {len(self.bundles)} bundles vs "
                f"{self.metadata.total_bundles} in metadata"
            )

        # Validate bundles by type counts
        counts_by_type = {}
        for bundle in self.bundles:
            counts_by_type[bundle.bundle_type] = counts_by_type.get(bundle.bundle_type, 0) + 1

        for bundle_type, count in self.metadata.bundles_by_type.items():
            if counts_by_type.get(bundle_type, 0) != count:
                raise ValueError(
                    f"Bundle type '{bundle_type}' count mismatch: "
                    f"{counts_by_type.get(bundle_type, 0)} actual vs {count} in metadata"
                )

        logger.info(f"RAG output validation passed: {len(self.bundles)} bundles")
        return True

    def validate_completeness(self) -> bool:
        """
        Validate RAG output appears complete (basic sanity checks).

        Returns:
            True if RAG output appears complete

        Raises:
            ValueError: If RAG output appears incomplete
        """
        # Must have at least some bundles
        if len(self.bundles) == 0:
            raise ValueError("No bundles created - RAG output appears empty")

        # Should have some relationships
        if self.metadata.total_relationships == 0:
            logger.warning("No relationships extracted - knowledge graph may be empty")

        # Should have created semantic chunks
        if self.metadata.semantic_chunks_created == 0:
            logger.warning("No semantic chunks created")

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

        logger.info(f"RAG output written to {path}")

    def to_jsonl_file(self, path: Path, validate: bool = True) -> None:
        """
        Write bundles to JSONL file (one bundle per line) with optional validation.

        This is the preferred format for streaming ingestion into vector databases.

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

        with path.open('w', encoding='utf-8') as f:
            for bundle in self.bundles:
                bundle_dict = bundle.to_dict()
                # Add document_id to each bundle for context
                bundle_dict['source_document_id'] = self.document_id
                f.write(json.dumps(bundle_dict, ensure_ascii=False) + '\n')

        logger.info(f"RAG output written to JSONL: {path} ({len(self.bundles)} bundles)")

    @classmethod
    def from_json_file(cls, path: Path, validate: bool = True) -> "RAGOutput":
        """
        Load from JSON file with optional validation.

        Args:
            path: Input file path
            validate: Whether to validate after loading (default: True)

        Returns:
            RAGOutput instance

        Raises:
            ValueError: If file doesn't match schema or validation fails
        """
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)

        # Reconstruct nested dataclasses
        metadata_data = data['metadata']
        metadata = RAGMetadata(**metadata_data)

        bundles = []
        for bundle_data in data['bundles']:
            bundles.append(RAGBundle(**bundle_data))

        output = cls(
            document_id=data['document_id'],
            bundles=bundles,
            metadata=metadata,
            knowledge_graph=data.get('knowledge_graph')
        )

        if validate:
            output.validate()

        logger.info(f"RAG output loaded from {path}")
        return output

    @classmethod
    def from_jsonl_file(cls, path: Path, document_id: str, validate: bool = True) -> "RAGOutput":
        """
        Load from JSONL file (one bundle per line) with optional validation.

        Args:
            path: Input JSONL file path
            document_id: Document identifier
            validate: Whether to validate after loading (default: True)

        Returns:
            RAGOutput instance

        Raises:
            ValueError: If file doesn't match schema or validation fails
        """
        bundles = []
        with path.open('r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    bundle_data = json.loads(line)
                    # Remove source_document_id if present (metadata field)
                    bundle_data.pop('source_document_id', None)
                    bundles.append(RAGBundle(**bundle_data))
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON on line {line_num}: {e}")

        # Create metadata from bundles
        bundles_by_type = {}
        total_relationships = 0
        for bundle in bundles:
            bundles_by_type[bundle.bundle_type] = bundles_by_type.get(bundle.bundle_type, 0) + 1
            total_relationships += len(bundle.relationships)

        metadata = RAGMetadata(
            source_document_id=document_id,
            processing_timestamp=datetime.now().isoformat(),
            total_bundles=len(bundles),
            bundles_by_type=bundles_by_type,
            total_relationships=total_relationships
        )

        output = cls(
            document_id=document_id,
            bundles=bundles,
            metadata=metadata
        )

        if validate:
            output.validate()

        logger.info(f"RAG output loaded from JSONL: {path} ({len(bundles)} bundles)")
        return output

    def summary(self) -> Dict[str, Any]:
        """Generate summary of RAG output."""
        return {
            "document_id": self.document_id,
            "timestamp": self.metadata.processing_timestamp,
            "total_bundles": len(self.bundles),
            "bundles_by_type": self.metadata.bundles_by_type,
            "total_relationships": self.metadata.total_relationships,
            "semantic_chunks": self.metadata.semantic_chunks_created,
            "citations": self.metadata.citations_extracted,
            "average_tokens_per_bundle": self.metadata.average_bundle_tokens
        }


# Export main contracts
__all__ = [
    'RAGOutput',
    'RAGBundle',
    'RAGMetadata'
]
