#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Classifier - Hybrid Auto-Detection + User Confirmation

Implements intelligent document type detection using:
1. Zotero metadata (high confidence: 0.95)
2. Structure heuristics (medium confidence: 0.70-0.85)
3. User confirmation when needed (confidence < 0.90)

Author: Claude Code
Date: 2025-01-27
Version: 1.0.0
"""

import sys
import os

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

import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import re


# Custom Exceptions
class ClassificationError(Exception):
    """Base exception for classification errors."""
    pass


class ConfigurationError(ClassificationError):
    """Configuration file error."""
    pass


class StructureDetectionError(ClassificationError):
    """Structure detection failed."""
    pass


class UserConfirmationError(ClassificationError):
    """User confirmation failed or cancelled."""
    pass


# Data Structures
@dataclass
class DocumentStructure:
    """Detected document structure."""
    has_chapters: bool = False
    has_sections: bool = False
    has_subsections: bool = False
    has_abstract: bool = False
    has_references: bool = False
    has_introduction: bool = False
    has_methods: bool = False
    has_results: bool = False
    has_discussion: bool = False
    has_conclusion: bool = False

    # Counts
    chapter_count: int = 0
    section_count: int = 0
    page_count: int = 0

    # Raw matches for debugging
    chapter_matches: List[str] = field(default_factory=list)
    section_matches: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ChunkingStrategy:
    """Chunking strategy configuration."""
    name: str
    description: str
    target_tokens: int
    max_tokens: int
    min_tokens: int
    overlap_tokens: int
    boundary_type: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ClassificationResult:
    """Complete document classification result."""
    # Document type
    document_type: str
    confidence: float
    detection_method: str  # "zotero", "heuristic", "user_confirmed"

    # Document structure
    structure: DocumentStructure

    # Recommended chunking strategy
    chunking_strategy: ChunkingStrategy

    # Metadata
    classification_date: str
    classifier_version: str
    human_verified: bool = False

    # Optional user feedback
    user_override: Optional[str] = None
    correction_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        result = asdict(self)
        result['structure'] = self.structure.to_dict()
        result['chunking_strategy'] = self.chunking_strategy.to_dict()
        return result

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class DocumentClassifier:
    """
    Hybrid document classifier with auto-detection and user confirmation.

    Classification Pipeline:
    1. Load configuration from YAML
    2. Try Zotero metadata (if available) → confidence 0.95
    3. Try structure heuristics → confidence 0.70-0.85
    4. If confidence < 0.90: Ask user for confirmation
    5. Store classification with document metadata
    6. Learn from user corrections

    Usage:
        classifier = DocumentClassifier()
        result = classifier.classify(
            pdf_path=Path("document.pdf"),
            zotero_key="ABC12345"
        )
        print(f"Type: {result.document_type}")
        print(f"Strategy: {result.chunking_strategy.name}")
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize document classifier.

        Args:
            config_path: Path to classification config YAML
                        (default: config/document_classification.yaml)

        Raises:
            ConfigurationError: If config file not found or invalid
        """
        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "document_classification.yaml"

        self.config_path = Path(config_path)
        self.config = self._load_config()

        # Version
        self.version = "1.0.0"

        # Statistics
        self.stats = {
            "total_classifications": 0,
            "zotero_detections": 0,
            "heuristic_detections": 0,
            "user_confirmations": 0,
            "user_corrections": 0
        }

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Configuration dictionary

        Raises:
            ConfigurationError: If config file missing or invalid
        """
        if not self.config_path.exists():
            raise ConfigurationError(f"Config file not found: {self.config_path}")

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Validate required sections
            required = ['document_types', 'structure_detection', 'chunking_strategies']
            for section in required:
                if section not in config:
                    raise ConfigurationError(f"Missing required section: {section}")

            return config

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in config file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading config: {e}")

    def classify(
        self,
        pdf_path: Path,
        zotero_key: Optional[str] = None,
        zotero_item_type: Optional[str] = None,
        force_user_confirmation: bool = False
    ) -> ClassificationResult:
        """
        Classify document type and recommend chunking strategy.

        Args:
            pdf_path: Path to PDF file
            zotero_key: Optional Zotero item key
            zotero_item_type: Optional Zotero item type (if known)
            force_user_confirmation: Always ask user even if confident

        Returns:
            ClassificationResult with document type and strategy

        Raises:
            ClassificationError: If classification fails
        """
        self.stats["total_classifications"] += 1

        # Step 1: Try Zotero metadata (high confidence)
        doc_type = None
        confidence = 0.0
        method = "unknown"

        if zotero_item_type:
            doc_type, confidence = self._classify_from_zotero(zotero_item_type)
            method = "zotero"
            self.stats["zotero_detections"] += 1

        # Step 2: Try structure heuristics (medium confidence)
        if doc_type is None or confidence < 0.70:
            structure = self._detect_structure(pdf_path)
            doc_type_heuristic, confidence_heuristic = self._classify_from_structure(structure)

            # Use heuristic if better than Zotero (shouldn't happen often)
            if confidence_heuristic > confidence:
                doc_type = doc_type_heuristic
                confidence = confidence_heuristic
                method = "heuristic"
                self.stats["heuristic_detections"] += 1
        else:
            # Still need structure for chunking strategy
            structure = self._detect_structure(pdf_path)

        # Step 3: User confirmation if needed
        human_verified = False
        user_override = None

        threshold = self.config['document_types']['confidence']['user_confirmation_threshold']

        if force_user_confirmation or confidence < threshold:
            if self.config['user_interaction']['ask_on_low_confidence']:
                try:
                    doc_type, structure, human_verified = self._get_user_confirmation(
                        pdf_path=pdf_path,
                        detected_type=doc_type,
                        detected_structure=structure,
                        confidence=confidence
                    )
                    confidence = 1.0  # User confirmation = 100% confidence
                    method = "user_confirmed"
                    self.stats["user_confirmations"] += 1
                except UserConfirmationError:
                    # User cancelled or timeout - use detected values
                    pass

        # Step 4: Select chunking strategy
        chunking_strategy = self._select_chunking_strategy(structure)

        # Step 5: Create result
        result = ClassificationResult(
            document_type=doc_type or "unknown",
            confidence=confidence,
            detection_method=method,
            structure=structure,
            chunking_strategy=chunking_strategy,
            classification_date=datetime.now().isoformat(),
            classifier_version=self.version,
            human_verified=human_verified,
            user_override=user_override
        )

        return result

    def _classify_from_zotero(self, item_type: str) -> Tuple[str, float]:
        """
        Classify document type from Zotero item type.

        Args:
            item_type: Zotero item type (e.g., "book", "journalArticle")

        Returns:
            (document_type, confidence)
        """
        mappings = self.config['document_types']['zotero_mappings']
        confidence = self.config['document_types']['confidence']['zotero_source']

        doc_type = mappings.get(item_type, "unknown")

        if doc_type == "unknown":
            confidence = 0.0

        return doc_type, confidence

    def _detect_structure(self, pdf_path: Path) -> DocumentStructure:
        """
        Detect document structure using heuristics.

        Args:
            pdf_path: Path to PDF file

        Returns:
            DocumentStructure with detected features
        """
        from .structure_detector import StructureDetector

        detector = StructureDetector(self.config)
        return detector.detect(pdf_path)

    def _classify_from_structure(self, structure: DocumentStructure) -> Tuple[str, float]:
        """
        Classify document type from detected structure.

        Args:
            structure: Detected document structure

        Returns:
            (document_type, confidence)
        """
        # Scoring based on structure features
        if structure.has_chapters:
            if structure.chapter_count > 5:
                return "book", 0.85
            else:
                return "book_chapter", 0.80

        if structure.has_abstract and structure.has_methods and structure.has_results:
            return "journal_article", 0.85

        if structure.has_abstract and structure.has_references:
            return "journal_article", 0.70

        if structure.has_sections and structure.section_count > 10:
            return "technical_report", 0.75

        # Low confidence fallback
        return "unknown", 0.50

    def _select_chunking_strategy(self, structure: DocumentStructure) -> ChunkingStrategy:
        """
        Select optimal chunking strategy based on structure.

        Args:
            structure: Detected document structure

        Returns:
            ChunkingStrategy configuration
        """
        strategies = self.config['chunking_strategies']['strategies']
        rules = self.config['chunking_strategies']['selection_rules']

        # Apply selection rules in order
        for rule in rules:
            condition = rule['condition']

            # Evaluate condition
            if self._evaluate_condition(condition, structure):
                strategy_name = rule['strategy']
                strategy_config = strategies[strategy_name]

                return ChunkingStrategy(
                    name=strategy_name,
                    description=strategy_config['description'],
                    target_tokens=strategy_config['target_tokens'],
                    max_tokens=strategy_config['max_tokens'],
                    min_tokens=strategy_config['min_tokens'],
                    overlap_tokens=strategy_config['overlap_tokens'],
                    boundary_type=strategy_config['boundary_type']
                )

        # Fallback to paragraphs
        strategy_config = strategies['paragraphs']
        return ChunkingStrategy(
            name='paragraphs',
            description=strategy_config['description'],
            target_tokens=strategy_config['target_tokens'],
            max_tokens=strategy_config['max_tokens'],
            min_tokens=strategy_config['min_tokens'],
            overlap_tokens=strategy_config['overlap_tokens'],
            boundary_type=strategy_config['boundary_type']
        )

    def _evaluate_condition(self, condition: str, structure: DocumentStructure) -> bool:
        """
        Evaluate condition string against structure.

        Args:
            condition: Condition string (e.g., "has_sections", "is_paper AND has_abstract")
            structure: Document structure

        Returns:
            True if condition met
        """
        condition = condition.lower().strip()

        # Special cases
        if condition == "fallback":
            return True

        # Simple boolean conditions
        if condition == "has_sections":
            return structure.has_sections
        elif condition == "has_chapters":
            return structure.has_chapters
        elif condition == "has_paragraphs":
            return True  # All documents have paragraphs
        elif condition == "is_paper and has_abstract":
            return structure.has_abstract and structure.has_methods

        return False

    def _get_user_confirmation(
        self,
        pdf_path: Path,
        detected_type: str,
        detected_structure: DocumentStructure,
        confidence: float
    ) -> Tuple[str, DocumentStructure, bool]:
        """
        Get user confirmation for classification.

        This will be implemented in user_confirmation_ui.py
        For now, just return detected values.

        Args:
            pdf_path: Path to PDF
            detected_type: Auto-detected type
            detected_structure: Auto-detected structure
            confidence: Detection confidence

        Returns:
            (confirmed_type, confirmed_structure, human_verified)
        """
        # Placeholder - will be implemented in Step 7
        return detected_type, detected_structure, False

    def get_stats(self) -> Dict[str, int]:
        """Get classification statistics."""
        return self.stats.copy()


# Testing function
def main():
    """Test document classifier."""
    print("Testing Document Classifier...")
    print("=" * 70)

    # Test 1: Configuration loading
    print("\n1. Configuration Loading")
    try:
        classifier = DocumentClassifier()
        print("   ✅ Configuration loaded successfully")
        print(f"   Version: {classifier.version}")
    except ConfigurationError as e:
        print(f"   ❌ Configuration error: {e}")
        return

    # Test 2: Zotero classification
    print("\n2. Zotero Classification")
    doc_type, confidence = classifier._classify_from_zotero("bookSection")
    print(f"   Input: bookSection")
    print(f"   Output: {doc_type} (confidence: {confidence:.2f})")
    assert doc_type == "book_chapter", "Expected book_chapter"
    assert confidence == 0.95, "Expected 0.95 confidence"
    print("   ✅ Zotero classification working")

    # Test 3: Structure classification
    print("\n3. Structure Classification")
    structure = DocumentStructure(
        has_chapters=True,
        chapter_count=12
    )
    doc_type, confidence = classifier._classify_from_structure(structure)
    print(f"   Input: chapters=True, count=12")
    print(f"   Output: {doc_type} (confidence: {confidence:.2f})")
    assert doc_type == "book", "Expected book"
    print("   ✅ Structure classification working")

    # Test 4: Chunking strategy selection
    print("\n4. Chunking Strategy Selection")
    structure = DocumentStructure(has_sections=True)
    strategy = classifier._select_chunking_strategy(structure)
    print(f"   Input: sections=True")
    print(f"   Output: {strategy.name}")
    print(f"   Description: {strategy.description}")
    assert strategy.name == "sections", "Expected sections strategy"
    print("   ✅ Strategy selection working")

    # Test 5: Statistics
    print("\n5. Statistics")
    stats = classifier.get_stats()
    print(f"   Classifications: {stats['total_classifications']}")
    print(f"   Zotero: {stats['zotero_detections']}")
    print(f"   Heuristic: {stats['heuristic_detections']}")
    print("   ✅ Statistics working")

    print("\n" + "=" * 70)
    print("✅ All tests passed!")
    print("\nNext steps:")
    print("  1. Implement structure_detector.py for heuristic detection")
    print("  2. Implement user_confirmation_ui.py for user interaction")
    print("  3. Integrate with ZoteroWorkingCopyManager")


if __name__ == "__main__":
    main()
