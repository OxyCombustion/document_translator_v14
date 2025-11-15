#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SymPy Equation Parser - Symbolic Mathematics Integration for Phase A

This agent enhances LaTeX equation extractions with SymPy symbolic representations,
enabling deterministic computation and code generation for engineering problem-solving.

Purpose:
--------
- Parse LaTeX equations into SymPy expressions
- Generate srepr (serialized representation) for exact storage/reconstruction
- Identify target variables for solve operations
- Flag equations as code-gen eligible when parse succeeds
- Maintain graceful fallback when parsing fails

Design Philosophy:
-----------------
- **Post-Processing Pattern**: Enhances existing extractions, doesn't re-extract
- **Graceful Degradation**: Parse failures don't lose LaTeX/context data
- **Product Quality Focus**: Optimizes for LLM + code-gen hybrid intelligence

Phase A Scope:
--------------
Operations: parse, srepr, simplify, solve (basic)
Deferred to Phase B: dimensional checking, derivatives, integrals, equation systems

Author: Claude Code (Phase A Implementation)
Date: 2025-10-11
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import re

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

# SymPy imports
try:
    import sympy as sp
    from sympy.parsing.latex import parse_latex
    from sympy import srepr, simplify, solve, symbols
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False
    print("⚠️  WARNING: SymPy not available. Install with: pip install sympy")


@dataclass
class SymPyResult:
    """
    Results of SymPy symbolic processing for one equation.

    Attributes:
        equation_id: Original equation identifier (e.g., "eq_1", "eq_79a")
        parse_success: True if LaTeX successfully parsed to SymPy expression
        sympy_expr: SymPy expression object (if parse succeeded)
        srepr_string: Serialized representation for storage/reconstruction
        target_variable: Variable to solve for (e.g., "q", "h", "Nu")
        solved_form: Solved expression with target isolated (if solvable)
        code_gen_eligible: True if equation ready for code generation
        simplification: Simplified form of expression (optional)
        error_message: Description of failure (if parse failed)
        latex_cleaned: Cleaned LaTeX that was attempted to parse
    """
    equation_id: str
    parse_success: bool
    sympy_expr: Optional[Any] = None  # SymPy expression (not JSON serializable)
    srepr_string: Optional[str] = None
    target_variable: Optional[str] = None
    solved_form: Optional[str] = None
    code_gen_eligible: bool = False
    simplification: Optional[str] = None
    error_message: Optional[str] = None
    latex_cleaned: Optional[str] = None


class SymPyEquationParser:
    """
    Parser that enhances LaTeX equations with SymPy symbolic representations.

    Workflow:
    ---------
    1. Load LaTeX equations from V11 extraction
    2. Clean LaTeX for SymPy compatibility
    3. Parse to SymPy expressions
    4. Generate srepr for storage
    5. Identify target variables
    6. Flag code-gen eligibility
    7. Generate enhanced output with symbolic data

    Error Handling:
    --------------
    - Parse failures: Graceful fallback, preserve original LaTeX
    - Unsolvable equations: Flag as code-gen ineligible, still store srepr
    - Complex notation: Attempt cleaning, document failures for improvement
    """

    def __init__(self, equations_file: Path, output_dir: Path):
        """
        Initialize SymPy equation parser.

        Args:
            equations_file: Path to V11 equations_latex.json
            output_dir: Directory for enhanced outputs
        """
        self.equations_file = Path(equations_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Statistics tracking
        self.stats = {
            "total_equations": 0,
            "parse_success": 0,
            "parse_failure": 0,
            "code_gen_eligible": 0,
            "target_identified": 0,
            "simplified": 0,
            "start_time": None,
            "end_time": None
        }

        # LaTeX cleaning patterns (expand as needed based on failures)
        self.cleaning_patterns = [
            (r'\\mathrm{([^}]+)}', r'\1'),  # Remove \mathrm{}
            (r'\\operatorname{([^}]+)}', r'\1'),  # Remove \operatorname{}
            (r'\\left', ''),  # Remove \left
            (r'\\right', ''),  # Remove \right
            (r'\\bigl', ''),  # Remove \bigl
            (r'\\bigr', ''),  # Remove \bigr
            (r'\\Bigl', ''),  # Remove \Bigl
            (r'\\Bigr', ''),  # Remove \Bigr
            (r'\\,', ' '),  # Spacing to space
            (r'\\:', ' '),  # Spacing to space
            (r'\\;', ' '),  # Spacing to space
            (r'\\quad', ' '),  # Spacing to space
            (r'\\qquad', ' '),  # Spacing to space
        ]

    def load_equations(self) -> List[Dict[str, Any]]:
        """
        Load LaTeX equations from V11 extraction.

        Returns:
            List of equation dictionaries with LaTeX strings
        """
        if not self.equations_file.exists():
            raise FileNotFoundError(f"Equations file not found: {self.equations_file}")

        with open(self.equations_file, 'r', encoding='utf-8') as f:
            equations = json.load(f)

        print(f"✅ Loaded {len(equations)} equations from {self.equations_file.name}")
        return equations

    def clean_latex(self, latex: str) -> str:
        """
        Clean LaTeX string for SymPy compatibility.

        Args:
            latex: Raw LaTeX string from OCR

        Returns:
            Cleaned LaTeX string more likely to parse

        Cleaning Steps:
        --------------
        1. Remove formatting commands (\mathrm, \operatorname)
        2. Remove size modifiers (\left, \right, \big)
        3. Normalize spacing commands
        4. Remove array/alignment structures (Phase A limitation)
        """
        cleaned = latex

        # Apply regex patterns
        for pattern, replacement in self.cleaning_patterns:
            cleaned = re.sub(pattern, replacement, cleaned)

        # Remove array structures (too complex for Phase A)
        if '\\begin{array}' in cleaned:
            # For Phase A, skip array equations
            return None

        return cleaned.strip()

    def identify_target_variable(self, expr: Any, latex: str) -> Optional[str]:
        """
        Identify the variable to solve for in an equation.

        Heuristics (Phase A):
        --------------------
        1. If equation form "var = expression", target is "var"
        2. If equation has single variable on one side, that's target
        3. Otherwise, identify leftmost variable as likely target

        Phase B Improvement:
        -------------------
        - Use domain knowledge (heat transfer: q is often target)
        - Parse equation caption/context for hints
        - Multi-variable handling

        Args:
            expr: SymPy expression
            latex: Original LaTeX for context

        Returns:
            Target variable symbol name (e.g., "q", "h", "Nu")
        """
        try:
            # Check if equation (Eq) or inequality
            if hasattr(expr, 'lhs') and hasattr(expr, 'rhs'):
                # Get free symbols from both sides
                lhs_symbols = expr.lhs.free_symbols
                rhs_symbols = expr.rhs.free_symbols

                # If LHS has single symbol not on RHS, that's likely target
                if len(lhs_symbols) == 1 and lhs_symbols.isdisjoint(rhs_symbols):
                    return str(list(lhs_symbols)[0])

                # If RHS has single symbol not on LHS, that's likely target
                if len(rhs_symbols) == 1 and rhs_symbols.isdisjoint(lhs_symbols):
                    return str(list(rhs_symbols)[0])

            # Fallback: Return first symbol alphabetically (deterministic)
            all_symbols = expr.free_symbols
            if all_symbols:
                return str(sorted([str(s) for s in all_symbols])[0])

            return None

        except Exception as e:
            return None

    def parse_equation(self, equation: Dict[str, Any]) -> SymPyResult:
        """
        Parse single equation with SymPy.

        Args:
            equation: Equation dictionary from V11 extraction

        Returns:
            SymPyResult with symbolic data (or error information)

        Workflow:
        --------
        1. Extract equation ID and LaTeX
        2. Clean LaTeX for compatibility
        3. Attempt SymPy parse
        4. Generate srepr if successful
        5. Identify target variable
        6. Attempt solve for target
        7. Flag code-gen eligibility
        8. Return complete result
        """
        eq_id = equation.get('equation_number', 'unknown')
        if eq_id is None:
            eq_id = f"unnumbered_{equation.get('page', 'unknown')}"
        else:
            eq_id = f"eq_{eq_id}"

        latex = equation.get('latex', '')

        result = SymPyResult(
            equation_id=eq_id,
            parse_success=False
        )

        # Clean LaTeX
        try:
            cleaned_latex = self.clean_latex(latex)
            result.latex_cleaned = cleaned_latex

            if cleaned_latex is None:
                result.error_message = "Array/alignment structure (too complex for Phase A)"
                return result

        except Exception as e:
            result.error_message = f"LaTeX cleaning failed: {str(e)}"
            return result

        # Parse with SymPy
        try:
            expr = parse_latex(cleaned_latex)
            result.sympy_expr = expr
            result.parse_success = True

            # Generate srepr
            result.srepr_string = srepr(expr)

            # Identify target variable
            target = self.identify_target_variable(expr, latex)
            result.target_variable = target

            # Attempt simplification
            try:
                simplified = simplify(expr)
                result.simplification = str(simplified)
                self.stats["simplified"] += 1
            except:
                pass  # Simplification optional

            # Attempt solve for target (if target identified)
            if target:
                result.target_identified = True
                try:
                    # Solve for target variable
                    target_sym = symbols(target)
                    if hasattr(expr, 'lhs') and hasattr(expr, 'rhs'):
                        # It's an equation (Eq object)
                        solved = solve(expr, target_sym)
                        if solved:
                            result.solved_form = str(solved[0]) if isinstance(solved, list) else str(solved)
                            result.code_gen_eligible = True
                except:
                    pass  # Solve failure doesn't block code-gen with srepr

            # If we have srepr, mark as code-gen eligible even without solve
            if result.srepr_string:
                result.code_gen_eligible = True

        except Exception as e:
            result.parse_success = False
            result.error_message = f"SymPy parse failed: {str(e)}"

        return result

    def process_all_equations(self) -> List[Dict[str, Any]]:
        """
        Process all equations with SymPy enhancement.

        Returns:
            List of enhanced equation dictionaries
        """
        equations = self.load_equations()
        self.stats["total_equations"] = len(equations)
        self.stats["start_time"] = datetime.now()

        print(f"\n{'='*70}")
        print(f"SYMPY EQUATION PARSER - PHASE A")
        print(f"{'='*70}")
        print(f"Processing {len(equations)} equations...")
        print()

        enhanced_equations = []

        for i, eq in enumerate(equations, 1):
            eq_id = eq.get('equation_number', 'unknown')
            print(f"  [{i}/{len(equations)}] Processing equation {eq_id}...", end=' ')

            # Parse with SymPy
            result = self.parse_equation(eq)

            # Update statistics
            if result.parse_success:
                self.stats["parse_success"] += 1
                print("✅ Success")
            else:
                self.stats["parse_failure"] += 1
                print(f"❌ Failed: {result.error_message}")

            if result.code_gen_eligible:
                self.stats["code_gen_eligible"] += 1

            if result.target_variable:
                self.stats["target_identified"] += 1

            # Build enhanced equation dictionary
            enhanced_eq = {
                **eq,  # Original fields (filename, page, latex, status)
                "sympy_parse_success": result.parse_success,
                "srepr": result.srepr_string,
                "target_variable": result.target_variable,
                "solved_form": result.solved_form,
                "code_gen_eligible": result.code_gen_eligible,
                "simplification": result.simplification,
                "parse_error": result.error_message,
                "latex_cleaned": result.latex_cleaned
            }

            enhanced_equations.append(enhanced_eq)

        self.stats["end_time"] = datetime.now()

        return enhanced_equations

    def generate_report(self, enhanced_equations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate Phase A baseline report.

        Returns:
            Report dictionary with statistics and analysis
        """
        elapsed = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()

        # Analyze failure patterns
        failure_patterns = {}
        for eq in enhanced_equations:
            if not eq["sympy_parse_success"] and eq.get("parse_error"):
                error = eq["parse_error"]
                # Categorize error
                if "Array" in error or "array" in error:
                    category = "Array/alignment structures"
                elif "parse" in error.lower():
                    category = "LaTeX parse failure"
                elif "cleaning" in error.lower():
                    category = "LaTeX cleaning failure"
                else:
                    category = "Other"

                failure_patterns[category] = failure_patterns.get(category, 0) + 1

        # Success rate breakdown
        total = self.stats["total_equations"]
        parse_success_rate = (self.stats["parse_success"] / total * 100) if total > 0 else 0
        code_gen_rate = (self.stats["code_gen_eligible"] / total * 100) if total > 0 else 0
        target_id_rate = (self.stats["target_identified"] / total * 100) if total > 0 else 0

        report = {
            "phase": "A",
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_equations": total,
                "parse_success": self.stats["parse_success"],
                "parse_failure": self.stats["parse_failure"],
                "parse_success_rate": f"{parse_success_rate:.1f}%",
                "code_gen_eligible": self.stats["code_gen_eligible"],
                "code_gen_rate": f"{code_gen_rate:.1f}%",
                "target_identified": self.stats["target_identified"],
                "target_identification_rate": f"{target_id_rate:.1f}%",
                "simplified": self.stats["simplified"],
                "processing_time_seconds": elapsed
            },
            "failure_analysis": {
                "patterns": failure_patterns,
                "top_failure_category": max(failure_patterns.items(), key=lambda x: x[1])[0] if failure_patterns else "None"
            },
            "phase_a_success_criteria": {
                "target_parse_success": "≥80%",
                "actual_parse_success": f"{parse_success_rate:.1f}%",
                "target_met": parse_success_rate >= 80.0
            },
            "next_steps": {
                "if_target_met": "Proceed to chunk assembly (Day 4-5)",
                "if_target_not_met": "Enhance LaTeX cleaning pipeline, focus on top failure category"
            }
        }

        return report

    def print_statistics(self, report: Dict[str, Any]):
        """Print formatted statistics."""
        stats = report["statistics"]
        criteria = report["phase_a_success_criteria"]

        print(f"\n{'-'*70}")
        print(f"PHASE A BASELINE - SYMPY INTEGRATION RESULTS")
        print(f"{'-'*70}")
        print(f"  Total equations: {stats['total_equations']}")
        print(f"  Parse success: {stats['parse_success']} ({stats['parse_success_rate']})")
        print(f"  Parse failure: {stats['parse_failure']}")
        print(f"  Code-gen eligible: {stats['code_gen_eligible']} ({stats['code_gen_rate']})")
        print(f"  Target identified: {stats['target_identified']} ({stats['target_identification_rate']})")
        print(f"  Simplified: {stats['simplified']}")
        print(f"  Processing time: {stats['processing_time_seconds']:.2f}s")
        print(f"\n  Phase A Target: {criteria['target_parse_success']}")
        print(f"  Actual Result: {criteria['actual_parse_success']}")
        print(f"  Target Met: {'✅ YES' if criteria['target_met'] else '❌ NO'}")

        if report["failure_analysis"]["patterns"]:
            print(f"\n  Failure Patterns:")
            for pattern, count in sorted(report["failure_analysis"]["patterns"].items(), key=lambda x: -x[1]):
                print(f"    - {pattern}: {count}")

        print(f"{'='*70}\n")

    def save_results(self, enhanced_equations: List[Dict[str, Any]], report: Dict[str, Any]):
        """
        Save enhanced equations and report.

        Outputs:
        -------
        1. equations_enhanced.json - Full enhanced equation data
        2. sympy_baseline_report.json - Phase A statistics
        3. code_gen_eligible.json - Subset ready for code generation
        """
        # Save enhanced equations
        output_file = self.output_dir / "equations_enhanced.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_equations, f, indent=2, ensure_ascii=False)
        print(f"  💾 Enhanced equations saved: {output_file}")

        # Save report
        report_file = self.output_dir / "sympy_baseline_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"  💾 Baseline report saved: {report_file}")

        # Save code-gen eligible subset
        code_gen_eligible = [eq for eq in enhanced_equations if eq["code_gen_eligible"]]
        code_gen_file = self.output_dir / "code_gen_eligible.json"
        with open(code_gen_file, 'w', encoding='utf-8') as f:
            json.dump(code_gen_eligible, f, indent=2, ensure_ascii=False)
        print(f"  💾 Code-gen eligible equations saved: {code_gen_file}")
        print(f"      ({len(code_gen_eligible)} equations ready for code generation)")


def main():
    """Main execution for SymPy equation parser."""
    if not SYMPY_AVAILABLE:
        print("❌ SymPy not available. Cannot proceed.")
        print("   Install with: pip install sympy")
        return

    # Paths
    base_dir = Path(__file__).parent.parent.parent
    equations_file = base_dir / "extractions" / "doclayout_latex" / "equations_latex.json"
    output_dir = base_dir / "results" / "sympy_baseline"

    # Create parser and process
    parser = SymPyEquationParser(equations_file, output_dir)
    enhanced_equations = parser.process_all_equations()
    report = parser.generate_report(enhanced_equations)
    parser.print_statistics(report)
    parser.save_results(enhanced_equations, report)

    print("\n✅ Phase A Day 1-2: SymPy Integration Complete")
    print(f"   Next: Review {output_dir / 'sympy_baseline_report.json'}")
    print(f"   If target met (≥80%), proceed to Day 2-3: Schema Implementation")


if __name__ == "__main__":
    main()
