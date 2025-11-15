#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Variable Matching Engine

Matches equation variables to table columns using multi-factor scoring:
- Symbol exact match (40%)
- Dimensional consistency (30%)
- Semantic tag overlap (20%)
- Name similarity (10%)

Author: V12 Development Team
Created: 2025-11-04
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import difflib

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

from src.detectors.data_structures import (
    VariableLinkage, VariableRole, LookupMethod,
    UnitInfo, ConfidenceScore, ConfidenceFactors
)
from src.detectors.equation_variable_extractor import EquationVariable
from src.detectors.table_column_analyzer import TableColumnInfo
from src.core.semantic_registry import SemanticRegistry


class VariableMatchingEngine:
    """
    Match equation variables to table columns using multi-factor scoring.

    Responsibilities:
    - Compute match scores between variables and columns
    - Apply weighted scoring from config
    - Filter by confidence threshold
    - Handle ambiguous matches
    - Use SemanticRegistry for dimensional analysis
    """

    def __init__(
        self,
        semantic_registry: SemanticRegistry,
        config: Dict
    ):
        """
        Initialize variable matching engine.

        Args:
            semantic_registry: SemanticRegistry for dimensional analysis
            config: Configuration dict from data_dependency_config.yaml
        """
        self.semantic_registry = semantic_registry
        self.config = config
        self.weights = config['matching']['weights']
        self.thresholds = config['matching']['thresholds']

    def match_variables(
        self,
        equation_vars: List[EquationVariable],
        table_columns: List[TableColumnInfo]
    ) -> List[VariableLinkage]:
        """
        Match equation variables to table columns.

        Args:
            equation_vars: List of EquationVariable from equation
            table_columns: List of TableColumnInfo from table

        Returns:
            List of VariableLinkage with confidence >= threshold
        """
        matches = []

        for eq_var in equation_vars:
            # Find best match for this variable
            best_match = None
            best_score = 0.0
            best_factors = None
            candidates = []

            for table_col in table_columns:
                # Compute match score
                score, factors = self._compute_match_score(eq_var, table_col)

                candidates.append({
                    'column': table_col,
                    'score': score,
                    'factors': factors
                })

                if score > best_score:
                    best_score = score
                    best_match = table_col
                    best_factors = factors

            # Check if best match meets threshold
            min_confidence = self.thresholds['minimum_confidence']
            if best_match and best_score >= min_confidence:
                # Determine lookup method
                lookup_method = self._determine_lookup_method(best_match)

                # Create linkage
                linkage = VariableLinkage(
                    variable_id=eq_var.canonical_id or f"var:{eq_var.symbol}",
                    symbol=eq_var.symbol,
                    name=best_match.name or eq_var.symbol,
                    equation_role=eq_var.role,
                    table_column=best_match.header_text,
                    table_column_index=best_match.column_index,
                    lookup_method=lookup_method,
                    lookup_key_column=None,  # Will be set later if needed
                    units=UnitInfo(
                        equation_units=self._get_equation_units(eq_var),
                        table_units=best_match.units or "dimensionless",
                        conversion_needed=False  # Will be checked during validation
                    )
                )

                matches.append({
                    'linkage': linkage,
                    'confidence': ConfidenceScore(
                        score=best_score,
                        method="multi_factor_weighted",
                        factors=best_factors
                    ),
                    'candidates': candidates
                })

        return [m['linkage'] for m in matches], [m['confidence'] for m in matches]

    def _compute_match_score(
        self,
        eq_var: EquationVariable,
        table_col: TableColumnInfo
    ) -> Tuple[float, ConfidenceFactors]:
        """
        Compute weighted match score (0.0-1.0).

        Args:
            eq_var: Equation variable
            table_col: Table column

        Returns:
            Tuple of (score, factors)
        """
        factors = ConfidenceFactors()

        # Factor 1: Symbol exact match (40%)
        factors.symbol_exact_match = self._symbol_exact_match(
            eq_var.symbol,
            table_col.symbol
        )

        # Factor 2: Dimensional consistency (30%)
        factors.dimensional_consistency = self._dimensional_consistency(
            eq_var,
            table_col
        )

        # Factor 3: Semantic tag overlap (20%)
        factors.semantic_tag_overlap = self._semantic_tag_overlap(
            eq_var,
            table_col
        )

        # Factor 4: Name similarity (10%)
        factors.name_similarity = self._name_similarity(
            eq_var.symbol,
            table_col.name
        )

        # Compute weighted score
        score = (
            factors.symbol_exact_match * self.weights['symbol_exact_match'] +
            factors.dimensional_consistency * self.weights['dimensional_consistency'] +
            factors.semantic_tag_overlap * self.weights['semantic_tag_overlap'] +
            factors.name_similarity * self.weights['name_similarity']
        )

        return score, factors

    def _symbol_exact_match(self, sym1: Optional[str], sym2: Optional[str]) -> float:
        """
        Symbol comparison (1.0 or 0.0).

        Args:
            sym1: Equation variable symbol
            sym2: Table column symbol

        Returns:
            1.0 if exact match, 0.0 otherwise
        """
        if not sym1 or not sym2:
            return 0.0

        # Normalize symbols (case-insensitive for Latin, case-sensitive for Greek)
        sym1_clean = sym1.strip()
        sym2_clean = sym2.strip()

        # Exact match
        if sym1_clean == sym2_clean:
            return 1.0

        # Case-insensitive match for Latin letters
        if sym1_clean.lower() == sym2_clean.lower():
            # Only if both are Latin (not Greek)
            if sym1_clean.isascii() and sym2_clean.isascii():
                return 1.0

        return 0.0

    def _dimensional_consistency(
        self,
        eq_var: EquationVariable,
        table_col: TableColumnInfo
    ) -> float:
        """
        Dimensional analysis via SemanticRegistry (1.0, 0.5, or 0.0).

        Args:
            eq_var: Equation variable
            table_col: Table column

        Returns:
            1.0 if same dimensions, 0.5 if compatible, 0.0 if incompatible
        """
        # Try to get dimensional info from SemanticRegistry
        if not self.semantic_registry or not eq_var.canonical_id or not table_col.canonical_id:
            # No registry or IDs → can't determine, return neutral
            return 0.5

        # Get dimension info from registry
        eq_dims = self.semantic_registry.get_dimensions(eq_var.canonical_id)
        col_dims = self.semantic_registry.get_dimensions(table_col.canonical_id)

        if not eq_dims or not col_dims:
            # Can't determine dimensions
            return 0.5

        # Compare dimensions
        if eq_dims == col_dims:
            return 1.0

        # Check if units are provided and match
        if table_col.units:
            # If both are dimensionless
            if eq_dims == "dimensionless" and table_col.units == "dimensionless":
                return 1.0

            # Check for unit compatibility (could be expanded)
            # For now, just check if units are present and non-contradictory
            return 0.5

        return 0.0

    def _semantic_tag_overlap(
        self,
        eq_var: EquationVariable,
        table_col: TableColumnInfo
    ) -> float:
        """
        Jaccard similarity of semantic tags (0.0-1.0).

        Args:
            eq_var: Equation variable
            table_col: Table column

        Returns:
            Jaccard similarity score
        """
        # Get tags from SemanticRegistry
        if not self.semantic_registry or not eq_var.canonical_id or not table_col.canonical_id:
            return 0.0

        eq_tags = self.semantic_registry.get_tags(eq_var.canonical_id)
        col_tags = self.semantic_registry.get_tags(table_col.canonical_id)

        if not eq_tags or not col_tags:
            return 0.0

        # Convert to sets
        eq_set = set(eq_tags)
        col_set = set(col_tags)

        # Jaccard similarity: |intersection| / |union|
        intersection = len(eq_set & col_set)
        union = len(eq_set | col_set)

        if union == 0:
            return 0.0

        return intersection / union

    def _name_similarity(self, symbol: str, name: Optional[str]) -> float:
        """
        Levenshtein distance similarity (0.0-1.0).

        Args:
            symbol: Variable symbol
            name: Column name

        Returns:
            Similarity score (1.0 = identical, 0.0 = completely different)
        """
        if not symbol or not name:
            return 0.0

        # Convert symbol to potential name (e.g., 'ε' → 'epsilon', 'k' → 'k')
        symbol_as_name = self._symbol_to_name(symbol)

        # Use difflib for string similarity
        similarity = difflib.SequenceMatcher(
            None,
            symbol_as_name.lower(),
            name.lower()
        ).ratio()

        return similarity

    def _symbol_to_name(self, symbol: str) -> str:
        """
        Convert symbol to potential name.

        Examples:
        - 'ε' → 'epsilon'
        - 'k' → 'conductivity' (if known)
        - 'T' → 'temperature'
        """
        # Greek letter mapping
        greek_names = {
            'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta',
            'ε': 'epsilon', 'ζ': 'zeta', 'η': 'eta', 'θ': 'theta',
            'κ': 'kappa', 'λ': 'lambda', 'μ': 'mu', 'ν': 'nu',
            'ξ': 'xi', 'ο': 'omicron', 'π': 'pi', 'ρ': 'rho',
            'σ': 'sigma', 'τ': 'tau', 'υ': 'upsilon', 'φ': 'phi',
            'χ': 'chi', 'ψ': 'psi', 'ω': 'omega'
        }

        if symbol in greek_names:
            return greek_names[symbol]

        # Common physics symbols
        common_names = {
            'k': 'conductivity',
            'h': 'coefficient',
            'T': 'temperature',
            'P': 'pressure',
            'ρ': 'density',
            'q': 'heat'
        }

        return common_names.get(symbol, symbol)

    def _determine_lookup_method(self, table_col: TableColumnInfo) -> LookupMethod:
        """
        Determine appropriate lookup method based on column type.

        Args:
            table_col: Table column information

        Returns:
            LookupMethod enum value
        """
        if table_col.is_index_column:
            return LookupMethod.SELECT_BY_CATEGORY

        if table_col.data_type == "categorical":
            return LookupMethod.SELECT_BY_CATEGORY
        elif table_col.data_type == "continuous":
            return LookupMethod.INTERPOLATE_LINEAR
        elif table_col.data_type == "discrete":
            return LookupMethod.EXACT_MATCH
        else:
            # Default
            return LookupMethod.SELECT_BY_CATEGORY

    def _get_equation_units(self, eq_var: EquationVariable) -> str:
        """
        Get units for equation variable.

        Args:
            eq_var: Equation variable

        Returns:
            Units string or "dimensionless"
        """
        # Try to get from SemanticRegistry
        if self.semantic_registry and eq_var.canonical_id:
            units = self.semantic_registry.get_units(eq_var.canonical_id)
            if units:
                return units

        # Default
        return "dimensionless"

    def get_matching_summary(
        self,
        equation_vars: List[EquationVariable],
        table_columns: List[TableColumnInfo],
        matches: List[VariableLinkage]
    ) -> Dict:
        """
        Generate summary statistics for matching results.

        Returns:
            Dict with match statistics
        """
        summary = {
            'total_equation_vars': len(equation_vars),
            'total_table_columns': len(table_columns),
            'successful_matches': len(matches),
            'match_rate': len(matches) / len(equation_vars) if equation_vars else 0.0,
            'unmatched_variables': len(equation_vars) - len(matches),
            'by_role': {
                'input': 0,
                'output': 0,
                'parameter': 0
            },
            'by_lookup_method': {
                'categorical': 0,
                'interpolate': 0,
                'exact': 0
            }
        }

        # Count by role
        for var in equation_vars:
            if var.role:
                summary['by_role'][var.role.value] += 1

        # Count by lookup method
        for match in matches:
            method_value = match.lookup_method.value
            if 'categorical' in method_value or 'select' in method_value:
                summary['by_lookup_method']['categorical'] += 1
            elif 'interpolate' in method_value:
                summary['by_lookup_method']['interpolate'] += 1
            elif 'exact' in method_value:
                summary['by_lookup_method']['exact'] += 1

        return summary
