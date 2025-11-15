#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Equation Variable Extractor

Extracts variables from equation LaTeX/text and classifies them as
input, output, or parameter variables.

Author: V12 Development Team
Created: 2025-11-03
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
import re
from dataclasses import dataclass
import yaml

# Set UTF-8 encoding for Windows console
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

from src.detectors.data_structures import VariableRole
from src.core.semantic_registry import SemanticRegistry


@dataclass
class EquationVariable:
    """Extracted variable from equation"""
    symbol: str
    role: VariableRole
    canonical_id: Optional[str] = None
    appears_left_of_equals: bool = False
    has_derivative: bool = False
    in_function_argument: bool = False
    is_greek_letter: bool = False
    subscripts: List[str] = None
    superscripts: List[str] = None

    def __post_init__(self):
        if self.subscripts is None:
            self.subscripts = []
        if self.superscripts is None:
            self.superscripts = []


class EquationVariableExtractor:
    """
    Extract and classify variables from equation LaTeX/text.

    Responsibilities:
    - Parse LaTeX to extract variable symbols
    - Classify variables by role (input/output/parameter)
    - Resolve symbols to canonical IDs via SemanticRegistry
    - Handle subscripts, superscripts, derivatives
    """

    def __init__(
        self,
        config_path: Path,
        semantic_registry: SemanticRegistry
    ):
        """
        Initialize equation variable extractor.

        Args:
            config_path: Path to data_dependency_config.yaml
            semantic_registry: SemanticRegistry instance for symbol resolution
        """
        self.config = self._load_config(config_path)
        self.semantic_registry = semantic_registry
        self.greek_letters = self._build_greek_letter_set()

    def _load_config(self, config_path: Path) -> Dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _build_greek_letter_set(self) -> Set[str]:
        """Build set of Greek letters (both Unicode and LaTeX)"""
        # Greek alphabet ranges
        greek_lower = set('αβγδεζηθικλμνξοπρστυφχψω')
        greek_upper = set('ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ')

        # LaTeX Greek letter commands
        latex_greek = {
            'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'varepsilon',
            'zeta', 'eta', 'theta', 'vartheta', 'iota', 'kappa',
            'lambda', 'mu', 'nu', 'xi', 'omicron', 'pi', 'varpi',
            'rho', 'varrho', 'sigma', 'varsigma', 'tau', 'upsilon',
            'phi', 'varphi', 'chi', 'psi', 'omega',
            # Uppercase
            'Gamma', 'Delta', 'Theta', 'Lambda', 'Xi', 'Pi',
            'Sigma', 'Upsilon', 'Phi', 'Psi', 'Omega'
        }

        return greek_lower | greek_upper | latex_greek

    def extract_from_equation(
        self,
        equation_text: str,
        equation_latex: Optional[str] = None,
        equation_id: Optional[str] = None
    ) -> List[EquationVariable]:
        """
        Extract variables from equation text/LaTeX.

        Args:
            equation_text: Plain text representation of equation
            equation_latex: LaTeX representation (if available)
            equation_id: Equation ID for context (e.g., "eq:9")

        Returns:
            List of EquationVariable objects
        """
        # Use LaTeX if available, otherwise fall back to text
        source = equation_latex if equation_latex else equation_text

        # Extract variable symbols
        symbols = self._extract_symbols(source)

        # Analyze equation structure
        equation_structure = self._analyze_equation_structure(source)

        # Classify each variable
        variables = []
        for symbol_info in symbols:
            role = self._classify_variable_role(
                symbol_info,
                equation_structure,
                equation_id
            )

            # Try to resolve to canonical ID
            canonical_id = None
            if self.semantic_registry:
                context = {
                    'equation_id': equation_id,
                    'equation_text': equation_text
                }
                canonical_id = self.semantic_registry.resolve_symbol(
                    symbol_info['base_symbol'],
                    context
                )

            var = EquationVariable(
                symbol=symbol_info['full_symbol'],
                role=role,
                canonical_id=canonical_id,
                appears_left_of_equals=symbol_info.get('left_of_equals', False),
                has_derivative=symbol_info.get('has_derivative', False),
                in_function_argument=symbol_info.get('in_function', False),
                is_greek_letter=self._is_greek_letter(symbol_info['base_symbol']),
                subscripts=symbol_info.get('subscripts', []),
                superscripts=symbol_info.get('superscripts', [])
            )
            variables.append(var)

        return variables

    def _extract_symbols(self, equation_str: str) -> List[Dict]:
        """
        Extract variable symbols from equation string.

        Returns:
            List of dicts with keys: full_symbol, base_symbol, subscripts, superscripts
        """
        symbols = []

        # Comprehensive pattern for variables:
        # - Single Latin/Greek letter: a-z, A-Z, α-ω, Α-Ω
        # - With optional subscript: _{text} or _text
        # - With optional superscript: ^{num} or ^num
        comprehensive_pattern = r'([a-zA-Zα-ωΑ-Ω])(_\{?[a-zA-Z0-9]+\}?)?(\^\{?[0-9]+\}?)?'

        for match in re.finditer(comprehensive_pattern, equation_str):
            symbol_info = self._parse_comprehensive_match(match, equation_str)
            if symbol_info:
                symbols.append(symbol_info)

        # Remove duplicates (same full_symbol)
        unique_symbols = {}
        for sym in symbols:
            full = sym['full_symbol']
            if full not in unique_symbols:
                unique_symbols[full] = sym

        return list(unique_symbols.values())

    def _parse_comprehensive_match(self, match: re.Match, equation_str: str) -> Optional[Dict]:
        """
        Parse comprehensive regex match to extract symbol components.

        Args:
            match: Regex match object
            equation_str: Full equation string for context

        Returns:
            Dict with symbol information or None if invalid
        """
        # Extract groups
        base_symbol = match.group(1)  # Main letter
        subscript_part = match.group(2) if len(match.groups()) > 1 else None
        superscript_part = match.group(3) if len(match.groups()) > 2 else None

        # Build full symbol
        full_symbol = base_symbol
        if subscript_part:
            full_symbol += subscript_part
        if superscript_part:
            full_symbol += superscript_part

        # Extract subscripts (remove _ and {})
        subscripts = []
        if subscript_part:
            sub_clean = subscript_part.strip('_{}')
            if sub_clean:
                subscripts.append(sub_clean)

        # Extract superscripts (remove ^ and {})
        superscripts = []
        if superscript_part:
            sup_clean = superscript_part.strip('^{}')
            if sup_clean:
                superscripts.append(sup_clean)

        # Check if left of equals sign
        left_of_equals = False
        equals_pos = equation_str.find('=')
        if equals_pos >= 0:
            match_pos = match.start()
            left_of_equals = match_pos < equals_pos

        # Check for derivative notation
        has_derivative = self._check_derivative_notation(full_symbol, equation_str, match.start())

        # Check if in function argument
        in_function = self._check_function_argument(equation_str, match.start())

        return {
            'full_symbol': full_symbol,
            'base_symbol': base_symbol,
            'subscripts': subscripts,
            'superscripts': superscripts,
            'left_of_equals': left_of_equals,
            'has_derivative': has_derivative,
            'in_function': in_function
        }

    def _parse_match(self, match: re.Match, equation_str: str) -> Optional[Dict]:
        """
        Parse regex match to extract symbol components.

        Args:
            match: Regex match object
            equation_str: Full equation string for context

        Returns:
            Dict with symbol information or None if invalid
        """
        # Get matched text
        matched_text = match.group(0)

        # Skip common LaTeX commands that aren't variables
        skip_commands = {
            'frac', 'sqrt', 'exp', 'ln', 'log', 'sin', 'cos', 'tan',
            'int', 'sum', 'prod', 'lim', 'partial', 'nabla', 'times',
            'cdot', 'left', 'right', 'text', 'mathrm', 'mathbf'
        }
        if any(cmd in matched_text for cmd in skip_commands):
            return None

        # Extract base symbol
        base_symbol = match.group(1) if match.groups() else matched_text

        # Extract subscripts
        subscripts = []
        sub_match = re.search(r'_\{?([a-zA-Z0-9]+)\}?', matched_text)
        if sub_match:
            subscripts.append(sub_match.group(1))

        # Extract superscripts
        superscripts = []
        sup_match = re.search(r'\^\{?([0-9]+)\}?', matched_text)
        if sup_match:
            superscripts.append(sup_match.group(1))

        # Check if left of equals sign
        left_of_equals = False
        equals_pos = equation_str.find('=')
        if equals_pos >= 0:
            match_pos = match.start()
            left_of_equals = match_pos < equals_pos

        # Check for derivative notation
        has_derivative = self._check_derivative_notation(matched_text, equation_str, match.start())

        # Check if in function argument
        in_function = self._check_function_argument(equation_str, match.start())

        return {
            'full_symbol': matched_text,
            'base_symbol': base_symbol,
            'subscripts': subscripts,
            'superscripts': superscripts,
            'left_of_equals': left_of_equals,
            'has_derivative': has_derivative,
            'in_function': in_function
        }

    def _check_derivative_notation(
        self,
        symbol: str,
        equation_str: str,
        position: int
    ) -> bool:
        """Check if symbol appears in derivative notation (d/dx, ∂/∂x, etc.)"""
        # Look for derivative patterns around the symbol position
        # Check before position (dy/d[x] case)
        before = equation_str[max(0, position-15):position]
        # Check after position ([d]y/dx case)
        after = equation_str[position:min(len(equation_str), position+15)]
        context = before + after

        derivative_patterns = [
            r'd\s*/\s*d',         # dy/dx (standard)
            r'd[a-zA-Zα-ωΑ-Ω]\s*/\s*d',  # dy/dx with variable
            r'\\partial',         # \partial (LaTeX partial derivative)
            r'\\frac\s*\{\s*d',  # \frac{dy}{dx}
            r'\\frac\s*\{\s*\\partial',  # \frac{\partial y}{\partial x}
        ]
        return any(re.search(pattern, context) for pattern in derivative_patterns)

    def _check_function_argument(self, equation_str: str, position: int) -> bool:
        """Check if symbol appears in function argument (sin(x), f(T), etc.)"""
        # Look before the position for function name followed by (
        before = equation_str[max(0, position-25):position]
        # Look for pattern: function_name(
        # Function names include: sin, cos, exp, f, g, etc.
        function_start_pattern = r'(sin|cos|tan|exp|ln|log|sqrt|[a-zA-Z])\s*\($'
        return bool(re.search(function_start_pattern, before))

    def _analyze_equation_structure(self, equation_str: str) -> Dict:
        """
        Analyze overall equation structure.

        Returns:
            Dict with keys: has_equals, left_side, right_side, is_definition
        """
        structure = {
            'has_equals': '=' in equation_str,
            'left_side': '',
            'right_side': '',
            'is_definition': False
        }

        if structure['has_equals']:
            parts = equation_str.split('=', 1)
            structure['left_side'] = parts[0].strip()
            structure['right_side'] = parts[1].strip() if len(parts) > 1 else ''

            # Check if it's a definition (single variable on left, possibly with subscripts/superscripts)
            # Pattern: single letter followed by optional subscript/superscript
            # Examples: q, q_r, T_s, T^4, x_i^2
            left_stripped = structure['left_side'].replace(' ', '')
            single_var_pattern = r'^[a-zA-Zα-ωΑ-Ω](_\{?[a-zA-Z0-9]+\}?)?(\^\{?[0-9]+\}?)?$'
            structure['is_definition'] = bool(re.match(single_var_pattern, left_stripped))

        return structure

    def _classify_variable_role(
        self,
        symbol_info: Dict,
        equation_structure: Dict,
        equation_id: Optional[str]
    ) -> VariableRole:
        """
        Classify variable role based on indicators.

        Classification rules (from config):
        - OUTPUT: Left of equals sign in definition equation
        - INPUT: Has derivative, or in function argument
        - PARAMETER: Greek letter, known physical meaning, doesn't fit above
        """
        classification_config = self.config['variable_extraction']['equation']['classification']

        # Check OUTPUT indicators
        if equation_structure['is_definition'] and symbol_info.get('left_of_equals', False):
            return VariableRole.OUTPUT

        # Check INPUT indicators
        input_indicators = classification_config['input_indicators']
        if symbol_info.get('has_derivative', False):
            return VariableRole.INPUT
        if symbol_info.get('in_function', False):
            return VariableRole.INPUT

        # Check PARAMETER indicators
        parameter_indicators = classification_config['parameter_indicators']
        if self._is_greek_letter(symbol_info['base_symbol']):
            return VariableRole.PARAMETER

        # Default: treat as parameter if can't determine
        return VariableRole.PARAMETER

    def _is_greek_letter(self, symbol: str) -> bool:
        """Check if symbol is a Greek letter"""
        # Check if the symbol itself is Greek
        if symbol in self.greek_letters:
            return True

        # Check if it's a LaTeX command for Greek letter
        if symbol.startswith('\\'):
            command = symbol[1:]  # Remove backslash
            return command in self.greek_letters

        return False

    def extract_from_multiple_equations(
        self,
        equations: List[Dict]
    ) -> Dict[str, List[EquationVariable]]:
        """
        Extract variables from multiple equations.

        Args:
            equations: List of dicts with keys: equation_id, equation_text, equation_latex

        Returns:
            Dict mapping equation_id to list of EquationVariable objects
        """
        results = {}

        for eq in equations:
            eq_id = eq.get('equation_id')
            eq_text = eq.get('equation_text', '')
            eq_latex = eq.get('equation_latex')

            variables = self.extract_from_equation(
                equation_text=eq_text,
                equation_latex=eq_latex,
                equation_id=eq_id
            )

            results[eq_id] = variables

        return results

    def get_variable_summary(
        self,
        variables: List[EquationVariable]
    ) -> Dict:
        """
        Generate summary statistics for extracted variables.

        Returns:
            Dict with counts by role, symbols, etc.
        """
        summary = {
            'total_variables': len(variables),
            'by_role': {
                'input': 0,
                'output': 0,
                'parameter': 0
            },
            'greek_letters': 0,
            'with_subscripts': 0,
            'with_superscripts': 0,
            'with_derivatives': 0,
            'resolved_to_canonical': 0,
            'unique_base_symbols': set()
        }

        for var in variables:
            # Count by role
            summary['by_role'][var.role.value] += 1

            # Other counts
            if var.is_greek_letter:
                summary['greek_letters'] += 1
            if var.subscripts:
                summary['with_subscripts'] += 1
            if var.superscripts:
                summary['with_superscripts'] += 1
            if var.has_derivative:
                summary['with_derivatives'] += 1
            if var.canonical_id:
                summary['resolved_to_canonical'] += 1

            # Track unique base symbols
            base = var.symbol.split('_')[0].split('^')[0]
            summary['unique_base_symbols'].add(base)

        summary['unique_base_symbols'] = len(summary['unique_base_symbols'])

        return summary
