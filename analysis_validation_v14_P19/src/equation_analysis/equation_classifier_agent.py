# -*- coding: utf-8 -*-
"""
Equation Classifier Agent - Semantic Classification of Mathematical Equations

This agent classifies equations into two categories based on their intended use:
1. COMPUTATIONAL: Direct calculation equations (input → output)
2. RELATIONAL: Constraints, conservation laws, fundamental relationships

Author: Document Translator V11 System
Date: 2025-10-09
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class StructuralFeatures:
    """Features extracted from LaTeX structure analysis."""
    has_isolated_output: bool
    has_equality_chain: bool
    has_differential: bool
    has_summation: bool
    has_reciprocity_pattern: bool
    num_equals_signs: int
    num_variables: int
    complexity_score: float


@dataclass
class SymbolFeatures:
    """Features from symbol and variable analysis."""
    output_variable: Optional[str]
    input_variables: List[str]
    constants: List[str]
    has_heat_transfer_symbol: bool
    has_dimensionless_number: bool
    has_property_symbol: bool


@dataclass
class PatternMatch:
    """Result of pattern matching against known equation types."""
    pattern_type: str
    confidence: float
    description: str


@dataclass
class ClassificationResult:
    """Complete classification result for an equation."""
    equation_number: str
    classification: str  # 'computational', 'relational', or 'ambiguous'
    confidence: float
    structural_score: float
    symbol_score: float
    pattern_score: float
    rationale: Dict[str, str]
    features: Dict


class EquationClassifierAgent:
    """
    Semantic classifier for mathematical equations.

    Uses multi-layer analysis:
    1. Structural analysis (LaTeX parsing)
    2. Symbol analysis (variable roles)
    3. Pattern matching (domain knowledge)
    4. Confidence scoring
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the classifier.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or self._default_config()

        # Pattern libraries
        self._init_pattern_libraries()

    def _default_config(self) -> Dict:
        """Default configuration."""
        return {
            'thresholds': {
                'computational_high': 0.6,  # Lowered from 0.7 based on analysis
                'relational_low': 0.35      # Raised from 0.3 for tighter classification
            },
            'weights': {
                'structural': 0.4,
                'symbol': 0.3,
                'pattern': 0.3
            }
        }

    def _init_pattern_libraries(self):
        """Initialize pattern matching libraries."""

        # Computational patterns
        self.computational_patterns = {
            'heat_transfer': {
                'symbols': ['q', 'q_{', 'Q'],
                'description': 'Heat transfer calculation'
            },
            'dimensionless': {
                'symbols': ['Nu', 'Re', 'Pr', 'Gr', 'Ra', 'St', 'Pe'],
                'description': 'Dimensionless number calculation'
            },
            'temperature_calc': {
                'symbols': ['T_2', 'T_{2}', 'T_{out}'],
                'description': 'Temperature calculation'
            },
            'coefficient': {
                'symbols': ['h =', 'U =', 'k_{eff}'],
                'description': 'Heat transfer coefficient'
            }
        }

        # Relational patterns
        self.relational_patterns = {
            'conservation': {
                'patterns': [r'=.*=.*1', r'\+.*\+.*=\s*1', r'energy.*in.*=.*out'],
                'description': 'Conservation law'
            },
            'reciprocity': {
                'patterns': [r'q_{12}.*=.*-.*q_{21}', r'A.*F.*=.*A.*F'],
                'description': 'Reciprocity relationship'
            },
            'summation': {
                'patterns': [r'\\sum.*=\s*1', r'\\Sigma.*=\s*1'],
                'description': 'Summation constraint'
            },
            'property_equality': {
                'patterns': [r'^[^=]+=\s*[^=]+$', r'\\varepsilon.*=.*\\alpha'],
                'description': 'Property equality'
            },
            'differential': {
                'patterns': [r'\\frac{d', r'\\frac{\\partial', r'\\nabla', r'=\s*0\s*$'],
                'description': 'Differential equation'
            }
        }

        # Output variable patterns (computational indicators)
        self.output_variables = [
            'q', 'Q', 'h', 'U', 'Nu', 'Re', 'Pr', 'Gr', 'Ra', 'St', 'Pe',
            'T_2', 'T_{out}', 'T_{2}', 'R_{eq}'
        ]

        # Property symbols (relational indicators)
        self.property_symbols = [
            'varepsilon', 'alpha', 'rho', 'tau', 'sigma'
        ]

    def classify_equation(self, equation: Dict) -> ClassificationResult:
        """
        Classify a single equation.

        Args:
            equation: Dictionary with 'latex', 'equation_number', etc.

        Returns:
            ClassificationResult with classification and confidence
        """
        latex = equation.get('latex', '')
        eq_num = equation.get('equation_number', 'unknown')

        # Layer 1: Structural analysis
        structural = self.analyze_structure(latex)
        structural_score = self._score_structural(structural)

        # Layer 2: Symbol analysis
        symbols = self.analyze_symbols(latex)
        symbol_score = self._score_symbols(symbols)

        # Layer 3: Pattern matching
        patterns = self.match_patterns(latex)
        pattern_score = self._score_patterns(patterns)

        # Calculate combined confidence
        weights = self.config['weights']
        confidence = (
            weights['structural'] * structural_score +
            weights['symbol'] * symbol_score +
            weights['pattern'] * pattern_score
        )

        # Classify based on confidence
        thresholds = self.config['thresholds']
        if confidence >= thresholds['computational_high']:
            classification = 'computational'
        elif confidence <= thresholds['relational_low']:
            classification = 'relational'
        else:
            classification = 'ambiguous'

        # Build rationale
        rationale = self._build_rationale(structural, symbols, patterns)

        # Combine features
        features = {
            'structural': asdict(structural),
            'symbols': asdict(symbols),
            'patterns': [{'type': p.pattern_type, 'confidence': p.confidence} for p in patterns]
        }

        return ClassificationResult(
            equation_number=eq_num,
            classification=classification,
            confidence=confidence,
            structural_score=structural_score,
            symbol_score=symbol_score,
            pattern_score=pattern_score,
            rationale=rationale,
            features=features
        )

    def analyze_structure(self, latex: str) -> StructuralFeatures:
        """
        Analyze LaTeX structural features.

        Args:
            latex: LaTeX equation string

        Returns:
            StructuralFeatures object
        """
        # Check for isolated output variable (y = f(x1, x2, ...))
        has_isolated = self._check_isolated_output(latex)

        # Check for equality chains (a = b = c)
        num_equals = latex.count('=')
        has_equality_chain = num_equals > 1 and '\\begin{array}' not in latex

        # Check for differential operators
        has_differential = bool(
            re.search(r'\\frac{d|\\frac{\\partial|\\nabla', latex)
        )

        # Check for summation
        has_summation = bool(
            re.search(r'\\sum|\\Sigma', latex)
        )

        # Check for reciprocity pattern (q12 = -q21, A1F12 = A2F21)
        has_reciprocity = bool(
            re.search(r'=\s*-', latex) or
            re.search(r'[A-Z]_[12].*=.*[A-Z]_[21]', latex)
        )

        # Count variables (rough estimate)
        variables = re.findall(r'[a-zA-Z]_{?[a-zA-Z0-9]+}?', latex)
        num_variables = len(set(variables))

        # Complexity score (arithmetic operations)
        complexity = (
            latex.count('\\frac') * 2 +
            latex.count('\\times') +
            latex.count('\\cdot') +
            latex.count('^') * 0.5
        ) / max(len(latex), 1) * 100

        return StructuralFeatures(
            has_isolated_output=has_isolated,
            has_equality_chain=has_equality_chain,
            has_differential=has_differential,
            has_summation=has_summation,
            has_reciprocity_pattern=has_reciprocity,
            num_equals_signs=num_equals,
            num_variables=num_variables,
            complexity_score=complexity
        )

    def _check_isolated_output(self, latex: str) -> bool:
        """
        Check if equation has form: y = f(x1, x2, ...)

        Single variable on left, expression on right.
        """
        # Remove array environments
        if '\\begin{array}' in latex:
            return False

        # Split on equals
        parts = latex.split('=')
        if len(parts) != 2:
            return False

        left = parts[0].strip()
        right = parts[1].strip()

        # Left side should be simple variable (not expression)
        # Right side should have arithmetic
        left_simple = not any(op in left for op in ['\\frac', '\\times', '\\cdot', '+', '-', '^'])
        right_complex = any(op in right for op in ['\\frac', '\\times', '\\cdot', '+', '-', '^'])

        return left_simple and right_complex

    def analyze_symbols(self, latex: str) -> SymbolFeatures:
        """
        Analyze symbols and variables.

        Args:
            latex: LaTeX equation string

        Returns:
            SymbolFeatures object
        """
        # Try to identify output variable (left side of =)
        output_var = None
        if '=' in latex and '\\begin{array}' not in latex:
            left = latex.split('=')[0].strip()
            # Extract main variable
            match = re.search(r'([a-zA-Z]_?{?[a-zA-Z0-9]+}?)', left)
            if match:
                output_var = match.group(1)

        # Extract all variables
        all_vars = re.findall(r'([a-zA-Z]_?{?[a-zA-Z0-9]+}?)', latex)
        all_vars = list(set(all_vars))

        # Identify input variables (exclude output)
        input_vars = [v for v in all_vars if v != output_var]

        # Identify constants (sigma, g, c_p, etc.)
        constants = []
        for var in all_vars:
            if any(const in var for const in ['sigma', 'pi', 'g']):
                constants.append(var)

        # Check for heat transfer symbols
        has_heat_transfer = any(
            symbol in latex for symbol in ['q', 'Q', 'q_{']
        )

        # Check for dimensionless numbers
        has_dimensionless = any(
            symbol in latex for symbol in ['Nu', 'Re', 'Pr', 'Gr', 'Ra', 'St', 'Pe']
        )

        # Check for property symbols (Greek letters)
        has_property = any(
            symbol in latex for symbol in self.property_symbols
        )

        return SymbolFeatures(
            output_variable=output_var,
            input_variables=input_vars,
            constants=constants,
            has_heat_transfer_symbol=has_heat_transfer,
            has_dimensionless_number=has_dimensionless,
            has_property_symbol=has_property
        )

    def match_patterns(self, latex: str) -> List[PatternMatch]:
        """
        Match equation against known patterns.

        Args:
            latex: LaTeX equation string

        Returns:
            List of PatternMatch objects
        """
        matches = []

        # Check computational patterns
        for pattern_name, pattern_info in self.computational_patterns.items():
            if any(symbol in latex for symbol in pattern_info['symbols']):
                matches.append(PatternMatch(
                    pattern_type=f'computational_{pattern_name}',
                    confidence=0.8,
                    description=pattern_info['description']
                ))

        # Check relational patterns
        for pattern_name, pattern_info in self.relational_patterns.items():
            for pattern in pattern_info['patterns']:
                if re.search(pattern, latex):
                    matches.append(PatternMatch(
                        pattern_type=f'relational_{pattern_name}',
                        confidence=0.9,
                        description=pattern_info['description']
                    ))
                    break

        return matches

    def _score_structural(self, features: StructuralFeatures) -> float:
        """
        Calculate structural score (0-1, higher = more computational).

        Args:
            features: StructuralFeatures object

        Returns:
            Score from 0.0 (relational) to 1.0 (computational)
        """
        score = 0.5  # Start neutral

        # Computational indicators
        if features.has_isolated_output:
            score += 0.3
        if features.complexity_score > 5:
            score += 0.2
        if features.num_variables >= 4:
            score += 0.1

        # Relational indicators
        if features.has_differential:
            score -= 0.4
        if features.has_summation and features.num_equals_signs == 1:
            score -= 0.3
        if features.has_reciprocity_pattern:
            score -= 0.3
        if features.has_equality_chain:
            score -= 0.2
        if features.num_variables <= 2 and features.num_equals_signs == 1:
            score -= 0.2

        return max(0.0, min(1.0, score))

    def _score_symbols(self, features: SymbolFeatures) -> float:
        """
        Calculate symbol score (0-1, higher = more computational).

        Args:
            features: SymbolFeatures object

        Returns:
            Score from 0.0 (relational) to 1.0 (computational)
        """
        score = 0.5  # Start neutral

        # Computational indicators
        if features.has_heat_transfer_symbol:
            score += 0.3
        if features.has_dimensionless_number:
            score += 0.3
        if features.output_variable and any(
            out in features.output_variable for out in self.output_variables
        ):
            score += 0.2
        if len(features.input_variables) >= 3:
            score += 0.2

        # Relational indicators
        if features.has_property_symbol and len(features.input_variables) <= 2:
            score -= 0.3

        return max(0.0, min(1.0, score))

    def _score_patterns(self, patterns: List[PatternMatch]) -> float:
        """
        Calculate pattern score (0-1, higher = more computational).

        Args:
            patterns: List of PatternMatch objects

        Returns:
            Score from 0.0 (relational) to 1.0 (computational)
        """
        if not patterns:
            return 0.5  # Neutral if no patterns matched

        # Average confidence of computational patterns
        comp_scores = [
            p.confidence for p in patterns
            if p.pattern_type.startswith('computational')
        ]

        # Average confidence of relational patterns
        rel_scores = [
            p.confidence for p in patterns
            if p.pattern_type.startswith('relational')
        ]

        if comp_scores and not rel_scores:
            return sum(comp_scores) / len(comp_scores)
        elif rel_scores and not comp_scores:
            return 1.0 - (sum(rel_scores) / len(rel_scores))
        elif comp_scores and rel_scores:
            # Both present, use difference
            comp_avg = sum(comp_scores) / len(comp_scores)
            rel_avg = sum(rel_scores) / len(rel_scores)
            return 0.5 + 0.5 * (comp_avg - rel_avg)
        else:
            return 0.5

    def _build_rationale(
        self,
        structural: StructuralFeatures,
        symbols: SymbolFeatures,
        patterns: List[PatternMatch]
    ) -> Dict[str, str]:
        """
        Build human-readable rationale for classification.

        Returns:
            Dictionary with rationale for each layer
        """
        # Structural rationale
        struct_reasons = []
        if structural.has_isolated_output:
            struct_reasons.append("Isolated output variable on left side")
        if structural.has_differential:
            struct_reasons.append("Contains differential operators (governing equation)")
        if structural.has_summation:
            struct_reasons.append("Contains summation (constraint pattern)")
        if structural.has_reciprocity_pattern:
            struct_reasons.append("Reciprocity pattern detected")
        if structural.complexity_score > 5:
            struct_reasons.append(f"Complex expression (score: {structural.complexity_score:.1f})")
        if not struct_reasons:
            struct_reasons.append("Simple structural form")

        # Symbol rationale
        symbol_reasons = []
        if symbols.has_heat_transfer_symbol:
            symbol_reasons.append("Heat transfer variable detected")
        if symbols.has_dimensionless_number:
            symbol_reasons.append("Dimensionless number calculation")
        if symbols.has_property_symbol:
            symbol_reasons.append("Material property symbols present")
        if symbols.output_variable:
            symbol_reasons.append(f"Output variable: {symbols.output_variable}")
        if len(symbols.input_variables) >= 3:
            symbol_reasons.append(f"{len(symbols.input_variables)} input parameters")
        if not symbol_reasons:
            symbol_reasons.append("Few variables, simple relationship")

        # Pattern rationale
        pattern_reasons = []
        for pattern in patterns:
            pattern_reasons.append(f"{pattern.description} (conf: {pattern.confidence:.2f})")
        if not pattern_reasons:
            pattern_reasons.append("No specific patterns matched")

        return {
            'structural': '; '.join(struct_reasons),
            'symbols': '; '.join(symbol_reasons),
            'patterns': '; '.join(pattern_reasons)
        }


def main():
    """Test the classifier on sample equations."""
    print("EquationClassifierAgent - Test Run\n")
    print("="*60)

    # Test equations
    test_cases = [
        {
            'equation_number': '10',
            'latex': '{\\mathcal{E}}\\,=\\,\\alpha',
            'expected': 'relational'
        },
        {
            'equation_number': '11',
            'latex': 'q_{12}\\;=\\;A_{1}\\:F_{12}\\:\\sigma\\:\\left(\\!\\:T_{1}^{4}\\:-\\:T_{2}^{4}\\right)',
            'expected': 'computational'
        },
        {
            'equation_number': '12',
            'latex': 'q_{12}\\;=\\;-\\,q_{21}',
            'expected': 'relational'
        }
    ]

    classifier = EquationClassifierAgent()

    for test in test_cases:
        result = classifier.classify_equation(test)

        print(f"\nEquation {test['equation_number']}: {test['latex'][:50]}...")
        print(f"Expected: {test['expected']}")
        print(f"Classified as: {result.classification}")
        print(f"Confidence: {result.confidence:.3f}")
        print(f"Scores: Struct={result.structural_score:.2f}, "
              f"Symbol={result.symbol_score:.2f}, Pattern={result.pattern_score:.2f}")
        match_str = "MATCH" if result.classification == test['expected'] else "MISMATCH"
        print(f"[{match_str}]")

    print("\n" + "="*60)


if __name__ == '__main__':
    main()
