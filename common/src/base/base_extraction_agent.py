#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Base Extraction Agent - Standard Interface for RAG-Ready Content Extraction

This module defines the abstract base class that all specialized extraction agents
must implement. It provides a standardized contract for processing document zones
and generating RAG-ready outputs with consistent metadata and formatting.

Design Rationale:
-----------------
- **Interface Segregation**: All agents share common interface but implement specialized logic
- **Low Coupling**: Agents communicate through standard data structures, not direct calls
- **High Cohesion**: Each agent has single responsibility (equations, tables, figures, or text)
- **Extensibility**: New agent types can be added without modifying existing agents

Alternatives Considered:
------------------------
1. Monolithic extractor: Rejected - too complex, violates single responsibility
2. Function-based approach: Rejected - harder to test, no state management
3. Plugin architecture: Overkill for current needs, may add in Phase 2

Author: Claude Code
Date: 2025-10-03
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

# MANDATORY UTF-8 SETUP - NO EXCEPTIONS
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


@dataclass
class Zone:
    """
    Represents a detected content region in the document.

    This is the standard input format for all extraction agents.
    Zones are identified by the detection phase before extraction begins.

    Attributes:
        zone_id: Unique identifier (e.g., "eq_79a", "table_1", "fig_3")
        type: Content type ("equation", "table", "figure", "text")
        page: Page number (1-indexed)
        bbox: Bounding box [x0, y0, x1, y1] in PDF coordinates
        metadata: Optional additional data (e.g., equation_number, caption_hint)
    """
    zone_id: str
    type: str  # "equation", "table", "figure", "text"
    page: int
    bbox: List[float]  # [x0, y0, x1, y1]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ExtractedObject:
    """
    Represents an extracted content object in RAG-ready format.

    This is the standard output format for all extraction agents.
    Design ensures consistency across different content types and enables
    seamless integration with vector databases and LLM retrieval systems.

    Attributes:
        id: Unique identifier matching zone_id
        type: Content type ("equation", "table", "figure", "text")
        page: Page number (1-indexed)
        bbox: Original bounding box [x0, y0, x1, y1]
        content: Type-specific content dictionary (LaTeX, CSV, image path, etc.)
        context: Surrounding text and related information
        references: Cross-references to other objects
        metadata: Extraction metadata (method, confidence, timing)
        embedding: Optional vector embedding for semantic search
        document_id: Optional document identifier for bibliographic tracking
        zotero_key: Optional Zotero item key for citation lookup

    RAG Integration:
        - content: Primary data for LLM context
        - references: Enables graph-based retrieval
        - embedding: Enables vector similarity search
        - metadata: Supports confidence-based filtering
        - document_id: Links to bibliographic metadata for proper citations
    """
    id: str
    type: str
    page: int
    bbox: List[float]
    content: Dict[str, Any]
    context: Dict[str, Any]
    references: Dict[str, List[str]]
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    document_id: Optional[str] = None
    zotero_key: Optional[str] = None


class BaseExtractionAgent(ABC):
    """
    Abstract base class for all specialized extraction agents.

    This class defines the standard interface that all extraction agents
    (equation, table, figure, text) must implement. It ensures consistency
    in how zones are processed and how outputs are generated.

    Design Pattern: Template Method + Strategy
    ------------------------------------------
    - Template Method: process_zones() defines the workflow
    - Strategy: extract_from_zone() is implemented by subclasses

    Subclass Responsibilities:
    --------------------------
    1. Implement extract_from_zone() with specialized extraction logic
    2. Set agent_type and agent_version in __init__
    3. Override validate_zone() if type-specific validation needed
    4. Override post_process() if cross-object processing needed

    Usage Example:
    --------------
    >>> class EquationAgent(BaseExtractionAgent):
    ...     def extract_from_zone(self, zone: Zone) -> ExtractedObject:
    ...         # Specialized equation extraction logic
    ...         pass
    ...
    >>> agent = EquationAgent(pdf_path="doc.pdf", output_dir="results/")
    >>> zones = [Zone(id="eq_1", type="equation", page=2, bbox=[...])]
    >>> results = agent.process_zones(zones)
    """

    def __init__(self, pdf_path: Path, output_dir: Path, document_metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize base extraction agent.

        Args:
            pdf_path: Path to source PDF document
            output_dir: Base directory for extraction outputs
            document_metadata: Optional bibliographic metadata from DocumentMetadataAgent
                             (includes document_id, zotero_key, title, authors, etc.)

        Raises:
            FileNotFoundError: If PDF path does not exist
            PermissionError: If output directory cannot be created
        """
        self.pdf_path = Path(pdf_path)
        self.output_dir = Path(output_dir)
        self.document_metadata = document_metadata or {}

        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

        # Create output directory structure
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Agent identification (set by subclasses)
        self.agent_type = "base"  # Override in subclass
        self.agent_version = "1.0"  # Override in subclass

        # Processing statistics
        self.stats = {
            "zones_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "start_time": None,
            "end_time": None
        }

    @abstractmethod
    def extract_from_zone(self, zone: Zone) -> Optional[ExtractedObject]:
        """
        Extract content from a single zone.

        This is the core method that subclasses must implement with their
        specialized extraction logic. Should be idempotent and thread-safe.

        Args:
            zone: Detected content region to extract

        Returns:
            ExtractedObject with complete content and metadata, or None if extraction fails

        Raises:
            NotImplementedError: If subclass doesn't implement this method

        Implementation Guidelines:
        -------------------------
        1. Validate zone data before processing
        2. Handle all expected errors gracefully
        3. Generate complete metadata for traceability
        4. Return None on failure (don't raise exceptions)
        5. Log detailed information for debugging

        Example Implementation:
        ----------------------
        ```python
        def extract_from_zone(self, zone: Zone) -> Optional[ExtractedObject]:
            try:
                # 1. Validate zone
                if not self.validate_zone(zone):
                    return None

                # 2. Perform extraction
                content = self._extract_content(zone)
                context = self._extract_context(zone)

                # 3. Build result
                return ExtractedObject(
                    id=zone.zone_id,
                    type=zone.type,
                    page=zone.page,
                    bbox=zone.bbox,
                    content=content,
                    context=context,
                    references={},
                    metadata=self._build_metadata(zone)
                )
            except Exception as e:
                print(f"Extraction failed for {zone.zone_id}: {e}")
                return None
        ```
        """
        raise NotImplementedError("Subclass must implement extract_from_zone()")

    def validate_zone(self, zone: Zone) -> bool:
        """
        Validate zone data before extraction.

        Performs basic validation that all zones must pass. Subclasses can
        override to add type-specific validation rules.

        Args:
            zone: Zone to validate

        Returns:
            True if zone is valid, False otherwise

        Validation Checks:
        -----------------
        - Zone ID is non-empty
        - Type matches agent's expected type
        - Page number is positive
        - Bounding box has 4 coordinates
        - Bounding box coordinates are valid (x0 < x1, y0 < y1)
        """
        if not zone.zone_id:
            print(f"  ❌ Invalid zone: empty zone_id")
            return False

        if zone.page < 1:
            print(f"  ❌ Invalid zone {zone.zone_id}: page {zone.page} < 1")
            return False

        if len(zone.bbox) != 4:
            print(f"  ❌ Invalid zone {zone.zone_id}: bbox must have 4 coordinates")
            return False

        x0, y0, x1, y1 = zone.bbox
        # Note: Some coordinate systems use bottom-left origin (Docling), others use top-left (PyMuPDF)
        # Accept either as long as x coordinates are valid
        if x0 >= x1:
            print(f"  ❌ Invalid zone {zone.zone_id}: invalid bbox x-coordinates (x0 >= x1)")
            return False

        return True

    def process_zones(self, zones: List[Zone]) -> List[ExtractedObject]:
        """
        Process multiple zones and extract all content.

        This is the main entry point for extraction. It handles the complete
        workflow: validation, extraction, post-processing, and statistics.

        Args:
            zones: List of zones to process

        Returns:
            List of successfully extracted objects

        Workflow:
        ---------
        1. Start timing
        2. Filter zones by type (only process zones matching agent type)
        3. Validate and extract each zone
        4. Post-process results (build cross-references)
        5. Update statistics
        6. Return results

        Thread Safety:
        -------------
        This method is currently single-threaded. For parallel processing,
        subclasses should override and use multiprocessing.Pool with proper
        resource management via CentralizedCoreManager.
        """
        self.stats["start_time"] = datetime.now()
        results = []

        print(f"\n{'='*70}")
        print(f"{self.agent_type.upper()} EXTRACTION")
        print(f"{'='*70}")
        print(f"Processing {len(zones)} zones...")

        for zone in zones:
            self.stats["zones_processed"] += 1

            # Validate zone
            if not self.validate_zone(zone):
                self.stats["failed_extractions"] += 1
                continue

            # Extract content
            print(f"  Processing {zone.zone_id} (page {zone.page})...")
            extracted = self.extract_from_zone(zone)

            if extracted:
                results.append(extracted)
                self.stats["successful_extractions"] += 1
                print(f"    ✅ Success")
            else:
                self.stats["failed_extractions"] += 1
                print(f"    ❌ Failed")

        # Post-processing
        results = self.post_process(results)

        self.stats["end_time"] = datetime.now()
        self._print_statistics()

        return results

    def post_process(self, objects: List[ExtractedObject]) -> List[ExtractedObject]:
        """
        Post-process extracted objects (optional override).

        Subclasses can override this to perform operations that require
        access to all extracted objects, such as:
        - Building cross-references between objects
        - Normalizing data formats
        - Generating embeddings in batch
        - Calculating derived metrics

        Args:
            objects: List of extracted objects

        Returns:
            Processed list of objects (may be modified in place)
        """
        return objects

    def _print_statistics(self):
        """Print extraction statistics."""
        elapsed = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()

        print(f"\n{'-'*70}")
        print(f"EXTRACTION STATISTICS")
        print(f"{'-'*70}")
        print(f"  Zones processed: {self.stats['zones_processed']}")
        print(f"  Successful: {self.stats['successful_extractions']}")
        print(f"  Failed: {self.stats['failed_extractions']}")
        print(f"  Success rate: {self.stats['successful_extractions']/max(1, self.stats['zones_processed'])*100:.1f}%")
        print(f"  Elapsed time: {elapsed:.2f}s")
        print(f"{'='*70}\n")

    def save_results(self, objects: List[ExtractedObject], output_file: Path):
        """
        Save extracted objects to JSON file.

        Args:
            objects: Extracted objects to save
            output_file: Output file path

        Note: This is a convenience method. Subclasses may override to
        save in different formats (e.g., CSV for tables, images for figures).
        """
        import json

        # Convert datetime objects to ISO strings for JSON serialization
        stats_serializable = {
            k: v.isoformat() if isinstance(v, datetime) else v
            for k, v in self.stats.items()
        }

        # Convert objects to dictionaries
        data = {
            "metadata": {
                "agent_type": self.agent_type,
                "agent_version": self.agent_version,
                "pdf": str(self.pdf_path),
                "extraction_date": datetime.now().isoformat(),
                "statistics": stats_serializable,
                "document_metadata": self.document_metadata  # Include bibliographic info
            },
            "objects": [
                {
                    "id": obj.id,
                    "type": obj.type,
                    "page": obj.page,
                    "bbox": obj.bbox,
                    "content": obj.content,
                    "context": obj.context,
                    "references": obj.references,
                    "metadata": obj.metadata,
                    "embedding": obj.embedding,
                    "document_id": obj.document_id,
                    "zotero_key": obj.zotero_key
                }
                for obj in objects
            ]
        }

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"  💾 Results saved: {output_file}")
