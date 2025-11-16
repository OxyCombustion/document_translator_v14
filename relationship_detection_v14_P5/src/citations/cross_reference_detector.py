# -*- coding: utf-8 -*-
"""
Cross-Reference Detector - Detects references in text to equations, tables, and figures.

This detector identifies textual references like "see Equation 9", "Table 3 shows",
"Figure 2 illustrates" and resolves them to entity IDs using the ReferenceResolver.

Key Features:
    - Pattern-based reference detection via ReferenceResolver
    - Reference intent classification (COMPARISON, DATA_SOURCE, METHODOLOGY, etc.)
    - Context extraction (surrounding sentences)
    - Entity existence validation
    - Confidence scoring based on resolution quality

Architecture:
    - Depends on: ReferenceResolver (pattern matching + disambiguation)
    - Depends on: RelationshipValidator (entity existence checks)
    - Low coupling: Minimal dependencies (2 injected services)
    - High cohesion: All methods focused on cross-reference detection
    - Single Responsibility: Cross-reference detection ONLY

Implementation Status:
✅ Phase 1: Core detection (detect_cross_references, _extract_context)
🔄 Phase 2: Intent classification (_classify_reference_intent)
⏸️ Phase 3: Integration & export

Author: V12 Development Team
Created: 2025-11-04
"""

import sys
import os
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

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import re

from src.core.reference_resolver import ReferenceResolver, ResolvedReference

logger = logging.getLogger(__name__)


# ========== Data Structures ==========

@dataclass
class CrossReference:
    """
    Cross-reference relationship from text to entity.

    This represents a reference in text (e.g., "see Equation 9") resolved
    to an entity ID (e.g., "eq:9").
    """
    relationship_id: str
    edge_type: str  # Always "REFERENCES"
    source: str  # Source paragraph/text ID (e.g., "doc:page_8_paragraph_3")
    target: str  # Target entity ID (e.g., "eq:9", "tbl:3", "fig:2")

    reference_context: Dict[str, Any]  # Reference phrase, type, intent, surrounding text, etc.
    confidence: Dict[str, Any]  # Confidence score, method, factors
    validation: Dict[str, Any]  # Validation result from validator

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'relationship_id': self.relationship_id,
            'edge_type': self.edge_type,
            'source': self.source,
            'target': self.target,
            'reference_context': self.reference_context,
            'confidence': self.confidence,
            'validation': self.validation
        }


# ========== Exceptions ==========

class CrossReferenceDetectorError(Exception):
    """Base exception for CrossReferenceDetector errors."""
    pass


class InvalidTextChunkError(CrossReferenceDetectorError):
    """Raised when text chunk format is invalid."""
    pass


class ReferenceResolutionError(CrossReferenceDetectorError):
    """Raised when reference resolution fails."""
    pass


# ========== Main Detector Class ==========

class CrossReferenceDetector:
    """
    Detects cross-references in text to equations, tables, and figures.

    This detector uses ReferenceResolver to find reference phrases and resolve
    them to entity IDs, then classifies the reference intent and validates
    entity existence.

    Dependencies (Dependency Injection):
        - ReferenceResolver: Pattern matching and resolution
        - RelationshipValidator: Entity existence validation

    Key Responsibilities:
        - Find reference phrases in text chunks
        - Resolve references to entity IDs
        - Extract context around references
        - Classify reference intent
        - Validate entity existence

    Design Principles:
        - Single Responsibility: Cross-reference detection only
        - Dependency Inversion: Depends on abstractions (RR, Validator)
        - Low Coupling: Minimal dependencies
        - High Cohesion: All cross-reference logic together
    """

    def __init__(
        self,
        reference_resolver: ReferenceResolver,
        validator: Any,  # Type hint as Any to avoid circular import
        config_path: Optional[Path] = None
    ):
        """
        Initialize CrossReferenceDetector.

        Args:
            reference_resolver: ReferenceResolver instance for pattern matching
            validator: RelationshipValidator instance for validation
            config_path: Optional path to configuration file

        Raises:
            CrossReferenceDetectorError: If initialization fails
        """
        self.reference_resolver = reference_resolver
        self.validator = validator
        self.config = self._load_config(config_path) if config_path else {}

        # Statistics
        self.stats = {
            'total_chunks_processed': 0,
            'total_references_detected': 0,
            'references_by_type': {'table': 0, 'equation': 0, 'figure': 0},
            'references_by_intent': {},
            'validation_pass': 0,
            'validation_fail': 0
        }

        logger.info("✅ CrossReferenceDetector initialized")

    def detect_cross_references(
        self,
        text_chunks: List[Dict[str, Any]]
    ) -> List[CrossReference]:
        """
        Detect all cross-references in text chunks.

        This method:
        1. For each text chunk
        2. Find reference phrases (via ReferenceResolver)
        3. Resolve to entity IDs (via ReferenceResolver)
        4. Extract context (surrounding sentences)
        5. Classify reference intent
        6. Build relationship dict
        7. Validate (entity exists)
        8. Filter failures

        Args:
            text_chunks: List of text chunk dicts with keys:
                - 'text': str (chunk text)
                - 'page': int (page number)
                - 'paragraph_id': str (optional)
                - 'section': str (optional)
                - 'chunk_id': str (optional)

        Returns:
            List of CrossReference objects (validated only)

        Raises:
            InvalidTextChunkError: If text chunk format is invalid
        """
        logger.info(f"Starting cross-reference detection for {len(text_chunks)} text chunks")

        cross_references = []

        for chunk_idx, chunk in enumerate(text_chunks):
            # Validate chunk format
            if not isinstance(chunk, dict) or 'text' not in chunk or 'page' not in chunk:
                logger.warning(f"Invalid text chunk format at index {chunk_idx}: {chunk}")
                continue

            try:
                # Find all references in this chunk
                chunk_refs = self._detect_in_chunk(chunk)
                cross_references.extend(chunk_refs)

                self.stats['total_chunks_processed'] += 1

            except Exception as e:
                logger.error(f"Error processing chunk {chunk_idx} on page {chunk.get('page', '?')}: {e}")
                continue

        # Update statistics
        self.stats['total_references_detected'] = len(cross_references)

        logger.info(f"✅ Detection complete: {len(cross_references)} cross-references found")
        logger.info(f"   By type: {self.stats['references_by_type']}")
        logger.info(f"   Validation: {self.stats['validation_pass']} pass, {self.stats['validation_fail']} fail")

        return cross_references

    def _detect_in_chunk(
        self,
        chunk: Dict[str, Any]
    ) -> List[CrossReference]:
        """
        Detect references in a single text chunk.

        Args:
            chunk: Text chunk dict

        Returns:
            List of CrossReference objects from this chunk
        """
        text = chunk['text']
        page = chunk['page']
        context = {
            'section': chunk.get('section'),
            'paragraph_id': chunk.get('paragraph_id'),
            'chunk_id': chunk.get('chunk_id')
        }

        # Find all reference instances via ReferenceResolver
        ref_instances = self.reference_resolver.find_all_references(
            text=text,
            page=page,
            context=context
        )

        # Convert each reference instance to CrossReference
        cross_refs = []
        for ref_instance in ref_instances:
            try:
                # Build CrossReference object
                cross_ref = self._build_cross_reference(ref_instance, chunk)

                # Validate entity existence
                validated_cross_ref = self._validate_cross_reference(cross_ref)

                # Only keep if validation passed or warned (skip failures)
                validation_status = validated_cross_ref.validation.get('overall_status') if isinstance(validated_cross_ref.validation, dict) else validated_cross_ref.validation

                logger.debug(f"Validation result for {cross_ref.relationship_id}: status={validation_status}, validation={validated_cross_ref.validation}")

                if validation_status in ['pass', 'warn']:
                    cross_refs.append(validated_cross_ref)
                    self.stats['validation_pass'] += 1

                    # Update type stats
                    ref_type = validated_cross_ref.reference_context['reference_type']
                    self.stats['references_by_type'][ref_type] = \
                        self.stats['references_by_type'].get(ref_type, 0) + 1
                else:
                    self.stats['validation_fail'] += 1
                    logger.debug(f"Filtered out failed reference: {validated_cross_ref.relationship_id}, status={validation_status}")

            except Exception as e:
                import traceback
                logger.warning(f"Failed to build cross-reference from {ref_instance.reference_id}: {e}")
                logger.debug(traceback.format_exc())
                continue

        return cross_refs

    def _build_cross_reference(
        self,
        ref_instance,  # ReferenceInstance from ReferenceResolver
        chunk: Dict[str, Any]
    ) -> CrossReference:
        """
        Build CrossReference object from ReferenceInstance.

        Args:
            ref_instance: ReferenceInstance from ReferenceResolver
            chunk: Original text chunk

        Returns:
            CrossReference object (not yet validated)
        """
        # Generate relationship ID
        ref_id_suffix = ref_instance.reference_id.split(':')[-1] if ':' in ref_instance.reference_id else 'unk'
        relationship_id = f"xref:{chunk.get('page', 0)}_{chunk.get('paragraph_id', 'unk')}_{ref_id_suffix}"

        # Build source ID
        source_id = self._build_source_id(chunk, ref_instance)

        # Extract reference phrase and context dicts for safe access
        ref_phrase_dict = ref_instance.reference_phrase if isinstance(ref_instance.reference_phrase, dict) else {}
        context_dict = ref_instance.context if isinstance(ref_instance.context, dict) else {}

        # Extract target entity ID
        target_dict = ref_instance.target if isinstance(ref_instance.target, dict) else {}
        target_id = target_dict.get('entity_id')

        if not target_id:
            # If resolution failed, use tentative ID
            ref_type = ref_phrase_dict.get('reference_type', 'unknown')
            target_id = f"{ref_type}:unknown"

        # Classify reference intent
        ref_phrase_text = ref_phrase_dict.get('raw_text', '')
        context_sentence = context_dict.get('full_sentence', '')
        reference_intent = self._classify_reference_intent(ref_phrase_text, context_sentence)

        # Update intent stats
        self.stats['references_by_intent'][reference_intent] = \
            self.stats['references_by_intent'].get(reference_intent, 0) + 1

        # Build reference_context dict
        reference_context = {
            'reference_phrase': ref_phrase_dict.get('raw_text', str(ref_instance.reference_phrase)),
            'reference_type': ref_phrase_dict.get('reference_type', 'unknown'),
            'reference_intent': reference_intent,
            'surrounding_text': context_dict.get('preceding_text', '') + context_dict.get('following_text', ''),
            'sentence': context_dict.get('full_sentence', ''),
            'page': chunk['page'],
            'section': chunk.get('section')
        }

        # Build confidence dict
        confidence = ref_instance.confidence.copy() if isinstance(ref_instance.confidence, dict) else {}

        # Placeholder validation (will be filled by _validate_cross_reference)
        validation = {
            'overall_status': 'pending',
            'checks': []
        }

        return CrossReference(
            relationship_id=relationship_id,
            edge_type='REFERENCES',
            source=source_id,
            target=target_id,
            reference_context=reference_context,
            confidence=confidence,
            validation=validation
        )

    def _build_source_id(
        self,
        chunk: Dict[str, Any],
        ref_instance: Any
    ) -> str:
        """
        Build source ID for text location.

        Format: "doc:page_{page}_paragraph_{id}"

        Args:
            chunk: Text chunk dict
            ref_instance: ReferenceInstance

        Returns:
            Source ID string
        """
        page = chunk['page']
        paragraph_id = chunk.get('paragraph_id', 'unk')

        return f"doc:page_{page}_paragraph_{paragraph_id}"

    def _extract_reference_context(
        self,
        text: str,
        match_position: int,
        match_length: int,
        page: int,
        section: Optional[str]
    ) -> Dict[str, Any]:
        """
        Extract context around reference phrase.

        This extracts:
        - Surrounding text (±100 chars)
        - Full sentence containing reference
        - Page and section metadata

        Args:
            text: Full text
            match_position: Starting position of reference phrase
            match_length: Length of reference phrase
            page: Page number
            section: Section name (optional)

        Returns:
            Context dict with surrounding_text, sentence, page, section
        """
        # Extract surrounding text (±100 chars)
        start = max(0, match_position - 100)
        end = min(len(text), match_position + match_length + 100)
        surrounding_text = text[start:end]

        # Extract full sentence
        # Find sentence boundaries (simple heuristic: periods)
        before = text[:match_position]
        after = text[match_position + match_length:]

        sentence_start = before.rfind('.') + 1
        sentence_end = after.find('.')

        if sentence_end == -1:
            sentence_end = len(after)

        sentence = text[sentence_start:match_position + match_length + sentence_end].strip()

        return {
            'surrounding_text': surrounding_text,
            'sentence': sentence,
            'page': page,
            'section': section
        }

    def _classify_reference_intent(
        self,
        reference_phrase: str,
        surrounding_text: str
    ) -> str:
        """
        Classify reference intent based on context.

        Intent categories:
        - COMPARISON: "compared to X", "versus X", "differs from X"
        - DATA_SOURCE: "from X", "data in X", "values given in X"
        - METHODOLOGY: "using X", "applies X", "computed with X"
        - VISUAL_REFERENCE: "shown in X", "illustrated in X", "depicted in X"
        - GENERAL: "see X", "refer to X", "as in X"

        Args:
            reference_phrase: The reference phrase (e.g., "Table 3")
            surrounding_text: Context around reference

        Returns:
            Intent category string
        """
        # Normalize text for pattern matching
        context_lower = surrounding_text.lower()

        # COMPARISON patterns
        comparison_patterns = [
            r'compar\w*\s+to',
            r'versus',
            r'better\s+than',
            r'differs?\s+from',
            r'different\s+from',
            r'in\s+contrast\s+to'
        ]
        for pattern in comparison_patterns:
            if re.search(pattern, context_lower):
                return 'COMPARISON'

        # DATA_SOURCE patterns
        data_source_patterns = [
            r'\bfrom\s+',  # "from Table X"
            r'data\s+in',
            r'values?\s+(given\s+)?in',
            r'listed\s+in',
            r'provided\s+in'
        ]
        for pattern in data_source_patterns:
            if re.search(pattern, context_lower):
                return 'DATA_SOURCE'

        # METHODOLOGY patterns
        methodology_patterns = [
            r'using',
            r'applies?',
            r'computed\s+with',
            r'calculated\s+(with|from)',
            r'evaluated\s+with',
            r'based\s+on'
        ]
        for pattern in methodology_patterns:
            if re.search(pattern, context_lower):
                return 'METHODOLOGY'

        # VISUAL_REFERENCE patterns
        visual_patterns = [
            r'shown\s+in',
            r'illustrated\s+in',
            r'depicted\s+in',
            r'presented\s+in',
            r'displayed\s+in'
        ]
        for pattern in visual_patterns:
            if re.search(pattern, context_lower):
                return 'VISUAL_REFERENCE'

        # GENERAL (default)
        return 'GENERAL'

    def _validate_cross_reference(
        self,
        cross_ref: CrossReference
    ) -> CrossReference:
        """
        Validate cross-reference using RelationshipValidator.

        This checks:
        - entity_exists: Does target entity actually exist?

        Args:
            cross_ref: CrossReference object to validate

        Returns:
            CrossReference with validation dict filled
        """
        # Build relationship dict for validator
        relationship = {
            'relationship_id': cross_ref.relationship_id,
            'type': 'cross_reference',
            'source': cross_ref.source,
            'target': cross_ref.target,
            'edge_type': cross_ref.edge_type
        }

        # Call validator
        try:
            validation_result = self.validator.validate_relationship(relationship)

            # Convert validation result to dict
            # Handle both real ValidationResult and Mock objects
            if hasattr(validation_result, 'to_dict') and callable(validation_result.to_dict):
                result_dict = validation_result.to_dict()
                # Check if to_dict() returned a dict (not another Mock)
                if isinstance(result_dict, dict):
                    cross_ref.validation = result_dict
                else:
                    # Mock object's to_dict() returned a Mock - extract attributes directly
                    cross_ref.validation = {
                        'overall_status': getattr(validation_result, 'overall_status', 'unknown'),
                        'checks': list(getattr(validation_result, 'checks', []))
                    }
            elif hasattr(validation_result, '__dict__'):
                # Convert dataclass/object to dict
                cross_ref.validation = {
                    'overall_status': getattr(validation_result, 'overall_status', 'unknown'),
                    'checks': [
                        check.to_dict() if (hasattr(check, 'to_dict') and callable(check.to_dict) and isinstance(check.to_dict(), dict)) else check
                        for check in (getattr(validation_result, 'checks', None) or [])
                    ]
                }
            else:
                # Fallback for simple mock objects
                cross_ref.validation = {
                    'overall_status': getattr(validation_result, 'overall_status', 'unknown'),
                    'checks': list(getattr(validation_result, 'checks', []))
                }

        except Exception as e:
            logger.warning(f"Validation failed for {cross_ref.relationship_id}: {e}")
            cross_ref.validation = {
                'overall_status': 'fail',
                'checks': [{
                    'check_type': 'entity_exists',
                    'status': 'fail',
                    'details': {'error': str(e)},
                    'message': f"Validation error: {e}"
                }]
            }

        return cross_ref

    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dict
        """
        import yaml

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
            return {}

    def export_to_json(
        self,
        cross_references: List[CrossReference],
        output_path: Path
    ) -> None:
        """
        Export cross-references to JSON file.

        Args:
            cross_references: List of CrossReference objects
            output_path: Path to output JSON file
        """
        import json

        output_path.parent.mkdir(parents=True, exist_ok=True)

        output_data = {
            'metadata': {
                'total_references': len(cross_references),
                'by_type': self.stats['references_by_type'],
                'by_intent': self.stats['references_by_intent'],
                'validation_stats': {
                    'pass': self.stats['validation_pass'],
                    'fail': self.stats['validation_fail']
                }
            },
            'cross_references': [cr.to_dict() for cr in cross_references]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Exported {len(cross_references)} cross-references to {output_path}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get detection statistics.

        Returns:
            Statistics dict
        """
        return self.stats.copy()
