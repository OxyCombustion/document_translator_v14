#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Semantic Equation Extractor - Beyond Syntax to Meaning

This agent extracts equations WITH complete semantic context:
- LaTeX syntax (syntactic form)
- Symbol definitions (what each symbol means)
- Units and dimensions (physical quantities)
- Domain classification (thermodynamics, quantum, etc.)
- Physical interpretation (what the equation represents)
- Assumptions and constraints (when it's valid)
- Related equations (context links)

Philosophy: Clear naming and explicit context minimize ambiguity.
Just as good code uses descriptive names, good extraction provides
complete semantic context so AI can UNDERSTAND, not just parse.

Architecture: Modular, cohesive, self-documenting
- Each extraction concern is a separate module
- All semantic context kept together (cohesion)
- Explicit meanings, no cryptic abbreviations
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import re
from dataclasses import dataclass, asdict, field
from enum import Enum

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


# ============================================================================
# DATA STRUCTURES: Explicit, Self-Documenting
# ============================================================================

@dataclass
class SymbolDefinition:
    """
    Complete semantic definition of a mathematical symbol.

    Attributes capture everything needed for AI understanding:
    - What the symbol is called (name)
    - What it means (meaning)
    - How it's measured (units)
    - What kind of quantity (dimensions)
    - How it's used (role in equation)
    - What values are reasonable (typical_range)
    """
    symbol: str  # The actual symbol (e.g., "q", "T", "ρ")
    meaning: str  # What it represents (e.g., "heat transfer rate")
    full_description: Optional[str] = None  # Longer explanation if available
    units: Optional[str] = None  # Physical units (e.g., "W", "kg/m³")
    units_expanded: Optional[str] = None  # Full unit name (e.g., "watts (joules per second)")
    dimensions: Optional[str] = None  # Dimensional analysis (e.g., "[energy]/[time]")
    role: Optional[str] = None  # Role in equation: dependent_variable, parameter, constant
    typical_range: Optional[str] = None  # Expected value range
    constraints: List[str] = field(default_factory=list)  # Physical constraints (e.g., "T > 0 K")
    also_known_as: List[str] = field(default_factory=list)  # Alternative names


@dataclass
class SemanticEquation:
    """
    Complete semantic representation of an equation.

    Follows same principles as clear code:
    - Modular: Separate concerns (syntax, semantics, ontology)
    - Cohesive: All related context together
    - Self-documenting: Explicit field names, comprehensive docstrings
    """
    # Syntactic representation
    equation_number: str
    page: int
    latex: str
    latex_simplified: Optional[str] = None

    # Semantic context
    symbols: Dict[str, SymbolDefinition] = field(default_factory=dict)
    equation_name: Optional[str] = None  # e.g., "Fourier's law", "Newton's law of cooling"
    physical_interpretation: Optional[str] = None  # What the equation means physically

    # Domain classification
    domain: Optional[str] = None  # e.g., "thermodynamics", "quantum_mechanics"
    subdomain: Optional[str] = None  # e.g., "heat_transfer", "conduction"

    # Validity constraints
    assumptions: List[str] = field(default_factory=list)  # When equation is valid
    limitations: List[str] = field(default_factory=list)  # When equation breaks down
    applicable_conditions: Optional[str] = None  # General applicability

    # Contextual relationships
    related_equations: List[Dict[str, str]] = field(default_factory=list)  # Links to other equations
    derived_from: Optional[str] = None  # Parent equation if derived
    special_cases: List[str] = field(default_factory=list)  # Simplified forms

    # Ontology mapping
    ontology: Dict[str, Any] = field(default_factory=dict)  # Links to external knowledge

    # Source context
    surrounding_text: Optional[str] = None  # Raw text around equation
    context_before: Optional[str] = None  # Text before equation
    context_after: Optional[str] = None  # Text after equation (often has "where" clause)

    # Computational properties
    computational_difficulty: Optional[str] = None  # trivial, algebraic, numerical, analytical
    solve_for_variables: List[str] = field(default_factory=list)  # Which vars can be solved for

    # Quality metadata
    semantic_extraction_confidence: float = 0.0  # 0.0-1.0 confidence in semantic extraction
    symbols_fully_defined: bool = False  # All symbols have definitions?
    requires_human_validation: bool = False  # Needs human review?


# ============================================================================
# CONTEXT WINDOW EXTRACTOR: Extract Surrounding Text
# ============================================================================

class ContextWindowExtractor:
    """
    Extracts text surrounding an equation for semantic analysis.

    Principle: Symbol definitions usually appear near equations.
    Strategy: Page-level text extraction (bbox-independent approach).

    Two methods:
    1. extract_context_page_level() - NEW: Works when bbox data missing/invalid
    2. extract_context() - LEGACY: Works when bbox coordinates valid
    """

    def __init__(self,
                 window_paragraphs: int = 3,
                 window_lines: int = 10,
                 context_window_chars: int = 800):
        """
        Initialize context extractor.

        Args:
            window_paragraphs: Number of paragraphs before/after equation (bbox method)
            window_lines: Number of lines before/after equation (bbox fallback)
            context_window_chars: Characters to extract around equation mention (page-level method)
        """
        self.window_paragraphs = window_paragraphs
        self.window_lines = window_lines
        self.context_window_chars = context_window_chars

    def extract_context_page_level(self,
                                   equation_number: str,
                                   page) -> Dict[str, str]:
        """
        Extract context using page-level text search (bbox-independent).

        Method: Search for equation number mentions in page text, extract
        surrounding context. Works even when bbox coordinates missing.

        Args:
            equation_number: Equation number (e.g., "1", "79a")
            page: PyMuPDF page object

        Returns:
            Dictionary with 'before', 'after', 'full' context
        """
        # Get all page text
        page_text = page.get_text()

        # Build patterns to find equation mentions
        # Matches: "(1)", "Equation (1)", "Eq. (1)", "equation 1"
        patterns = [
            rf'\({equation_number}\)',  # (1)
            rf'Equation\s*\(?{equation_number}\)?',  # Equation (1) or Equation 1
            rf'Eq\.\s*\(?{equation_number}\)?',  # Eq. (1) or Eq. 1
            rf'equation\s*\(?{equation_number}\)?',  # equation (1) or equation 1
        ]

        # Find all matches
        matches = []
        for pattern in patterns:
            for match in re.finditer(pattern, page_text, re.IGNORECASE):
                matches.append(match.start())

        if not matches:
            # No equation mentions found - return page text segments
            # This handles cases where equation exists but isn't explicitly referenced
            return {
                'before': page_text[:len(page_text)//2],
                'after': page_text[len(page_text)//2:],
                'full': page_text
            }

        # Extract context around each match (±window_chars)
        contexts_before = []
        contexts_after = []

        for match_pos in matches:
            # Extract before match
            start_before = max(0, match_pos - self.context_window_chars)
            context_before = page_text[start_before:match_pos]
            contexts_before.append(context_before)

            # Extract after match (this usually has "where X is Y" clauses)
            end_after = min(len(page_text), match_pos + self.context_window_chars)
            context_after = page_text[match_pos:end_after]
            contexts_after.append(context_after)

        # Combine all contexts (remove duplicates by converting to set then back)
        combined_before = ' '.join(contexts_before)
        combined_after = ' '.join(contexts_after)
        full_context = combined_before + ' [EQUATION] ' + combined_after

        return {
            'before': combined_before,
            'after': combined_after,
            'full': full_context
        }

    def extract_context(self,
                       equation_bbox: Dict[str, float],
                       page,
                       full_text: str) -> Dict[str, str]:
        """
        Extract text surrounding equation using bbox coordinates (LEGACY method).

        NOTE: This method requires valid bbox coordinates. If bbox is (0,0,0,0),
        use extract_context_page_level() instead.

        Args:
            equation_bbox: Bounding box of equation {x0, y0, x1, y1}
            page: PyMuPDF page object
            full_text: Full text of page

        Returns:
            Dictionary with 'before', 'after', 'full' context
        """
        import fitz

        # Get equation vertical position
        eq_y0 = equation_bbox['y0']
        eq_y1 = equation_bbox['y1']
        eq_center_y = (eq_y0 + eq_y1) / 2

        # Extract all text blocks with positions
        blocks = page.get_text("blocks")

        # Separate text before and after equation
        text_before_blocks = []
        text_after_blocks = []

        for block in blocks:
            if len(block) < 5:
                continue

            block_x0, block_y0, block_x1, block_y1, text, block_type, flags = block[:7]

            # Skip non-text blocks
            if block_type != 0:
                continue

            # Classify as before or after equation
            block_center_y = (block_y0 + block_y1) / 2

            if block_center_y < eq_y0:
                text_before_blocks.append((block_y0, text))
            elif block_center_y > eq_y1:
                text_after_blocks.append((block_y0, text))

        # Sort by position
        text_before_blocks.sort(key=lambda x: x[0], reverse=True)  # Closest to equation first
        text_after_blocks.sort(key=lambda x: x[0])  # Closest to equation first

        # Take window of text
        context_before = ' '.join([text for _, text in text_before_blocks[:self.window_paragraphs]])
        context_after = ' '.join([text for _, text in text_after_blocks[:self.window_paragraphs]])

        return {
            'before': context_before,
            'after': context_after,
            'full': context_before + ' [EQUATION] ' + context_after
        }


# ============================================================================
# SYMBOL DEFINITION PARSER: Parse "where X is Y" Patterns
# ============================================================================

class SymbolDefinitionParser:
    """
    Parses symbol definitions from prose text.

    Patterns detected:
    - "where q is the heat flux"
    - "q = heat flux (W/m²)"
    - "q represents the rate of heat transfer"
    - "The variable q denotes..."

    Philosophy: Explicit pattern matching (not ML) for transparency.
    Each pattern is documented and testable.
    """

    def __init__(self):
        """Initialize parser with definition patterns."""
        # Pattern 1: "where X is Y" or "where X is the Y"
        # Non-greedy: stops at conjunctions, commas, periods
        self.where_pattern = re.compile(
            r'where\s+([A-Za-z_₀-₉⁰-⁹]+)\s+(?:is|=|represents?|denotes?)\s+(?:the\s+)?([^,\.\n]+?)(?=\s+and\s|\s+or\s|,|\.|;|$)',
            re.IGNORECASE
        )

        # Pattern 2: "X is Y" or "X is the Y" (mid-sentence, after commas)
        # Handles: "A is the surface area, Ts is the surface temperature"
        # Non-greedy: stops at conjunctions (and, or), commas, periods
        self.simple_is_pattern = re.compile(
            r'\b([A-Za-z_₀-₉⁰-⁹]+)\s+is\s+(?:the\s+)?([^,\.\n]+?)(?=\s+and\s|\s+or\s|,|\.|;|$)',
            re.IGNORECASE
        )

        # Pattern 3: "X = Y (units)" or "X = Y, units"
        self.definition_with_units_pattern = re.compile(
            r'([A-Za-z_₀-₉⁰-⁹]+)\s*[=:]\s*([^(,\n]+)\s*[,(]\s*([^),\n]+)\s*[),]?',
            re.MULTILINE
        )

        # Pattern 4: List format "X is Y, Z is W"
        self.list_pattern = re.compile(
            r'([A-Za-z_₀-₉⁰-⁹]+)\s+(?:is|=)\s+([^,\n]+)(?:,|;|\n)',
            re.IGNORECASE
        )

        # Pattern 5: "X represents Y" or "X denotes Y"
        # Non-greedy: stops at conjunctions, commas, periods
        self.represents_pattern = re.compile(
            r'\b([A-Za-z_₀-₉⁰-⁹]+)\s+(?:represents?|denotes?)\s+(?:the\s+)?([^,\.\n]+?)(?=\s+and\s|\s+or\s|,|\.|;|$)',
            re.IGNORECASE
        )

        # Pattern 6: Appositive phrases "The Y, X," (definition before symbol)
        # Handles: "The thermal conductivity, k, is used"
        #          "the heat flow, qc, represents"
        #          "an area, A, and"
        # More restrictive: captures 1-6 words between article and comma
        self.appositive_pattern = re.compile(
            r'(?:the|an?)\s+((?:\w+\s+){0,5}\w+),\s*([A-Za-z_₀-₉⁰-⁹/]+)\s*,',
            re.IGNORECASE
        )

    def parse_definitions(self,
                         context_text: str,
                         latex_symbols: List[str]) -> Dict[str, SymbolDefinition]:
        """
        Parse symbol definitions from context text.

        Args:
            context_text: Text surrounding equation
            latex_symbols: List of symbols found in LaTeX

        Returns:
            Dictionary mapping symbol -> SymbolDefinition
        """
        definitions = {}

        # Try each pattern in order of specificity
        definitions.update(self._parse_where_clauses(context_text, latex_symbols))
        definitions.update(self._parse_simple_is_statements(context_text, latex_symbols))
        definitions.update(self._parse_represents_statements(context_text, latex_symbols))
        definitions.update(self._parse_appositive_phrases(context_text, latex_symbols))
        definitions.update(self._parse_definition_lists(context_text, latex_symbols))

        return definitions

    def _parse_where_clauses(self,
                            text: str,
                            latex_symbols: List[str]) -> Dict[str, SymbolDefinition]:
        """Parse "where X is Y" patterns."""
        definitions = {}

        # Find all "where" clauses
        matches = self.where_pattern.finditer(text)

        for match in matches:
            symbol = match.group(1).strip()
            meaning = match.group(2).strip()

            # Normalize symbol (handle Unicode subscripts)
            symbol_normalized = self._normalize_symbol(symbol)

            # Check if this symbol is in our LaTeX
            if symbol_normalized in latex_symbols or symbol in latex_symbols:
                definitions[symbol_normalized] = SymbolDefinition(
                    symbol=symbol_normalized,
                    meaning=meaning
                )

        return definitions

    def _parse_simple_is_statements(self,
                                     text: str,
                                     latex_symbols: List[str]) -> Dict[str, SymbolDefinition]:
        """Parse simple "X is Y" patterns (mid-sentence)."""
        definitions = {}

        matches = self.simple_is_pattern.finditer(text)

        for match in matches:
            symbol = match.group(1).strip()
            meaning = match.group(2).strip()

            # Normalize symbol
            symbol_normalized = self._normalize_symbol(symbol)

            # Filter out common words that aren't symbols
            if symbol.lower() in ['this', 'that', 'it', 'which', 'what', 'there', 'here']:
                continue

            # Check if this symbol is in our LaTeX
            if symbol_normalized in latex_symbols or symbol in latex_symbols:
                definitions[symbol_normalized] = SymbolDefinition(
                    symbol=symbol_normalized,
                    meaning=meaning
                )

        return definitions

    def _parse_represents_statements(self,
                                     text: str,
                                     latex_symbols: List[str]) -> Dict[str, SymbolDefinition]:
        """Parse "X represents Y" or "X denotes Y" patterns."""
        definitions = {}

        matches = self.represents_pattern.finditer(text)

        for match in matches:
            symbol = match.group(1).strip()
            meaning = match.group(2).strip()

            # Normalize
            symbol_normalized = self._normalize_symbol(symbol)

            # Filter out common words
            if symbol.lower() in ['this', 'that', 'it', 'which', 'what']:
                continue

            if symbol_normalized in latex_symbols or symbol in latex_symbols:
                definitions[symbol_normalized] = SymbolDefinition(
                    symbol=symbol_normalized,
                    meaning=meaning
                )

        return definitions

    def _parse_appositive_phrases(self,
                                   text: str,
                                   latex_symbols: List[str]) -> Dict[str, SymbolDefinition]:
        """
        Parse appositive phrases where definition comes BEFORE symbol.

        Examples:
        - "The thermal conductivity, k, is used" → k = "thermal conductivity"
        - "the heat flow, qc, represents" → qc = "heat flow"
        - "an area, A, and" → A = "area"
        """
        definitions = {}

        matches = self.appositive_pattern.finditer(text)

        for match in matches:
            meaning = match.group(1).strip()
            symbol = match.group(2).strip()

            # Normalize symbol
            symbol_normalized = self._normalize_symbol(symbol)

            # Check if this symbol is in our LaTeX
            if symbol_normalized in latex_symbols or symbol in latex_symbols:
                definitions[symbol_normalized] = SymbolDefinition(
                    symbol=symbol_normalized,
                    meaning=meaning
                )

        return definitions

    def _parse_definition_lists(self,
                                text: str,
                                latex_symbols: List[str]) -> Dict[str, SymbolDefinition]:
        """Parse definition lists with units."""
        definitions = {}

        matches = self.definition_with_units_pattern.finditer(text)

        for match in matches:
            symbol = match.group(1).strip()
            meaning = match.group(2).strip()
            units = match.group(3).strip()

            # Normalize
            symbol_normalized = self._normalize_symbol(symbol)

            if symbol_normalized in latex_symbols or symbol in latex_symbols:
                definitions[symbol_normalized] = SymbolDefinition(
                    symbol=symbol_normalized,
                    meaning=meaning,
                    units=units
                )

        return definitions

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol names (handle subscripts, special chars).

        Examples:
        - "T_s" -> "T_s"
        - "Ts" -> "T_s" (if context suggests subscript)
        - "ΔT" -> "DeltaT"
        """
        # Basic normalization for now
        # TODO: Handle Unicode math symbols, subscripts, superscripts
        return symbol


# ============================================================================
# UNIT EXTRACTOR: Extract Physical Units and Dimensions
# ============================================================================

class UnitExtractor:
    """
    Extracts physical units and dimensional analysis.

    Handles SI units, compound units, dimensional analysis.
    Examples: "W", "kg/m³", "J/(kg·K)", "[energy]/[time]"
    """

    def __init__(self):
        """Initialize with SI unit patterns."""
        # Common SI base units
        self.base_units = {
            'm': 'meter',
            'kg': 'kilogram',
            's': 'second',
            'K': 'kelvin',
            'A': 'ampere',
            'mol': 'mole',
            'cd': 'candela'
        }

        # Common derived units
        self.derived_units = {
            'W': 'watt',
            'J': 'joule',
            'N': 'newton',
            'Pa': 'pascal',
            'V': 'volt',
            'Ω': 'ohm',
            'F': 'farad',
            'H': 'henry'
        }

        # Dimensional mappings
        self.dimension_map = {
            'W': '[energy]/[time]',
            'J': '[energy]',
            'N': '[mass]·[length]/[time]²',
            'Pa': '[mass]/([length]·[time]²)',
            'kg': '[mass]',
            'm': '[length]',
            's': '[time]',
            'K': '[temperature]'
        }

    def extract_units(self, text: str) -> Optional[str]:
        """
        Extract units from text.

        Args:
            text: Text potentially containing units

        Returns:
            Units string if found, None otherwise
        """
        # Pattern: units in parentheses (W), (kg/m³), etc.
        paren_pattern = r'\(([A-Za-zΩ°²³]+(?:[/·]?[A-Za-zΩ°²³]+)*)\)'
        match = re.search(paren_pattern, text)
        if match:
            return match.group(1)

        # Pattern: "in units" or "units:"
        units_pattern = r'(?:in\s+|units?:\s*)([A-Za-zΩ°²³]+(?:[/·]?[A-Za-zΩ°²³]+)*)'
        match = re.search(units_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def infer_dimensions(self, units: str) -> Optional[str]:
        """
        Infer dimensional analysis from units.

        Args:
            units: Unit string (e.g., "W", "kg/m³")

        Returns:
            Dimensional analysis string (e.g., "[energy]/[time]")
        """
        if units in self.dimension_map:
            return self.dimension_map[units]

        # TODO: Parse compound units and compute dimensions
        # For now, return None for compound units
        return None


# ============================================================================
# DOMAIN CLASSIFIER: Identify Document Domain
# ============================================================================

class DomainClassifier:
    """
    Classifies document domain from context and symbols.

    Domains: thermodynamics, fluid_dynamics, quantum_mechanics,
             electromagnetism, mechanics, economics, etc.
    """

    def __init__(self):
        """Initialize with domain keywords."""
        self.domain_keywords = {
            'thermodynamics': [
                'heat', 'temperature', 'thermal', 'conduction', 'convection',
                'radiation', 'entropy', 'enthalpy', 'carnot', 'heat transfer'
            ],
            'fluid_dynamics': [
                'flow', 'velocity', 'pressure', 'reynolds', 'turbulent',
                'laminar', 'bernoulli', 'navier-stokes', 'viscosity'
            ],
            'quantum_mechanics': [
                'wave function', 'hamiltonian', 'eigenvalue', 'quantum',
                'schrodinger', 'heisenberg', 'planck', 'orbital', 'spin'
            ],
            'electromagnetism': [
                'electric', 'magnetic', 'maxwell', 'coulomb', 'gauss',
                'ampere', 'faraday', 'voltage', 'current', 'field'
            ],
            'mechanics': [
                'force', 'acceleration', 'momentum', 'newton', 'kinetic',
                'potential', 'energy', 'work', 'power', 'torque'
            ],
            'economics': [
                'price', 'demand', 'supply', 'utility', 'cost', 'revenue',
                'profit', 'elasticity', 'equilibrium', 'market'
            ]
        }

    def classify_domain(self,
                       context_text: str,
                       symbols: Dict[str, SymbolDefinition]) -> Tuple[Optional[str], float]:
        """
        Classify domain from context and symbols.

        Args:
            context_text: Surrounding text
            symbols: Extracted symbol definitions

        Returns:
            (domain_name, confidence) tuple
        """
        # Score each domain by keyword matches
        domain_scores = {}

        text_lower = context_text.lower()

        for domain, keywords in self.domain_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                domain_scores[domain] = score

        # Also check symbol meanings
        for symbol_def in symbols.values():
            meaning_lower = symbol_def.meaning.lower()
            for domain, keywords in self.domain_keywords.items():
                for kw in keywords:
                    if kw in meaning_lower:
                        domain_scores[domain] = domain_scores.get(domain, 0) + 2

        if not domain_scores:
            return None, 0.0

        # Return highest scoring domain
        best_domain = max(domain_scores, key=domain_scores.get)
        total_score = sum(domain_scores.values())
        confidence = domain_scores[best_domain] / total_score

        return best_domain, confidence


# ============================================================================
# SEMANTIC EQUATION EXTRACTOR: Main Orchestrator
# ============================================================================

class SemanticEquationExtractor:
    """
    Main semantic extraction orchestrator.

    Coordinates all extraction modules to produce complete
    semantic representation of equations.

    Architecture:
    - Modular: Each concern is separate module
    - Cohesive: All semantic context kept together
    - Self-documenting: Clear method names, comprehensive docs
    """

    def __init__(self,
                 equations_file: Path,
                 pdf_path: Path,
                 output_dir: Path):
        """
        Initialize semantic extractor.

        Args:
            equations_file: JSON file with LaTeX equations
            pdf_path: Original PDF for context extraction
            output_dir: Where to save semantic extractions
        """
        self.equations_file = equations_file
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize extraction modules
        self.context_extractor = ContextWindowExtractor()
        self.symbol_parser = SymbolDefinitionParser()
        self.unit_extractor = UnitExtractor()
        self.domain_classifier = DomainClassifier()

        # Load equations
        with open(equations_file, 'r', encoding='utf-8') as f:
            self.equations = json.load(f)

    def extract_all_equations(self) -> List[SemanticEquation]:
        """
        Extract semantic context for all equations.

        Returns:
            List of SemanticEquation objects with full context
        """
        import fitz

        doc = fitz.open(self.pdf_path)
        semantic_equations = []

        print(f"\n{'='*80}")
        print(f"SEMANTIC EQUATION EXTRACTION")
        print(f"{'='*80}\n")
        print(f"Extracting from: {self.pdf_path}")
        print(f"Total equations: {len(self.equations)}\n")

        for i, eq in enumerate(self.equations, 1):
            print(f"Processing equation {i}/{len(self.equations)}: Equation {eq.get('equation_number', '?')}")

            semantic_eq = self.extract_semantic_equation(eq, doc)
            semantic_equations.append(semantic_eq)

            # Print summary
            symbols_defined = len(semantic_eq.symbols)
            print(f"  ✓ {symbols_defined} symbols defined")
            if semantic_eq.domain:
                print(f"  ✓ Domain: {semantic_eq.domain}")

        doc.close()

        return semantic_equations

    def extract_semantic_equation(self,
                                  equation: Dict,
                                  doc) -> SemanticEquation:
        """
        Extract complete semantic context for one equation.

        Args:
            equation: Basic equation data (latex, page, bbox)
            doc: PyMuPDF document object

        Returns:
            SemanticEquation with full semantic context
        """
        # Get page
        page_num = equation.get('page', 1)
        page = doc[page_num - 1]

        # Extract LaTeX symbols
        latex = equation.get('latex', '')
        latex_symbols = self._extract_symbols_from_latex(latex)

        # Determine extraction method based on bbox validity
        bbox = {
            'x0': equation.get('bbox_x0', 0),
            'y0': equation.get('bbox_y0', 0),
            'x1': equation.get('bbox_x1', 0),
            'y1': equation.get('bbox_y1', 0)
        }

        # Check if bbox is valid (not all zeros)
        bbox_valid = not (bbox['x0'] == 0 and bbox['y0'] == 0 and
                         bbox['x1'] == 0 and bbox['y1'] == 0)

        if bbox_valid:
            # Use spatial bbox-based extraction
            full_page_text = page.get_text()
            context = self.context_extractor.extract_context(bbox, page, full_page_text)
        else:
            # Use page-level text search (bbox-independent)
            equation_number = equation.get('equation_number', 'unknown')
            context = self.context_extractor.extract_context_page_level(
                equation_number,
                page
            )

        # Parse symbol definitions from context
        # Try both before and after context - definitions can appear in either location
        symbols_after = self.symbol_parser.parse_definitions(
            context['after'],  # Definitions usually after equation ("where X is...")
            latex_symbols
        )
        symbols_before = self.symbol_parser.parse_definitions(
            context['before'],  # Sometimes definitions appear before
            latex_symbols
        )

        # Merge symbol definitions (after takes precedence)
        symbols = {**symbols_before, **symbols_after}

        # Extract units for each symbol
        for symbol_name, symbol_def in symbols.items():
            if not symbol_def.units:
                # Try to extract units from the meaning text
                units = self.unit_extractor.extract_units(symbol_def.meaning)
                if units:
                    symbol_def.units = units
                    symbol_def.dimensions = self.unit_extractor.infer_dimensions(units)

        # Classify domain
        domain, confidence = self.domain_classifier.classify_domain(
            context['full'],
            symbols
        )

        # Create semantic equation
        semantic_eq = SemanticEquation(
            equation_number=equation.get('equation_number', 'unknown'),
            page=page_num,
            latex=latex,
            symbols=symbols,
            domain=domain,
            surrounding_text=context['full'],
            context_before=context['before'],
            context_after=context['after'],
            semantic_extraction_confidence=confidence,
            symbols_fully_defined=(len(symbols) == len(latex_symbols)) if latex_symbols else False
        )

        return semantic_eq

    def _extract_symbols_from_latex(self, latex: str) -> List[str]:
        """
        Extract symbol names from LaTeX string.

        Handles:
        - Subscripted variables: T_{s} → Ts, T_s → Ts
        - Superscripted variables: T^{2} → T2, T^2 → T2
        - Greek letters: \\alpha → alpha
        - Single letters: A, h, k

        Args:
            latex: LaTeX equation string

        Returns:
            List of symbol names (normalized)
        """
        symbols = set()

        # Pattern 1: Subscripted variables with braces: X_{abc} or X_{a b c}
        subscript_braces_pattern = r'([a-zA-Z]+)_{([a-zA-Z0-9 ]+)}'
        for match in re.finditer(subscript_braces_pattern, latex):
            base = match.group(1)
            subscript = match.group(2).strip().replace(' ', '')
            symbol = base + subscript  # e.g., T_{s} → Ts, q_{c v} → qcv
            symbols.add(symbol)
            symbols.add(base)  # Also add base symbol (T, q)

        # Pattern 2: Subscripted variables without braces: X_a
        subscript_simple_pattern = r'([a-zA-Z]+)_([a-zA-Z0-9])'
        for match in re.finditer(subscript_simple_pattern, latex):
            base = match.group(1)
            subscript = match.group(2)
            symbol = base + subscript  # e.g., T_s → Ts
            symbols.add(symbol)
            symbols.add(base)

        # Pattern 3: Superscripted variables: X^{2}, X^2
        superscript_pattern = r'([a-zA-Z]+)\^{?([a-zA-Z0-9]+)}?'
        for match in re.finditer(superscript_pattern, latex):
            base = match.group(1)
            # Don't add superscripts to symbol list (T^2 is still just T)
            symbols.add(base)

        # Pattern 4: Greek letters: \alpha, \beta, etc.
        greek_pattern = r'\\(alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega|Delta|Gamma|Theta|Lambda|Xi|Pi|Sigma|Phi|Psi|Omega)'
        for match in re.finditer(greek_pattern, latex):
            symbols.add(match.group(1))

        # Pattern 5: Single letters (a-z, A-Z) not already captured
        # Only match if NOT followed by subscript or superscript
        single_letter_pattern = r'\b([a-zA-Z])(?![_^])\b'
        for match in re.finditer(single_letter_pattern, latex):
            symbols.add(match.group(1))

        return list(symbols)

    def save_semantic_extractions(self,
                                 semantic_equations: List[SemanticEquation]):
        """
        Save semantic extractions to JSON.

        Args:
            semantic_equations: List of semantic equations
        """
        # Convert to dict for JSON serialization
        equations_dict = [asdict(eq) for eq in semantic_equations]

        output_file = self.output_dir / 'equations_semantic.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(equations_dict, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Semantic extractions saved: {output_file}")

        # Generate human-readable report
        self._generate_semantic_report(semantic_equations)

    def _generate_semantic_report(self,
                                  semantic_equations: List[SemanticEquation]):
        """Generate human-readable semantic extraction report."""
        report_file = self.output_dir / 'semantic_extraction_report.md'

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Semantic Equation Extraction Report\n\n")
            f.write(f"**Document**: {self.pdf_path.name}\n")
            f.write(f"**Total Equations**: {len(semantic_equations)}\n\n")

            # Statistics
            total_symbols = sum(len(eq.symbols) for eq in semantic_equations)
            equations_with_domain = sum(1 for eq in semantic_equations if eq.domain)

            f.write("## Statistics\n\n")
            f.write(f"- Total symbols defined: {total_symbols}\n")
            f.write(f"- Equations with domain classification: {equations_with_domain}/{len(semantic_equations)}\n")
            f.write(f"- Average symbols per equation: {total_symbols/len(semantic_equations):.1f}\n\n")

            # Domain distribution
            domains = {}
            for eq in semantic_equations:
                if eq.domain:
                    domains[eq.domain] = domains.get(eq.domain, 0) + 1

            f.write("## Domain Distribution\n\n")
            for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True):
                f.write(f"- {domain}: {count} equations\n")
            f.write("\n")

            # Sample equations
            f.write("## Sample Semantic Extractions\n\n")
            for eq in semantic_equations[:5]:
                f.write(f"### Equation {eq.equation_number} (Page {eq.page})\n\n")
                f.write(f"**LaTeX**: `{eq.latex}`\n\n")

                if eq.domain:
                    f.write(f"**Domain**: {eq.domain}\n\n")

                if eq.symbols:
                    f.write("**Symbols**:\n")
                    for symbol, defn in eq.symbols.items():
                        f.write(f"- **{symbol}**: {defn.meaning}")
                        if defn.units:
                            f.write(f" ({defn.units})")
                        f.write("\n")
                    f.write("\n")

                f.write("---\n\n")

        print(f"✅ Semantic report saved: {report_file}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution for semantic extraction."""
    print("="*80)
    print("SEMANTIC EQUATION EXTRACTOR")
    print("Extracting Meaning, Not Just Syntax")
    print("="*80)

    # Paths
    base_dir = Path(__file__).parent.parent.parent
    equations_file = base_dir / 'extractions' / 'doclayout_latex' / 'equations_latex.json'
    pdf_path = base_dir / 'tests' / 'test_data' / 'Ch-04_Heat_Transfer.pdf'
    output_dir = base_dir / 'results' / 'semantic_extraction'

    if not equations_file.exists():
        print(f"❌ Equations file not found: {equations_file}")
        return

    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return

    # Extract semantic context
    extractor = SemanticEquationExtractor(
        equations_file=equations_file,
        pdf_path=pdf_path,
        output_dir=output_dir
    )

    semantic_equations = extractor.extract_all_equations()
    extractor.save_semantic_extractions(semantic_equations)

    print("\n" + "="*80)
    print("SEMANTIC EXTRACTION COMPLETE")
    print("="*80)
    print(f"\n📊 Summary:")
    print(f"   - Equations processed: {len(semantic_equations)}")
    print(f"   - Symbols defined: {sum(len(eq.symbols) for eq in semantic_equations)}")
    print(f"   - Domain classified: {sum(1 for eq in semantic_equations if eq.domain)}")
    print(f"\n✅ Ready for AI understanding with full semantic context")


if __name__ == "__main__":
    main()
