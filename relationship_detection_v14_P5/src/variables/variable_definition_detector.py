# -*- coding: utf-8 -*-
"""
Variable Definition Detector - Links variable symbols to their canonical definitions.

This detector extracts variable definitions from multiple sources:
1. Nomenclature/Symbols section (highest confidence: 0.98)
2. Inline definitions ("where ε is emissivity...") (medium confidence: 0.85)
3. Equation captions (lower confidence: 0.70)
4. Table headers (lower confidence: 0.70)

Integrates with:
    - SemanticRegistry: register_variable(), resolve_symbol()
    - Validator: validate_relationship()

Architecture:
    - Single Responsibility: Variable definition detection only
    - Dependency Injection: Constructor injection for SR, Validator
    - Low Coupling: Minimal dependencies on SemanticRegistry and Validator
    - High Cohesion: All variable definition logic in one place

Author: V12 Development Team
Created: 2025-11-03
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

import re
import json
import logging
import yaml
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


# Custom Exceptions
class VariableDefinitionDetectorError(Exception):
    """Base exception for Variable Definition Detector errors."""
    pass


class ConfigurationError(VariableDefinitionDetectorError):
    """Raised when configuration is invalid."""
    pass


class DetectionError(VariableDefinitionDetectorError):
    """Raised when variable definition detection fails."""
    pass


# Data Structures
@dataclass
class VariableDefinition:
    """
    Complete variable definition with confidence scoring.

    This represents one detected variable definition from any source.
    """
    # Core variable information
    symbol: str  # Primary symbol (e.g., "ε")
    name: str  # Variable name (e.g., "emissivity")
    definition_text: str  # Full definition text

    # Source information
    source_type: str  # nomenclature_section | inline | equation_caption | table_header
    source_location: Dict[str, Any]  # {page, section, entity_id, paragraph_id}

    # Units and dimension
    units: Optional[Dict[str, Any]] = None  # {dimension, si_unit, allowed_range}
    dimension: Optional[str] = None  # Dimensional formula

    # Confidence
    confidence: float = 0.0  # Overall confidence score
    confidence_factors: Dict[str, float] = field(default_factory=dict)

    # Metadata
    aliases: List[str] = field(default_factory=list)
    semantic_tags: List[str] = field(default_factory=list)
    context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class NomenclatureSection:
    """Detected nomenclature section with entries."""
    page: int
    section_id: str
    header_text: str
    entries: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.98


class VariableDefinitionDetector:
    """
    Detector for variable definitions from multiple sources.

    This class coordinates pattern matching and definition extraction
    to link variable symbols to their canonical definitions.

    Dependencies (Dependency Injection):
        - SemanticRegistry: Injected via constructor
        - Validator: Injected via constructor (optional)

    Key Responsibilities:
        - Detect nomenclature sections
        - Parse inline definitions
        - Extract from equation captions
        - Extract from table headers
        - Register variables in SemanticRegistry
        - Validate relationships before export

    Design Principles:
        - Single Responsibility: Variable definition detection only
        - Dependency Inversion: Depends on SR/Validator abstractions
        - Low Coupling: Minimal dependencies
        - High Cohesion: All definition logic together
    """

    def __init__(
        self,
        config_path: Path,
        semantic_registry: Any,  # Type hint as Any to avoid circular import
        validator: Optional[Any] = None
    ):
        """
        Initialize VariableDefinitionDetector.

        Args:
            config_path: Path to variable_definition_patterns.yaml
            semantic_registry: SemanticRegistry instance
            validator: Optional Validator instance

        Raises:
            ConfigurationError: If configuration is invalid
        """
        self.config_path = Path(config_path)
        self.semantic_registry = semantic_registry
        self.validator = validator

        # Load configuration
        self.config = self._load_config()
        self.patterns = self._compile_patterns()

        # Detection results storage
        self.detected_definitions: List[VariableDefinition] = []
        self.definition_index: Dict[str, List[VariableDefinition]] = {}  # symbol → [definitions]

        logger.info("✅ VariableDefinitionDetector initialized")

    def _load_config(self) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """
        Compile regex patterns from configuration.

        Returns:
            Dict mapping pattern group names to compiled regex patterns
        """
        compiled = {}

        # Nomenclature section patterns
        if self.config['detection_methods']['nomenclature_section']['enabled']:
            nom_patterns = self.config['detection_methods']['nomenclature_section']['patterns']

            compiled['nomenclature_headers'] = [
                re.compile(p, re.MULTILINE) for p in nom_patterns['section_headers']
            ]

            compiled['nomenclature_entries'] = []
            for entry_fmt in nom_patterns['entry_formats']:
                compiled['nomenclature_entries'].append({
                    'pattern': re.compile(entry_fmt['pattern'], re.MULTILINE),
                    'groups': entry_fmt['groups'],
                    'confidence': entry_fmt['confidence']
                })

        # Inline definition patterns
        if self.config['detection_methods']['inline_definitions']['enabled']:
            inline_patterns = self.config['detection_methods']['inline_definitions']['patterns']

            compiled['inline_where'] = []
            for pattern_spec in inline_patterns['where_clause']:
                compiled['inline_where'].append({
                    'pattern': re.compile(pattern_spec['pattern'], re.MULTILINE | re.IGNORECASE),
                    'groups': pattern_spec['groups'],
                    'confidence': pattern_spec['confidence']
                })

            compiled['inline_parenthetical'] = []
            for pattern_spec in inline_patterns['parenthetical']:
                compiled['inline_parenthetical'].append({
                    'pattern': re.compile(pattern_spec['pattern']),
                    'groups': pattern_spec['groups'],
                    'confidence': pattern_spec['confidence']
                })

        # Equation caption patterns
        if self.config['detection_methods']['equation_captions']['enabled']:
            caption_patterns = self.config['detection_methods']['equation_captions']['patterns']

            compiled['equation_captions'] = []
            for pattern_spec in caption_patterns:
                compiled['equation_captions'].append({
                    'pattern': re.compile(pattern_spec['pattern'], re.IGNORECASE),
                    'groups': pattern_spec['groups'],
                    'confidence': pattern_spec['confidence']
                })

        # Table header patterns
        if self.config['detection_methods']['table_headers']['enabled']:
            table_patterns = self.config['detection_methods']['table_headers']['patterns']

            compiled['table_headers'] = []
            for pattern_spec in table_patterns:
                compiled['table_headers'].append({
                    'pattern': re.compile(pattern_spec['pattern']),
                    'groups': pattern_spec['groups'],
                    'confidence': pattern_spec['confidence']
                })

        logger.debug(f"Compiled {sum(len(v) if isinstance(v, list) else 1 for v in compiled.values())} patterns")
        return compiled

    # ========== Phase 2: Nomenclature Section Detector ==========

    def detect_nomenclature_sections(
        self,
        document_chunks: List[Dict[str, Any]]
    ) -> List[NomenclatureSection]:
        """
        Detect nomenclature/symbols sections in document.

        This method:
        1. Scans text blocks for section headers
        2. Identifies section boundaries
        3. Parses variable entries within section
        4. Returns structured nomenclature sections

        Args:
            document_chunks: List of semantic chunks with text and metadata

        Returns:
            List of detected NomenclatureSection objects
        """
        sections = []

        for chunk in document_chunks:
            text = chunk.get('text', '')
            page = chunk.get('page', -1)
            chunk_id = chunk.get('chunk_id', 'unknown')

            # Check for nomenclature section headers
            for header_pattern in self.patterns.get('nomenclature_headers', []):
                matches = header_pattern.finditer(text)
                for match in matches:
                    # Found nomenclature section
                    section = self._parse_nomenclature_section(
                        text=text,
                        page=page,
                        chunk_id=chunk_id,
                        header_match=match
                    )
                    if section:
                        sections.append(section)
                        logger.info(f"✅ Found nomenclature section on page {page} with {len(section.entries)} entries")

        return sections

    def _parse_nomenclature_section(
        self,
        text: str,
        page: int,
        chunk_id: str,
        header_match: re.Match
    ) -> Optional[NomenclatureSection]:
        """
        Parse nomenclature section entries.

        Args:
            text: Full text
            page: Page number
            chunk_id: Chunk identifier
            header_match: Regex match for section header

        Returns:
            NomenclatureSection or None if parsing fails
        """
        header_text = header_match.group(0).strip()
        section_start = header_match.end()

        # Find section end (next major header or end of text)
        section_end = len(text)
        # Simple heuristic: next blank line followed by all-caps line
        remaining_text = text[section_start:]

        # Extract entries
        entries = []
        for entry_spec in self.patterns.get('nomenclature_entries', []):
            pattern = entry_spec['pattern']
            groups = entry_spec['groups']
            confidence = entry_spec['confidence']

            # Search in section text only
            section_text = text[section_start:section_end]
            matches = pattern.finditer(section_text)

            for match in matches:
                entry = self._extract_nomenclature_entry(
                    match=match,
                    groups=groups,
                    confidence=confidence,
                    page=page,
                    chunk_id=chunk_id
                )
                if entry:
                    entries.append(entry)

        # Create section object
        if entries:
            section = NomenclatureSection(
                page=page,
                section_id=f"nomenclature_{chunk_id}",
                header_text=header_text,
                entries=entries,
                confidence=0.98
            )
            return section

        return None

    def _extract_nomenclature_entry(
        self,
        match: re.Match,
        groups: Dict[str, int],
        confidence: float,
        page: int,
        chunk_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract variable definition from nomenclature entry match.

        Args:
            match: Regex match
            groups: Group name → group index mapping
            confidence: Base confidence score
            page: Page number
            chunk_id: Chunk identifier

        Returns:
            Entry dict or None if extraction fails
        """
        try:
            # Extract groups
            entry = {}
            for group_name, group_idx in groups.items():
                value = match.group(group_idx)
                if value:
                    entry[group_name] = value.strip()

            # Must have at least symbol
            if 'symbol' not in entry:
                return None

            # Parse units if present
            units_info = None
            if 'units' in entry:
                units_info = self._parse_units(entry['units'])
            elif 'definition_text' in entry:
                # Try to extract units from definition text
                units_info = self._extract_units_from_text(entry['definition_text'])

            # Extract name if not explicit
            if 'name' not in entry and 'definition_text' in entry:
                name = self._extract_variable_name(entry['definition_text'])
                if name:
                    entry['name'] = name

            return {
                'symbol': entry['symbol'],
                'name': entry.get('name', entry['symbol']),
                'definition_text': entry.get('definition_text', ''),
                'units': units_info,
                'confidence': confidence,
                'source_page': page,
                'source_chunk': chunk_id
            }

        except Exception as e:
            logger.warning(f"Failed to extract nomenclature entry: {e}")
            return None

    def _parse_units(self, units_str: str) -> Optional[Dict[str, Any]]:
        """
        Parse units string to extract dimension and SI unit.

        Args:
            units_str: Units string (e.g., "W/m·K" or "dimensionless")

        Returns:
            Units dict or None
        """
        units_str = units_str.strip()

        # Check for dimensionless
        for pattern_spec in self.config.get('unit_patterns', {}).get('dimensionless', []):
            pattern = pattern_spec['pattern']
            if re.search(pattern, units_str, re.IGNORECASE):
                return {
                    'dimension': 'dimensionless',
                    'si_unit': '1',
                    'raw_text': units_str
                }

        # Try standard unit patterns
        for pattern_spec in (self.config.get('unit_patterns', {}).get('with_exponents', []) +
                            self.config.get('unit_patterns', {}).get('standard_notation', [])):
            pattern = pattern_spec['pattern']
            match = re.search(pattern, units_str)
            if match:
                return {
                    'si_unit': match.group(1),
                    'raw_text': units_str
                }

        return None

    def _extract_units_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract units from definition text.

        Looks for patterns like:
        - "emissivity, dimensionless"
        - "thermal conductivity, W/m·K"
        - "thermal conductivity (W/m·K)"

        Args:
            text: Definition text

        Returns:
            Units dict or None
        """
        # Pattern 1: Look for parenthetical units at end: "thermal conductivity (W/m·K)"
        parenthetical_match = re.search(r'\(([^)]+)\)\s*$', text)
        if parenthetical_match:
            potential_units = parenthetical_match.group(1).strip()
            units = self._parse_units(potential_units)
            if units:
                return units

        # Pattern 2: Look for comma-separated units at end: "emissivity, dimensionless"
        parts = text.rsplit(',', 1)
        if len(parts) == 2:
            potential_units = parts[1].strip()
            return self._parse_units(potential_units)

        return None

    def _extract_variable_name(self, definition_text: str) -> Optional[str]:
        """
        Extract variable name from definition text.

        Args:
            definition_text: Definition text

        Returns:
            Variable name or None
        """
        # Take first phrase before comma or "or"
        parts = re.split(r',|\s+or\s+', definition_text, maxsplit=1)
        if parts:
            name = parts[0].strip()
            # Remove units if present
            name = re.sub(r'\s+[A-Z][a-z]*(/[A-Z].*)?$', '', name)
            return name

        return None

    # ========== Phase 3: Inline Definition Detector ==========

    def detect_inline_definitions(
        self,
        document_chunks: List[Dict[str, Any]]
    ) -> List[VariableDefinition]:
        """
        Detect inline variable definitions in text.

        Patterns detected:
        - "where ε is emissivity..."
        - "where: ε = emissivity"
        - "where σ is the Stefan-Boltzmann constant (5.67×10⁻⁸ W/m²·K⁴)"
        - "emissivity (ε)"
        - "ε (emissivity)"

        Args:
            document_chunks: List of semantic chunks

        Returns:
            List of VariableDefinition objects
        """
        definitions = []

        for chunk in document_chunks:
            text = chunk.get('text', '')
            page = chunk.get('page', -1)
            chunk_id = chunk.get('chunk_id', 'unknown')

            # Try where-clause patterns
            for pattern_spec in self.patterns.get('inline_where', []):
                matches = pattern_spec['pattern'].finditer(text)
                for match in matches:
                    var_def = self._extract_inline_where_definition(
                        match=match,
                        groups=pattern_spec['groups'],
                        confidence=pattern_spec['confidence'],
                        page=page,
                        chunk_id=chunk_id,
                        text=text
                    )
                    if var_def:
                        definitions.append(var_def)

            # Try parenthetical patterns
            for pattern_spec in self.patterns.get('inline_parenthetical', []):
                matches = pattern_spec['pattern'].finditer(text)
                for match in matches:
                    var_def = self._extract_inline_parenthetical_definition(
                        match=match,
                        groups=pattern_spec['groups'],
                        confidence=pattern_spec['confidence'],
                        page=page,
                        chunk_id=chunk_id,
                        text=text
                    )
                    if var_def:
                        definitions.append(var_def)

        logger.info(f"✅ Detected {len(definitions)} inline variable definitions")
        return definitions

    def _extract_inline_where_definition(
        self,
        match: re.Match,
        groups: Dict[str, int],
        confidence: float,
        page: int,
        chunk_id: str,
        text: str
    ) -> Optional[VariableDefinition]:
        """Extract variable definition from 'where' clause match."""
        try:
            symbol = match.group(groups['symbol']).strip()

            # Get definition
            if 'definition' in groups:
                definition = match.group(groups['definition']).strip()
                # For "where ε is the total emissivity", extract the noun
                # Look for pattern: "the <adjective>* <noun>" or just "<noun>"
                name = self._extract_primary_noun(definition)
                if not name:
                    name = self._extract_variable_name(definition)
            elif 'name' in groups:
                name = match.group(groups['name']).strip()
                definition = name
            else:
                return None

            # Extract context
            context = self._extract_context(text, match.start(), match.end())

            # Parse units
            units = None
            if 'value_or_units' in groups:
                value_or_units = match.group(groups['value_or_units']).strip()
                units = self._parse_units(value_or_units)
            else:
                units = self._extract_units_from_text(definition)

            return VariableDefinition(
                symbol=symbol,
                name=name or symbol,
                definition_text=definition,
                source_type='inline_where_clause',
                source_location={
                    'page': page,
                    'chunk_id': chunk_id,
                    'char_offset': [match.start(), match.end()]
                },
                units=units,
                confidence=confidence,
                confidence_factors={'pattern_match': confidence},
                context=context
            )

        except Exception as e:
            logger.warning(f"Failed to extract inline where definition: {e}")
            return None

    def _extract_primary_noun(self, definition: str) -> Optional[str]:
        """
        Extract primary noun from definition text.

        Examples:
            "the total emissivity of the surface" → "emissivity"
            "the Stefan-Boltzmann constant" → "Stefan-Boltzmann constant"
            "temperature" → "temperature"

        Args:
            definition: Definition text

        Returns:
            Primary noun or None
        """
        # Remove leading articles and common words
        definition = definition.strip()

        # Pattern: "the <adj>* <noun>" - extract noun
        # Simple heuristic: take first noun-like word (starts with lowercase, > 3 chars)
        words = definition.split()

        # Skip articles and common modifiers
        skip_words = {'the', 'a', 'an', 'this', 'that', 'total', 'overall', 'average', 'mean'}
        filtered_words = [w for w in words if w.lower() not in skip_words]

        # Find first substantial word (likely the noun)
        for word in filtered_words:
            # Remove punctuation
            clean_word = word.strip('.,;:!?')
            # Check if it's a noun-like word (length > 3, not all uppercase)
            if len(clean_word) > 3 and not clean_word.isupper():
                # Handle compound nouns (e.g., "Stefan-Boltzmann")
                # Look for following hyphenated or capitalized words
                idx = filtered_words.index(word)
                noun_parts = [clean_word]
                for next_word in filtered_words[idx+1:]:
                    next_clean = next_word.strip('.,;:!?')
                    # Stop if we hit "of", "for", etc.
                    if next_clean.lower() in {'of', 'for', 'in', 'on', 'at', 'by'}:
                        break
                    # Include if hyphenated or part of compound
                    if '-' in next_word or next_clean[0].isupper():
                        noun_parts.append(next_clean)
                    else:
                        break

                return ' '.join(noun_parts)

        return None

    def _extract_inline_parenthetical_definition(
        self,
        match: re.Match,
        groups: Dict[str, int],
        confidence: float,
        page: int,
        chunk_id: str,
        text: str
    ) -> Optional[VariableDefinition]:
        """Extract variable definition from parenthetical match."""
        try:
            # Determine which group is symbol and which is name
            if 'symbol' in groups and 'name' in groups:
                symbol = match.group(groups['symbol']).strip()
                name = match.group(groups['name']).strip()
            else:
                # Heuristic: shorter one is symbol
                g1 = match.group(1).strip()
                g2 = match.group(2).strip()
                if len(g1) <= 3:
                    symbol, name = g1, g2
                else:
                    symbol, name = g2, g1

            # Extract context
            context = self._extract_context(text, match.start(), match.end())

            return VariableDefinition(
                symbol=symbol,
                name=name,
                definition_text=f"{name} ({symbol})",
                source_type='inline_parenthetical',
                source_location={
                    'page': page,
                    'chunk_id': chunk_id,
                    'char_offset': [match.start(), match.end()]
                },
                confidence=confidence,
                confidence_factors={'pattern_match': confidence},
                context=context
            )

        except Exception as e:
            logger.warning(f"Failed to extract parenthetical definition: {e}")
            return None

    def _extract_context(
        self,
        text: str,
        start_pos: int,
        end_pos: int
    ) -> Dict[str, Any]:
        """
        Extract surrounding context for definition.

        Args:
            text: Full text
            start_pos: Match start position
            end_pos: Match end position

        Returns:
            Context dict with preceding/following text
        """
        window_before = self.config['context']['window_before_chars']
        window_after = self.config['context']['window_after_chars']

        context_start = max(0, start_pos - window_before)
        context_end = min(len(text), end_pos + window_after)

        return {
            'preceding_text': text[context_start:start_pos],
            'following_text': text[end_pos:context_end],
            'full_sentence': self._extract_sentence(text, start_pos, end_pos)
        }

    def _extract_sentence(
        self,
        text: str,
        start_pos: int,
        end_pos: int
    ) -> str:
        """Extract full sentence containing the match."""
        # Find sentence boundaries
        sentence_start = text.rfind('.', 0, start_pos) + 1
        sentence_end = text.find('.', end_pos)
        if sentence_end == -1:
            sentence_end = len(text)

        return text[sentence_start:sentence_end].strip()

    # ========== Phase 4: Equation Caption & Table Header Detector ==========

    def detect_from_equation_captions(
        self,
        equation_metadata: List[Dict[str, Any]]
    ) -> List[VariableDefinition]:
        """
        Extract variable definitions from equation captions.

        This method searches equation captions for patterns like:
        - "where variables are defined as: ε = emissivity"
        - "Equation 9: Radiation (ε = emissivity)"

        Confidence: 0.70 (implicit definitions from captions)

        Args:
            equation_metadata: List of equation dicts with caption text

        Returns:
            List of VariableDefinition objects from captions

        Example caption:
            "Fourier's law of heat conduction, where:
             k = thermal conductivity (W/m K)
             ε = emissivity (dimensionless)"
        """
        definitions = []

        for eq_meta in equation_metadata:
            caption = eq_meta.get('caption', '')
            if not caption:
                continue

            equation_id = eq_meta.get('equation_id', 'unknown')
            page = eq_meta.get('page', -1)

            # Try all caption patterns
            for pattern_spec in self.patterns.get('equation_captions', []):
                matches = pattern_spec['pattern'].finditer(caption)
                for match in matches:
                    var_def = self._extract_caption_definition(
                        match=match,
                        groups=pattern_spec['groups'],
                        confidence=pattern_spec['confidence'],
                        page=page,
                        equation_id=equation_id,
                        caption=caption
                    )
                    if var_def:
                        definitions.append(var_def)

            # Also look for multi-line where clauses in captions
            # "where:\n k = thermal conductivity\n ε = emissivity"
            if 'where' in caption.lower():
                defs_from_multiline = self._extract_multiline_caption_definitions(
                    caption=caption,
                    page=page,
                    equation_id=equation_id
                )
                definitions.extend(defs_from_multiline)

        logger.info(f"✅ Detected {len(definitions)} variable definitions from equation captions")
        return definitions

    def _extract_caption_definition(
        self,
        match: re.Match,
        groups: Dict[str, int],
        confidence: float,
        page: int,
        equation_id: str,
        caption: str
    ) -> Optional[VariableDefinition]:
        """
        Extract variable definition from caption pattern match.

        Args:
            match: Regex match object
            groups: Group name → index mapping
            confidence: Base confidence score
            page: Page number
            equation_id: Equation identifier
            caption: Full caption text

        Returns:
            VariableDefinition or None
        """
        try:
            symbol = match.group(groups['symbol']).strip()
            definition = match.group(groups['definition']).strip()

            # Extract variable name from definition
            name = self._extract_variable_name(definition)
            if not name:
                name = symbol

            # Extract units if present
            units = self._extract_units_from_text(definition)

            # Build context
            context = {
                'caption_text': caption,
                'equation_id': equation_id,
                'match_position': [match.start(), match.end()]
            }

            return VariableDefinition(
                symbol=symbol,
                name=name,
                definition_text=definition,
                source_type='equation_caption',
                source_location={
                    'page': page,
                    'equation_id': equation_id,
                    'caption_offset': [match.start(), match.end()]
                },
                units=units,
                confidence=0.70,  # Standardized caption confidence
                confidence_factors={
                    'pattern_match': confidence,
                    'caption_source': 0.70
                },
                context=context
            )

        except Exception as e:
            logger.warning(f"Failed to extract caption definition: {e}")
            return None

    def _extract_multiline_caption_definitions(
        self,
        caption: str,
        page: int,
        equation_id: str
    ) -> List[VariableDefinition]:
        """
        Extract multiple definitions from multi-line caption.

        Handles captions like:
        "where:
         k = thermal conductivity (W/m K)
         ε = emissivity (dimensionless)
         T = temperature (K)"

        Args:
            caption: Caption text
            page: Page number
            equation_id: Equation identifier

        Returns:
            List of VariableDefinition objects
        """
        definitions = []

        # Look for "where:" followed by multiple lines
        where_match = re.search(r'(?i)where:\s*', caption)
        if not where_match:
            return definitions

        # Extract text after "where:"
        remaining = caption[where_match.end():]

        # Pattern: "symbol = definition" on each line
        line_pattern = re.compile(
            r'^\s*([a-zA-Zα-ωΑ-Ω_][a-zA-Z0-9α-ωΑ-Ω_]*)\s*=\s*(.+?)(?:\n|$)',
            re.MULTILINE
        )

        for match in line_pattern.finditer(remaining):
            symbol = match.group(1).strip()
            definition = match.group(2).strip()

            # Extract name and units
            name = self._extract_variable_name(definition)
            units = self._extract_units_from_text(definition)

            var_def = VariableDefinition(
                symbol=symbol,
                name=name or symbol,
                definition_text=definition,
                source_type='equation_caption',
                source_location={
                    'page': page,
                    'equation_id': equation_id,
                    'caption_offset': [match.start(), match.end()]
                },
                units=units,
                confidence=0.70,
                confidence_factors={
                    'multiline_caption': 0.70,
                    'equation_association': 0.75
                },
                context={'caption_text': caption, 'equation_id': equation_id}
            )
            definitions.append(var_def)

        return definitions

    def detect_from_table_headers(
        self,
        table_metadata: List[Dict[str, Any]]
    ) -> List[VariableDefinition]:
        """
        Extract variable definitions from table column headers.

        This method searches table headers for patterns like:
        - "Emissivity (ε)"
        - "Thermal Conductivity (k), W/m K"
        - "Temperature (T) [K]"
        - "ε (Emissivity)"

        Confidence: 0.70 (implicit definitions from headers)

        Args:
            table_metadata: List of table dicts with header information

        Returns:
            List of VariableDefinition objects from table headers

        Example headers:
            - "Emissivity (ε)"
            - "Thermal Conductivity (k), W/m K"
            - "Temperature (T) [K]"
        """
        definitions = []

        for table_meta in table_metadata:
            headers = table_meta.get('headers', [])
            if not headers:
                continue

            table_id = table_meta.get('table_id', 'unknown')
            page = table_meta.get('page', -1)

            for col_idx, header in enumerate(headers):
                if not header or not isinstance(header, str):
                    continue

                # Try all table header patterns
                for pattern_spec in self.patterns.get('table_headers', []):
                    match = pattern_spec['pattern'].search(header)
                    if match:
                        var_def = self._extract_table_header_definition(
                            match=match,
                            groups=pattern_spec['groups'],
                            confidence=pattern_spec['confidence'],
                            page=page,
                            table_id=table_id,
                            column_index=col_idx,
                            header_text=header
                        )
                        if var_def:
                            definitions.append(var_def)
                            break  # Use first matching pattern

        logger.info(f"✅ Detected {len(definitions)} variable definitions from table headers")
        return definitions

    def _extract_table_header_definition(
        self,
        match: re.Match,
        groups: Dict[str, int],
        confidence: float,
        page: int,
        table_id: str,
        column_index: int,
        header_text: str
    ) -> Optional[VariableDefinition]:
        """
        Extract variable definition from table header pattern match.

        Args:
            match: Regex match object
            groups: Group name → index mapping
            confidence: Base confidence score
            page: Page number
            table_id: Table identifier
            column_index: Column index in table
            header_text: Full header text

        Returns:
            VariableDefinition or None
        """
        try:
            # Determine symbol and name based on groups
            if 'symbol' in groups and 'name' in groups:
                symbol = match.group(groups['symbol']).strip()
                name = match.group(groups['name']).strip()
            else:
                # Heuristic: shorter one is symbol
                g1 = match.group(1).strip()
                g2 = match.group(2).strip()
                if len(g1) <= 3:
                    symbol, name = g1, g2
                else:
                    symbol, name = g2, g1

            # Extract units from header text
            # Look for units after comma or in brackets
            units = None

            # Pattern 1: "Name (symbol), units"
            units_after_comma = re.search(r',\s*(.+)$', header_text)
            if units_after_comma:
                units = self._parse_units(units_after_comma.group(1).strip())

            # Pattern 2: "Name (symbol) [units]"
            units_in_brackets = re.search(r'\[([^\]]+)\]', header_text)
            if units_in_brackets and not units:
                units = self._parse_units(units_in_brackets.group(1).strip())

            # Build context
            context = {
                'table_id': table_id,
                'column_index': column_index,
                'header_text': header_text
            }

            return VariableDefinition(
                symbol=symbol,
                name=name,
                definition_text=f"{name} from table header",
                source_type='table_header',
                source_location={
                    'page': page,
                    'table_id': table_id,
                    'column_index': column_index
                },
                units=units,
                confidence=confidence,
                confidence_factors={
                    'pattern_match': confidence,
                    'table_header_source': 0.70
                },
                context=context
            )

        except Exception as e:
            logger.warning(f"Failed to extract table header definition: {e}")
            return None

    # ========== Phase 5: Integration & Orchestration ==========

    def detect_all_definitions(
        self,
        document_chunks: List[Dict[str, Any]],
        equation_metadata: Optional[List[Dict[str, Any]]] = None,
        table_metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Orchestrate all detection methods and return complete results.

        This is the main entry point for variable definition detection.

        Steps:
        1. Detect from nomenclature sections (0.98 confidence)
        2. Detect from inline definitions (0.85 confidence)
        3. Detect from equation captions (0.70 confidence)
        4. Detect from table headers (0.70 confidence)
        5. Deduplicate (keep highest confidence)
        6. Register in SemanticRegistry
        7. Validate with Validator
        8. Export to JSON format

        Args:
            document_chunks: List of semantic chunks from document
            equation_metadata: Optional equation metadata with captions
            table_metadata: Optional table metadata with headers

        Returns:
            List of relationship dicts ready for export
        """
        logger.info("🚀 Starting variable definition detection...")

        all_definitions = []

        # Phase 2: Nomenclature sections
        nom_sections = self.detect_nomenclature_sections(document_chunks)
        logger.info(f"Found {len(nom_sections)} nomenclature sections")

        # Convert nomenclature entries to VariableDefinition objects
        for section in nom_sections:
            for entry in section.entries:
                var_def = VariableDefinition(
                    symbol=entry['symbol'],
                    name=entry['name'],
                    definition_text=entry['definition_text'],
                    source_type='nomenclature_section',
                    source_location={
                        'page': entry['source_page'],
                        'chunk_id': entry['source_chunk']
                    },
                    units=entry.get('units'),
                    confidence=entry['confidence'],
                    confidence_factors={'nomenclature_source': entry['confidence']}
                )
                all_definitions.append(var_def)

        # Phase 3: Inline definitions
        inline_defs = self.detect_inline_definitions(document_chunks)
        logger.info(f"Found {len(inline_defs)} inline definitions")
        all_definitions.extend(inline_defs)

        # Phase 4: Equation captions
        caption_defs = []
        if equation_metadata:
            caption_defs = self.detect_from_equation_captions(equation_metadata)
            logger.info(f"Found {len(caption_defs)} caption definitions")
            all_definitions.extend(caption_defs)

        # Phase 4: Table headers
        table_defs = []
        if table_metadata:
            table_defs = self.detect_from_table_headers(table_metadata)
            logger.info(f"Found {len(table_defs)} table header definitions")
            all_definitions.extend(table_defs)

        logger.info(f"Total definitions before deduplication: {len(all_definitions)}")

        # Phase 5: Deduplication
        deduplicated_defs = self._deduplicate_definitions(all_definitions)
        logger.info(f"Total definitions after deduplication: {len(deduplicated_defs)}")

        # Phase 5: Register in SemanticRegistry and build relationships
        relationships = []
        for var_def in deduplicated_defs:
            # Register variable in semantic registry
            canonical_id = self._register_in_semantic_registry(var_def)

            # Build relationship dict
            relationship = self._build_relationship_dict(var_def, canonical_id)

            # Validate relationship if validator available
            if self.validator:
                relationship = self._validate_relationship(relationship)
            else:
                # Add basic validation status
                relationship['validation'] = {
                    'overall_status': 'not_validated',
                    'checks': []
                }

            relationships.append(relationship)

        logger.info(f"✅ Variable definition detection complete: {len(relationships)} relationships")
        return relationships

    def _deduplicate_definitions(
        self,
        definitions: List[VariableDefinition]
    ) -> List[VariableDefinition]:
        """
        Merge duplicate symbols, keeping highest confidence source.

        When the same symbol appears from multiple sources:
        - Keep the definition with highest confidence
        - Merge definition_text from all sources
        - Track all source types

        Example:
            ε from nomenclature (0.98) + ε from inline (0.85)
            → Keep nomenclature source (0.98)
            → Merge both definition texts

        Args:
            definitions: List of all detected definitions

        Returns:
            List of deduplicated definitions
        """
        # Group by symbol
        symbol_groups: Dict[str, List[VariableDefinition]] = {}
        for defn in definitions:
            symbol = defn.symbol
            if symbol not in symbol_groups:
                symbol_groups[symbol] = []
            symbol_groups[symbol].append(defn)

        # Process each group
        deduplicated = []
        for symbol, group in symbol_groups.items():
            if len(group) == 1:
                # No duplicates
                deduplicated.append(group[0])
            else:
                # Merge duplicates
                merged = self._merge_definitions(group)
                deduplicated.append(merged)

        return deduplicated

    def _merge_definitions(
        self,
        definitions: List[VariableDefinition]
    ) -> VariableDefinition:
        """
        Merge multiple definitions of the same symbol.

        Strategy:
        - Use highest confidence definition as base
        - Merge definition texts
        - Combine source types
        - Aggregate confidence factors

        Args:
            definitions: List of definitions for same symbol

        Returns:
            Merged VariableDefinition
        """
        # Sort by confidence (highest first)
        sorted_defs = sorted(definitions, key=lambda d: d.confidence, reverse=True)
        base = sorted_defs[0]

        # Merge definition texts
        merged_text_parts = [base.definition_text]
        for defn in sorted_defs[1:]:
            if defn.definition_text not in base.definition_text:
                merged_text_parts.append(defn.definition_text)

        merged_definition_text = "; ".join(merged_text_parts)

        # Collect all source types
        source_types = [base.source_type] + [d.source_type for d in sorted_defs[1:]]

        # Merge confidence factors
        merged_factors = base.confidence_factors.copy()
        for defn in sorted_defs[1:]:
            for key, value in defn.confidence_factors.items():
                if key not in merged_factors:
                    merged_factors[key] = value

        merged_factors['merged_from'] = source_types

        # Create merged definition
        merged = VariableDefinition(
            symbol=base.symbol,
            name=base.name,
            definition_text=merged_definition_text,
            source_type=base.source_type,  # Primary source
            source_location=base.source_location,
            units=base.units,  # Use highest confidence units
            confidence=base.confidence,  # Keep highest confidence
            confidence_factors=merged_factors,
            aliases=list(set(base.aliases + [d.name for d in sorted_defs[1:]])),
            semantic_tags=base.semantic_tags,
            context=base.context
        )

        logger.debug(f"Merged {len(definitions)} definitions of '{base.symbol}' (confidence: {base.confidence})")
        return merged

    def _register_in_semantic_registry(
        self,
        definition: VariableDefinition
    ) -> str:
        """
        Register variable in SemanticRegistry.

        Calls SemanticRegistry.register_variable() to create canonical ID.

        Args:
            definition: VariableDefinition to register

        Returns:
            Canonical ID (e.g., "var:epsilon")
        """
        try:
            # Build variable dict for registration
            variable_dict = {
                'symbol': definition.symbol,
                'name': definition.name,
                'definition': definition.definition_text,
                'units': definition.units,
                'semantic_tags': definition.semantic_tags,
                'aliases': definition.aliases
            }

            # Register in semantic registry
            canonical_id = self.semantic_registry.register_variable(
                symbol=definition.symbol,
                name=definition.name,
                definition=definition.definition_text,
                units=definition.units,
                semantic_tags=definition.semantic_tags
            )

            logger.debug(f"Registered '{definition.symbol}' as {canonical_id}")
            return canonical_id

        except Exception as e:
            logger.warning(f"Failed to register '{definition.symbol}' in semantic registry: {e}")
            # Fallback: create manual ID
            return f"var:{definition.symbol.lower()}"

    def _build_relationship_dict(
        self,
        definition: VariableDefinition,
        canonical_id: str
    ) -> Dict[str, Any]:
        """
        Build relationship dictionary for export.

        Format follows SEMANTIC_RELATIONSHIP_EXTRACTION_FINAL_PLAN.md Part 4.1

        Args:
            definition: VariableDefinition object
            canonical_id: Canonical ID from SemanticRegistry

        Returns:
            Relationship dict ready for JSON export
        """
        # Generate relationship ID
        # Format: vardef:symbol_nnn
        symbol_clean = definition.symbol.lower().replace(' ', '_')
        relationship_id = f"vardef:{symbol_clean}_{hash(canonical_id) % 1000:03d}"

        # Build variable block
        variable_block = {
            'canonical_id': canonical_id,
            'symbol': definition.symbol,
            'name': definition.name,
            'definition_text': definition.definition_text,
            'source_type': definition.source_type
        }

        # Add units if present
        if definition.units:
            variable_block['units'] = definition.units

        # Build relationship dict
        relationship = {
            'relationship_id': relationship_id,
            'edge_type': 'DEFINES_VARIABLE',
            'source': f"doc:page_{definition.source_location.get('page', 0)}_{definition.source_type}",
            'target': canonical_id,
            'variable': variable_block,
            'confidence': {
                'score': definition.confidence,
                'method': definition.source_type,
                'factors': definition.confidence_factors
            },
            'source_location': definition.source_location,
            'context': definition.context
        }

        return relationship

    def _validate_relationship(
        self,
        relationship: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate relationship using Validator.

        Calls Validator.validate_relationship() and adds validation block.

        Args:
            relationship: Relationship dict

        Returns:
            Relationship dict with validation block added
        """
        try:
            validation_result = self.validator.validate_relationship(relationship)
            relationship['validation'] = validation_result
            return relationship
        except Exception as e:
            logger.warning(f"Validation failed for {relationship['relationship_id']}: {e}")
            # Add error validation status
            relationship['validation'] = {
                'overall_status': 'error',
                'checks': [],
                'error': str(e)
            }
            return relationship

    def export_to_json(
        self,
        relationships: List[Dict[str, Any]],
        output_path: Path
    ) -> None:
        """
        Export relationships to JSON file.

        Format: relationships/variable_definitions.json

        Args:
            relationships: List of relationship dicts
            output_path: Output file path

        Example output:
            [
              {
                "relationship_id": "vardef:epsilon_001",
                "edge_type": "DEFINES_VARIABLE",
                "source": "doc:page_5_nomenclature",
                "target": "var:epsilon",
                "variable": {...},
                "confidence": {...},
                "validation": {...}
              }
            ]
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(relationships, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Exported {len(relationships)} relationships to {output_path}")

        except Exception as e:
            logger.error(f"Failed to export relationships: {e}")
            raise
