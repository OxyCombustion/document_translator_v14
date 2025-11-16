#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LaTeX Quality Control Agent with Re-extraction Feedback Loop

This agent implements a quality-first approach to equation extraction:
1. Validates LaTeX parseability with SymPy
2. Analyzes failure patterns to identify extraction issues
3. Triggers re-extraction with adjusted parameters
4. Iterates until quality threshold is met or max attempts reached

Architecture:
- LaTeX Quality Validator: Checks SymPy parseability
- Failure Pattern Analyzer: Diagnoses why extraction failed
- Extraction Parameter Optimizer: Adjusts extraction settings
- Re-extraction Controller: Coordinates the feedback loop

This is GENERIC - works for any document by adjusting extraction, not patching output.
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
from dataclasses import dataclass, asdict
from enum import Enum
import re

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


class FailureCategory(Enum):
    """Categories of extraction failures that can be fixed by re-extraction"""
    LOW_RESOLUTION = "low_resolution"  # OCR quality issue - increase DPI
    INCOMPLETE_CROP = "incomplete_crop"  # Equation truncated - expand bbox
    BACKGROUND_NOISE = "background_noise"  # Text contamination - refine bbox
    SPACING_ISSUES = "spacing_issues"  # OCR spacing artifacts - OCR tuning
    COMPLEX_STRUCTURE = "complex_structure"  # Multi-line equations - adaptive sizing
    SYMBOL_MISRECOGNITION = "symbol_misrecognition"  # Wrong chars - OCR model switch
    UNFIXABLE = "unfixable"  # Array structures, etc. - defer to Phase B


@dataclass
class FailureAnalysis:
    """Analysis of why LaTeX parsing failed"""
    equation_id: str
    category: FailureCategory
    confidence: float  # 0.0-1.0 confidence in diagnosis
    evidence: List[str]  # Specific patterns that indicate this category
    recommended_actions: List[Dict[str, any]]  # Extraction parameter adjustments


@dataclass
class ReextractionAttempt:
    """Record of a re-extraction attempt"""
    attempt_number: int
    parameters: Dict[str, any]  # Extraction parameters used
    success: bool
    new_latex: Optional[str]
    parse_result: Optional[Dict]
    improvements: List[str]  # What improved from previous attempt


class LaTeXQualityValidator:
    """Validates LaTeX quality by attempting SymPy parsing"""

    def __init__(self):
        try:
            from sympy.parsing.latex import parse_latex
            self.parse_latex = parse_latex
            self.sympy_available = True
        except ImportError:
            print("⚠️  SymPy not available - LaTeX validation disabled")
            self.sympy_available = False

    def validate(self, latex: str) -> Tuple[bool, Optional[str]]:
        """
        Validate LaTeX can be parsed by SymPy.

        Returns:
            (success, error_message)
        """
        if not self.sympy_available:
            return (False, "SymPy not installed")

        try:
            expr = self.parse_latex(latex)
            return (True, None)
        except Exception as e:
            return (False, str(e))


class FailurePatternAnalyzer:
    """Analyzes LaTeX parsing failures to diagnose extraction issues"""

    def __init__(self):
        # Pattern signatures for each failure category
        self.category_patterns = {
            FailureCategory.SPACING_ISSUES: [
                (r'\\\ ', "Backslash-space artifacts from OCR"),
                (r'~', "Non-breaking space in LaTeX"),
                (r'\s{3,}', "Excessive spacing"),
            ],
            FailureCategory.SYMBOL_MISRECOGNITION: [
                (r'[^\x00-\x7F]', "Non-ASCII characters (OCR misread)"),
                (r'\\mathrm\{[A-Z]+\}', "Text mode letters (should be math)"),
                (r'\|', "Vertical bars (often misread delimiters)"),
            ],
            FailureCategory.INCOMPLETE_CROP: [
                # These patterns suggest equation was cut off
                (r'^\.\.\.|\\ldots$', "Equation starts/ends with ellipsis"),
                (r'^[+\-*/=]', "Starts with operator (likely incomplete)"),
                (r'[+\-*/=]$', "Ends with operator (likely incomplete)"),
            ],
            FailureCategory.COMPLEX_STRUCTURE: [
                (r'\\begin\{array\}', "Array environment (multi-line)"),
                (r'\\begin\{cases\}', "Cases environment (piecewise)"),
                (r'\\\\', "Line breaks (multi-line equation)"),
            ],
            FailureCategory.BACKGROUND_NOISE: [
                (r'[A-Z]{3,}', "All-caps words (surrounding text)"),
                (r'\bthe\b|\band\b|\bor\b', "English words contaminating equation"),
            ],
        }

    def analyze(self, equation: Dict, error_message: str) -> FailureAnalysis:
        """
        Analyze why equation parsing failed and categorize the issue.

        Args:
            equation: Equation dict with 'latex' and metadata
            error_message: SymPy parsing error message

        Returns:
            FailureAnalysis with category and recommended actions
        """
        latex = equation.get('latex', '')
        eq_id = equation.get('equation_number', 'unknown')

        # Score each category based on pattern matches
        category_scores = {}
        evidence_by_category = {}

        for category, patterns in self.category_patterns.items():
            score = 0
            evidence = []
            for pattern, description in patterns:
                if re.search(pattern, latex):
                    score += 1
                    evidence.append(description)

            if score > 0:
                category_scores[category] = score
                evidence_by_category[category] = evidence

        # Check for array structures (unfixable in Phase A)
        if FailureCategory.COMPLEX_STRUCTURE in category_scores:
            if 'array' in latex.lower():
                return FailureAnalysis(
                    equation_id=eq_id,
                    category=FailureCategory.UNFIXABLE,
                    confidence=0.95,
                    evidence=["Array/alignment structure - deferred to Phase B"],
                    recommended_actions=[]
                )

        # Find top category
        if not category_scores:
            # No patterns matched - generic unfixable
            return FailureAnalysis(
                equation_id=eq_id,
                category=FailureCategory.UNFIXABLE,
                confidence=0.5,
                evidence=[f"No specific patterns matched. Error: {error_message[:100]}"],
                recommended_actions=[]
            )

        top_category = max(category_scores, key=category_scores.get)
        confidence = min(0.95, category_scores[top_category] * 0.3)  # Scale to 0.0-1.0

        # Generate recommended actions based on category
        actions = self._generate_actions(top_category, equation)

        return FailureAnalysis(
            equation_id=eq_id,
            category=top_category,
            confidence=confidence,
            evidence=evidence_by_category[top_category],
            recommended_actions=actions
        )

    def _generate_actions(self, category: FailureCategory, equation: Dict) -> List[Dict]:
        """Generate extraction parameter adjustments for the failure category"""

        actions = []

        if category == FailureCategory.LOW_RESOLUTION:
            actions.append({
                'parameter': 'dpi',
                'current': 216,
                'new': 300,
                'reason': 'Increase resolution for clearer OCR'
            })

        elif category == FailureCategory.INCOMPLETE_CROP:
            actions.append({
                'parameter': 'bbox_expansion',
                'current': {'left': 180, 'right': 20, 'top': 20, 'bottom': 20},
                'new': {'left': 250, 'right': 50, 'top': 30, 'bottom': 30},
                'reason': 'Expand bounding box to capture full equation'
            })

        elif category == FailureCategory.BACKGROUND_NOISE:
            actions.append({
                'parameter': 'bbox_refinement',
                'current': 'off',
                'new': 'text_density_filtering',
                'reason': 'Filter surrounding text from equation crop'
            })

        elif category == FailureCategory.SPACING_ISSUES:
            actions.append({
                'parameter': 'ocr_model',
                'current': 'pix2tex_default',
                'new': 'pix2tex_spacing_aware',
                'reason': 'Use OCR model with better spacing handling'
            })

        elif category == FailureCategory.COMPLEX_STRUCTURE:
            actions.append({
                'parameter': 'adaptive_sizing',
                'current': 'fixed_40px',
                'new': 'complexity_based',
                'reason': 'Use smart multi-line detection for complex equations'
            })

        elif category == FailureCategory.SYMBOL_MISRECOGNITION:
            actions.append({
                'parameter': 'ocr_model',
                'current': 'pix2tex',
                'new': 'mathpix_api',
                'reason': 'Switch to more accurate OCR for difficult symbols'
            })

        return actions


class ReextractionController:
    """
    Controls the re-extraction feedback loop for failed equations.

    Quality-first approach:
    1. Analyze failure pattern
    2. Adjust extraction parameters
    3. Re-extract equation
    4. Validate improvement
    5. Iterate until success or max attempts
    """

    def __init__(
        self,
        max_attempts: int = 3,
        quality_threshold: float = 0.8,
        output_dir: Path = None
    ):
        self.max_attempts = max_attempts
        self.quality_threshold = quality_threshold
        self.output_dir = output_dir or Path('results/reextraction')
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.validator = LaTeXQualityValidator()
        self.analyzer = FailurePatternAnalyzer()

        self.reextraction_history: Dict[str, List[ReextractionAttempt]] = {}

    def process_failed_equation(
        self,
        equation: Dict,
        error_message: str,
        original_image_path: Path
    ) -> Optional[Dict]:
        """
        Process a failed equation through the re-extraction feedback loop.

        Args:
            equation: Original equation dict
            error_message: SymPy parsing error
            original_image_path: Path to original equation crop image

        Returns:
            Enhanced equation dict if successful, None if all attempts failed
        """
        eq_id = equation.get('equation_number', 'unknown')
        print(f"\n🔄 Processing failed equation {eq_id}")

        # Analyze failure
        analysis = self.analyzer.analyze(equation, error_message)
        print(f"   Diagnosis: {analysis.category.value} (confidence: {analysis.confidence:.2f})")
        print(f"   Evidence: {', '.join(analysis.evidence[:2])}")

        # Check if fixable
        if analysis.category == FailureCategory.UNFIXABLE:
            print(f"   ⚠️  Not fixable via re-extraction - {analysis.evidence[0]}")
            return None

        if not analysis.recommended_actions:
            print(f"   ⚠️  No extraction adjustments available")
            return None

        # Initialize re-extraction history
        self.reextraction_history[eq_id] = []

        # Attempt re-extraction with adjusted parameters
        for attempt_num in range(1, self.max_attempts + 1):
            print(f"\n   Attempt {attempt_num}/{self.max_attempts}:")

            # Get parameters for this attempt
            params = self._get_attempt_parameters(analysis, attempt_num)
            print(f"   Parameters: {params}")

            # Re-extract equation (this would call back to extraction agent)
            # For now, we'll simulate by documenting what WOULD happen
            new_equation = self._simulate_reextraction(
                equation,
                original_image_path,
                params
            )

            # Validate new extraction
            success, error = self.validator.validate(new_equation['latex'])

            # Record attempt
            attempt = ReextractionAttempt(
                attempt_number=attempt_num,
                parameters=params,
                success=success,
                new_latex=new_equation['latex'] if success else None,
                parse_result=new_equation if success else None,
                improvements=self._identify_improvements(equation['latex'], new_equation['latex'])
            )
            self.reextraction_history[eq_id].append(attempt)

            if success:
                print(f"   ✅ Success! Improvements: {', '.join(attempt.improvements)}")
                return new_equation
            else:
                print(f"   ❌ Still failed: {error[:100]}")

        print(f"   ⚠️  Max attempts reached without success")
        return None

    def _get_attempt_parameters(
        self,
        analysis: FailureAnalysis,
        attempt_num: int
    ) -> Dict[str, any]:
        """
        Get extraction parameters for this attempt.
        Progressively applies more aggressive adjustments.
        """
        base_params = {
            'dpi': 216,
            'bbox_left': 180,
            'bbox_right': 20,
            'bbox_top': 20,
            'bbox_bottom': 20,
            'ocr_model': 'pix2tex',
        }

        # Apply recommended actions
        for action in analysis.recommended_actions[:attempt_num]:
            param = action['parameter']
            new_value = action['new']

            if param == 'dpi':
                base_params['dpi'] = new_value
            elif param == 'bbox_expansion':
                base_params.update({
                    'bbox_left': new_value['left'],
                    'bbox_right': new_value['right'],
                    'bbox_top': new_value['top'],
                    'bbox_bottom': new_value['bottom'],
                })
            elif param == 'ocr_model':
                base_params['ocr_model'] = new_value

        return base_params

    def _simulate_reextraction(
        self,
        original_equation: Dict,
        image_path: Path,
        params: Dict
    ) -> Dict:
        """
        Simulate re-extraction with new parameters.

        In production, this would:
        1. Re-crop PDF with adjusted bbox
        2. Re-run LaTeX OCR with new settings
        3. Return new equation dict

        For now, we document the process.
        """
        # This is where we'd integrate with the actual extraction pipeline
        # For demonstration, we'll return a mock improved version

        print(f"   📸 Would re-crop equation with params: {params}")
        print(f"   🔍 Would re-run OCR with model: {params['ocr_model']}")

        # Return original for now (in production, this returns re-extracted LaTeX)
        return original_equation

    def _identify_improvements(self, old_latex: str, new_latex: str) -> List[str]:
        """Identify what improved between old and new extraction"""
        improvements = []

        if len(new_latex) > len(old_latex):
            improvements.append("More complete equation")

        if old_latex.count('\\\ ') > new_latex.count('\\\ '):
            improvements.append("Reduced spacing artifacts")

        if re.search(r'[^\x00-\x7F]', old_latex) and not re.search(r'[^\x00-\x7F]', new_latex):
            improvements.append("Fixed non-ASCII characters")

        return improvements or ["Minor refinements"]

    def generate_reextraction_report(self, output_path: Path):
        """Generate comprehensive report of all re-extraction attempts"""

        report = {
            'summary': {
                'total_equations_processed': len(self.reextraction_history),
                'successful_reextractions': sum(
                    1 for attempts in self.reextraction_history.values()
                    if any(a.success for a in attempts)
                ),
                'failed_after_all_attempts': sum(
                    1 for attempts in self.reextraction_history.values()
                    if not any(a.success for a in attempts)
                ),
                'total_attempts': sum(
                    len(attempts) for attempts in self.reextraction_history.values()
                ),
            },
            'details': {}
        }

        for eq_id, attempts in self.reextraction_history.items():
            report['details'][eq_id] = [
                {
                    'attempt': a.attempt_number,
                    'success': a.success,
                    'parameters': a.parameters,
                    'improvements': a.improvements
                }
                for a in attempts
            ]

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📊 Re-extraction report saved: {output_path}")


def main():
    """
    Demonstration of LaTeX Quality Control Agent with Re-extraction Feedback Loop.

    This shows how the agent would process failed equations from the baseline SymPy run.
    """
    print("="*80)
    print("LaTeX QUALITY CONTROL AGENT - Re-extraction Feedback Loop")
    print("="*80)

    # Load baseline results
    baseline_dir = Path('results/sympy_baseline')
    equations_file = baseline_dir / 'equations_enhanced.json'

    if not equations_file.exists():
        print(f"❌ Baseline results not found: {equations_file}")
        return

    with open(equations_file, 'r', encoding='utf-8') as f:
        equations = json.load(f)

    # Filter to failed equations
    failed = [eq for eq in equations if not eq.get('sympy_parse_success', False)]

    print(f"\n📊 Found {len(failed)} failed equations from baseline run")
    print(f"   Will analyze and attempt re-extraction for fixable failures")

    # Initialize controller
    controller = ReextractionController(
        max_attempts=3,
        output_dir=Path('results/reextraction')
    )

    # Process first 5 failed equations as demonstration
    demo_equations = failed[:5]

    print(f"\n🔬 Processing {len(demo_equations)} equations as demonstration")

    successes = 0
    for eq in demo_equations:
        # Get original image path
        eq_num = eq.get('equation_number', 'unknown')
        page = eq.get('page', 0)
        image_path = Path(f'extractions/doclayout_equations/eq_{eq_num}_page{page}.png')

        error = eq.get('parse_error', 'Unknown error')

        # Process through feedback loop
        result = controller.process_failed_equation(eq, error, image_path)

        if result:
            successes += 1

    print(f"\n" + "="*80)
    print(f"DEMONSTRATION RESULTS")
    print(f"="*80)
    print(f"Processed: {len(demo_equations)} equations")
    print(f"Successful re-extractions: {successes}")
    print(f"Still failed: {len(demo_equations) - successes}")

    # Generate report
    report_path = controller.output_dir / 'reextraction_report.json'
    controller.generate_reextraction_report(report_path)

    print(f"\n💡 NEXT STEPS:")
    print(f"   1. Integrate with actual extraction pipeline")
    print(f"   2. Implement parameter adjustments in extraction agents")
    print(f"   3. Run full re-extraction loop on all {len(failed)} failed equations")
    print(f"   4. Measure improvement in parse success rate")


if __name__ == "__main__":
    main()
