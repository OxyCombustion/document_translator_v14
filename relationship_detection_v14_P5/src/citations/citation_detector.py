# -*- coding: utf-8 -*-
"""
Citation Detector - Detects citations in text to academic papers and external sources.

This detector identifies citation markers like [8], [11-13], Smith et al. (2020) and
resolves them to bibliographic reference IDs for provenance tracking.

Key Features:
    - Pattern-based citation detection via ReferenceResolver
    - Citation type classification (NUMERIC, AUTHOR_YEAR, SUPERSCRIPT)
    - Citation purpose classification (SUPPORTING_EVIDENCE, METHODOLOGY, etc.)
    - Context extraction (surrounding sentences)
    - Bibliographic reference validation
    - Confidence scoring based on resolution quality

Architecture:
    - Depends on: ReferenceResolver (pattern matching + disambiguation)
    - Depends on: RelationshipValidator (reference existence checks)
    - Low coupling: Minimal dependencies (2 injected services)
    - High cohesion: All methods focused on citation detection
    - Single Responsibility: Citation detection ONLY

Implementation Status:
✅ Phase 1: Core detection (detect_citations, _extract_context)
🔄 Phase 2: Type & purpose classification
⏸️ Phase 3: Integration & export

Author: V12 Development Team
Created: 2025-11-06
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
from dataclasses import dataclass
import re

from src.core.reference_resolver import ReferenceResolver, ResolvedReference

logger = logging.getLogger(__name__)


# ========== Data Structures ==========

@dataclass
class Citation:
    """
    Citation relationship from text/entity to bibliographic reference.

    This represents a citation in text (e.g., "[8]") resolved to a
    bibliographic reference ID (e.g., "ref:8").
    """
    relationship_id: str
    edge_type: str  # Always "CITES"
    source: str  # Source paragraph/entity ID (e.g., "doc:page_5_paragraph_2", "eq:9")
    target: str  # Target reference ID (e.g., "ref:8") or list for ranges

    citation_context: Dict[str, Any]  # Citation phrase, type, purpose, surrounding text, etc.
    bibliographic_info: Optional[Dict[str, Any]]  # Authors, title, year, DOI, etc.
    confidence: Dict[str, Any]  # Confidence score, method, factors
    validation: Dict[str, Any]  # Validation result from validator

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'relationship_id': self.relationship_id,
            'edge_type': self.edge_type,
            'source': self.source,
            'target': self.target,
            'citation_context': self.citation_context,
            'bibliographic_info': self.bibliographic_info,
            'confidence': self.confidence,
            'validation': self.validation
        }


# ========== Exceptions ==========

class CitationDetectorError(Exception):
    """Base exception for CitationDetector errors."""
    pass


class InvalidTextChunkError(CitationDetectorError):
    """Raised when text chunk format is invalid."""
    pass


class BibliographyNotFoundError(CitationDetectorError):
    """Raised when bibliography index is not available."""
    pass


# ========== Citation Detector ==========

class CitationDetector:
    """
    Detect citations in text to academic papers and external sources.

    This detector uses ReferenceResolver for pattern-based citation detection
    and resolves citation markers to bibliographic reference IDs.

    Design Principles:
        - Single Responsibility: Citation detection only
        - Dependency Injection: ReferenceResolver and Validator injected
        - Low Coupling: Only depends on 2 injected services
        - High Cohesion: All methods focused on citation detection
    """

    def __init__(
        self,
        reference_resolver: ReferenceResolver,
        validator: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize CitationDetector with dependency injection.

        Args:
            reference_resolver: ReferenceResolver for pattern matching
            validator: RelationshipValidator for reference existence checks (optional)
            config: Configuration dictionary (optional)
        """
        self.reference_resolver = reference_resolver
        self.validator = validator
        self.config = config or {}

        # Configuration parameters
        self.confidence_threshold = self.config.get('confidence_threshold', 0.80)
        self.context_window_chars = self.config.get('context_window_chars', 100)
        self.bibliography_index: Dict[str, Dict[str, Any]] = {}

        logger.info("CitationDetector initialized (confidence_threshold=%.2f)", self.confidence_threshold)

    def set_bibliography_index(self, bibliography: Dict[str, Dict[str, Any]]) -> None:
        """
        Set the bibliography index for reference metadata lookup.

        Args:
            bibliography: Dictionary mapping reference IDs (e.g., "ref:8") to
                         bibliographic metadata (authors, title, year, DOI)

        Example:
            bibliography = {
                "ref:8": {
                    "reference_id": "ref:8",
                    "reference_number": 8,
                    "authors": ["Modest, M.F."],
                    "title": "Radiative Heat Transfer",
                    "year": 2013,
                    "doi": "10.1016/B978-0-12-386944-9.50023-6"
                }
            }
        """
        self.bibliography_index = bibliography
        logger.info("Bibliography index set: %d references", len(bibliography))

    def detect_citations(
        self,
        text_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect all citations in text chunks.

        This is the main entry point for citation detection. It:
        1. Iterates through text chunks
        2. Finds citation phrases using ReferenceResolver
        3. Resolves citations to bibliographic reference IDs
        4. Extracts context (surrounding sentences)
        5. Classifies citation type and purpose
        6. Builds Citation relationship dicts
        7. Validates (reference exists)
        8. Filters failures

        Args:
            text_chunks: List of text chunk dicts with keys:
                        - 'chunk_id': Unique chunk identifier
                        - 'text': Text content
                        - 'page': Page number
                        - 'section': Section name (optional)

        Returns:
            List of validated citation relationship dicts

        Raises:
            InvalidTextChunkError: If text chunk format is invalid
        """
        if not text_chunks:
            logger.warning("No text chunks provided for citation detection")
            return []

        logger.info("Starting citation detection on %d text chunks", len(text_chunks))

        all_citations = []
        citation_count = 0
        filtered_count = 0

        for chunk in text_chunks:
            # Validate chunk format
            if not self._validate_text_chunk(chunk):
                continue

            # Find all citation matches in this chunk
            matches = self.reference_resolver.find_all_matches(
                text=chunk['text'],
                reference_type='citation'
            )

            if not matches:
                continue

            logger.debug("Found %d citation matches in chunk %s", len(matches), chunk.get('chunk_id', 'unknown'))

            # Process each citation match
            for match in matches:
                # Resolve citation to reference ID
                resolved = self.reference_resolver.resolve_reference(
                    reference_phrase=match.matched_text,
                    reference_type='citation',
                    page=chunk.get('page', 0),
                    context={'section': chunk.get('section', '')}
                )

                # Filter low-confidence resolutions
                if resolved.confidence < self.confidence_threshold:
                    filtered_count += 1
                    logger.debug(
                        "Filtered citation '%s' (confidence=%.2f < %.2f)",
                        match.matched_text, resolved.confidence, self.confidence_threshold
                    )
                    continue

                # Build citation relationship
                citation = self._build_citation(match, resolved, chunk)

                # Validate citation (reference exists check)
                if self.validator:
                    validated = self._validate_citation(citation)
                    citation['validation'] = validated

                    # Filter failed validations
                    if validated.get('overall_status') == 'fail':
                        filtered_count += 1
                        logger.debug("Filtered citation '%s' (validation failed)", match.matched_text)
                        continue

                all_citations.append(citation)
                citation_count += 1

        logger.info(
            "Citation detection complete: %d citations found, %d filtered (%.1f%% success)",
            citation_count, filtered_count,
            100 * citation_count / (citation_count + filtered_count) if (citation_count + filtered_count) > 0 else 0
        )

        return all_citations

    def _validate_text_chunk(self, chunk: Dict[str, Any]) -> bool:
        """
        Validate text chunk has required fields.

        Args:
            chunk: Text chunk dictionary

        Returns:
            True if valid, False otherwise

        Raises:
            InvalidTextChunkError: If chunk is critically invalid
        """
        if not isinstance(chunk, dict):
            raise InvalidTextChunkError(f"Text chunk must be dictionary, got {type(chunk)}")

        if 'text' not in chunk:
            logger.warning("Text chunk missing 'text' field: %s", chunk.keys())
            return False

        if not chunk['text'] or not isinstance(chunk['text'], str):
            logger.warning("Text chunk has empty or invalid 'text' field")
            return False

        return True

    def _build_citation(
        self,
        match: Any,  # MatchResult from PatternMatcher
        resolved: ResolvedReference,
        chunk: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build Citation relationship dict from match and resolved reference.

        Args:
            match: MatchResult from ReferenceResolver pattern matching
            resolved: ResolvedReference with entity_id, confidence, etc.
            chunk: Source text chunk with chunk_id, page, section

        Returns:
            Citation relationship dict matching specification format
        """
        # Generate unique relationship ID
        source_id = chunk.get('chunk_id', f"doc:page_{chunk.get('page', 0)}_chunk")
        target_id = resolved.entity_id
        relationship_id = f"cite:{source_id}_{target_id}_{match.start_pos}"

        # Extract context around citation
        context = self._extract_citation_context(
            text=chunk['text'],
            match_position=match.start_pos,
            match_length=len(match.matched_text),
            page=chunk.get('page', 0),
            section=chunk.get('section', '')
        )

        # Classify citation type and purpose
        citation_type = self._classify_citation_type(match.matched_text)
        citation_purpose = self._classify_citation_purpose(
            citation_phrase=match.matched_text,
            surrounding_text=context['surrounding_text']
        )

        # Get bibliographic metadata
        bibliographic_info = self._extract_bibliographic_info(target_id)

        # Build citation dict
        citation = {
            'relationship_id': relationship_id,
            'edge_type': 'CITES',
            'source': source_id,
            'target': target_id,
            'citation_context': {
                'citation_phrase': match.matched_text,
                'citation_type': citation_type,
                'citation_purpose': citation_purpose,
                'surrounding_text': context['surrounding_text'],
                'sentence': context['sentence'],
                'page': chunk.get('page', 0),
                'section': chunk.get('section', '')
            },
            'bibliographic_info': bibliographic_info,
            'confidence': {
                'score': resolved.confidence,
                'method': resolved.disambiguation_method,
                'factors': {
                    'pattern_match': 1.0,  # Pattern matched perfectly
                    'reference_exists': 1.0 if bibliographic_info else 0.5
                }
            },
            'validation': {}  # Filled by validator if available
        }

        return citation

    def _extract_citation_context(
        self,
        text: str,
        match_position: int,
        match_length: int,
        page: int,
        section: str
    ) -> Dict[str, Any]:
        """
        Extract context around citation phrase.

        This extracts:
        1. Surrounding text (±100 characters around citation)
        2. Full sentence containing citation
        3. Page and section information

        Args:
            text: Full text of chunk
            match_position: Character position of citation match start
            match_length: Length of matched citation phrase
            page: Page number
            section: Section name

        Returns:
            Context dict with 'surrounding_text', 'sentence', 'page', 'section'
        """
        # Extract surrounding text (±context_window_chars)
        start = max(0, match_position - self.context_window_chars)
        end = min(len(text), match_position + match_length + self.context_window_chars)
        surrounding_text = text[start:end]

        # Extract full sentence containing citation
        sentence = self._extract_sentence(text, match_position)

        return {
            'surrounding_text': surrounding_text,
            'sentence': sentence,
            'page': page,
            'section': section
        }

    def _extract_sentence(self, text: str, position: int) -> str:
        """
        Extract full sentence containing position.

        Args:
            text: Full text
            position: Character position to find sentence for

        Returns:
            Full sentence containing position
        """
        # Find sentence boundaries (simple heuristic: periods followed by space/newline)
        sentence_end_pattern = r'[.!?]\s+'

        # Find start of sentence (search backward)
        start = 0
        for match in re.finditer(sentence_end_pattern, text[:position]):
            start = match.end()

        # Find end of sentence (search forward)
        end = len(text)
        match = re.search(sentence_end_pattern, text[position:])
        if match:
            end = position + match.start() + 1  # Include period

        sentence = text[start:end].strip()
        return sentence

    def _classify_citation_type(self, citation_phrase: str) -> str:
        """
        Classify citation type based on format.

        Citation Types:
        - NUMERIC: [8], [11], [11-13], [8,9,11]
        - AUTHOR_YEAR: Smith et al. (2020), (Jones, 2015)
        - SUPERSCRIPT: ¹, ²³, ⁴⁻⁶

        Args:
            citation_phrase: Citation text (e.g., "[8]", "Smith et al. (2020)")

        Returns:
            Citation type string
        """
        # NUMERIC: [8], [11-13], [8,11,15]
        if re.match(r'^\[\d+(?:[,-]\d+)*\]$', citation_phrase):
            return 'NUMERIC'

        # SUPERSCRIPT: ¹, ²³, ⁴⁻⁶
        if re.match(r'^[⁰¹²³⁴⁵⁶⁷⁸⁹⁻–]+$', citation_phrase):
            return 'SUPERSCRIPT'

        # AUTHOR_YEAR: Smith et al. (2020), (Jones, 2015)
        if re.search(r'\(\d{4}\)', citation_phrase):
            return 'AUTHOR_YEAR'

        # Default
        return 'UNKNOWN'

    def _classify_citation_purpose(
        self,
        citation_phrase: str,
        surrounding_text: str
    ) -> str:
        """
        Classify citation purpose based on context.

        Citation Purposes:
        - SUPPORTING_EVIDENCE: "measured [8]", "confirmed by [8]"
        - METHODOLOGY: "following [8]", "using the method of [8]"
        - COMPARISON: "unlike [8]", "compared to [8]"
        - BACKGROUND: "as shown in [8]", "see [8]"
        - GENERAL: default category

        Args:
            citation_phrase: Citation text
            surrounding_text: Text around citation (±100 chars)

        Returns:
            Citation purpose string
        """
        # Normalize for case-insensitive matching
        context_lower = surrounding_text.lower()

        # Escape special characters in citation phrase for regex
        citation_escaped = re.escape(citation_phrase.lower())

        # Check patterns in order of specificity (most specific first)

        # BACKGROUND patterns (most specific phrases)
        background_patterns = [
            r'as\s+shown\s+in\s+' + citation_escaped,
            r'see\s+' + citation_escaped,
            r'refer\s+to\s+' + citation_escaped,
            r'described\s+in\s+' + citation_escaped,
            r'for\s+(?:more\s+)?details\s+see\s+' + citation_escaped,
        ]
        for pattern in background_patterns:
            if re.search(pattern, context_lower):
                return 'BACKGROUND'

        # COMPARISON patterns
        comparison_patterns = [
            r'unlike\s+(?:the\s+)?(?:results\s+(?:in|from)\s+)?' + citation_escaped,
            r'compared\s+(?:to|with)\s+' + citation_escaped,
            r'in\s+contrast\s+to\s+' + citation_escaped,
            r'different\s+from\s+' + citation_escaped,
        ]
        for pattern in comparison_patterns:
            if re.search(pattern, context_lower):
                return 'COMPARISON'

        # METHODOLOGY patterns
        methodology_patterns = [
            r'following\s+(?:the\s+)?(?:method\s+(?:of|from|in)\s+)?' + citation_escaped,
            r'using\s+(?:the\s+)?(?:method|approach|technique)\s+(?:of|from|in)\s+' + citation_escaped,
            r'according\s+to\s+' + citation_escaped,
            r'based\s+on\s+' + citation_escaped,
            r'derived\s+(?:from|in)\s+' + citation_escaped,
            r'method\s+of\s+' + citation_escaped,
        ]
        for pattern in methodology_patterns:
            if re.search(pattern, context_lower):
                return 'METHODOLOGY'

        # SUPPORTING_EVIDENCE patterns (more general, so checked last)
        evidence_patterns = [
            r'measured\s+' + citation_escaped,
            r'confirmed\s+(?:by|in)\s+' + citation_escaped,
            r'demonstrated\s+(?:by|in)\s+' + citation_escaped,
            r'shown\s+(?:by|in)\s+' + citation_escaped,  # Note: "as shown in" handled above
            r'reported\s+(?:by|in)\s+' + citation_escaped,
            r'observed\s+(?:by|in)\s+' + citation_escaped,
        ]
        for pattern in evidence_patterns:
            if re.search(pattern, context_lower):
                return 'SUPPORTING_EVIDENCE'

        # Default to GENERAL
        return 'GENERAL'

    def _extract_bibliographic_info(self, reference_id: str) -> Optional[Dict[str, Any]]:
        """
        Extract bibliographic metadata from reference database.

        Args:
            reference_id: Reference ID (e.g., "ref:8")

        Returns:
            Bibliographic metadata dict or None if not found
        """
        if not self.bibliography_index:
            logger.debug("Bibliography index not set, cannot extract metadata for %s", reference_id)
            return None

        if reference_id not in self.bibliography_index:
            logger.debug("Reference %s not found in bibliography index", reference_id)
            return None

        return self.bibliography_index[reference_id]

    def _validate_citation(self, citation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate citation using RelationshipValidator.

        This calls validator.validate_relationship() to check:
        - Reference exists in bibliography
        - Citation is relevant to source context

        Args:
            citation: Citation relationship dict

        Returns:
            Validation result dict with overall_status and checks
        """
        if not self.validator:
            # No validator available, return pass
            return {
                'overall_status': 'pass',
                'checks': []
            }

        # Call validator (assuming it has validate_relationship method)
        try:
            validation = self.validator.validate_relationship(citation)
            return validation
        except Exception as e:
            logger.error("Validation failed for citation %s: %s", citation['relationship_id'], e)
            return {
                'overall_status': 'error',
                'checks': [
                    {
                        'check_type': 'validation_error',
                        'status': 'fail',
                        'details': {'error': str(e)}
                    }
                ]
            }
