# -*- coding: utf-8 -*-
"""
Computational Code Generator Agent - Mathematica and Python Code Generation

This agent generates executable code for computational equations:
- Mathematica functions with documentation
- Python functions with NumPy/SciPy
- Test cases for validation

Author: Document Translator V11 System
Date: 2025-10-09
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CodeGenerationResult:
    """Result of code generation for a single equation."""
    equation_number: str
    success: bool
    mathematica_code: Optional[str]
    python_code: Optional[str]
    test_cases: List[Dict]
    errors: List[str]
    warnings: List[str]


class ComputationalCodeGeneratorAgent:
    """
    Generate executable code for computational equations.

    Converts LaTeX equations to:
    1. Mathematica functions with documentation
    2. Python functions with type hints and NumPy docstrings
    3. Test cases with sample inputs
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the code generator.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or self._default_config()
        self._init_latex_to_code_mappings()

    def _default_config(self) -> Dict:
        """Default configuration."""
        return {
            'mathematica': {
                'use_symbolic': True,
                'add_assumptions': True,
                'add_documentation': True
            },
            'python': {
                'use_numpy': True,
                'add_type_hints': True,
                'add_docstrings': True
            },
            'test_cases': {
                'generate_automatic': True,
                'num_test_cases': 3
            }
        }

    def _init_latex_to_code_mappings(self):
        """Initialize LaTeX to code translation mappings."""

        # Common mathematical function mappings
        self.latex_to_mathematica = {
            r'\\frac{([^}]+)}{([^}]+)}': r'(\1)/(\2)',
            r'\\sqrt{([^}]+)}': r'Sqrt[\1]',
            r'\\sin': 'Sin',
            r'\\cos': 'Cos',
            r'\\tan': 'Tan',
            r'\\exp': 'Exp',
            r'\\log': 'Log',
            r'\\ln': 'Log',
            r'\\pi': 'Pi',
            r'\\sigma': 'σ',  # Stefan-Boltzmann constant or property
            r'\\varepsilon': 'ε',
            r'\\alpha': 'α',
            r'\\rho': 'ρ',
            r'\\mu': 'μ',
            r'\\Delta': 'Δ',
            r'\\nabla': 'Nabla',
            r'\^{([^}]+)}': '^(\1)',
            r'_\{([^}]+)\}': '_(\1)'
        }

        self.latex_to_python = {
            r'\\frac{([^}]+)}{([^}]+)}': r'((\1)/(\2))',
            r'\\sqrt{([^}]+)}': r'np.sqrt(\1)',
            r'\\sin': 'np.sin',
            r'\\cos': 'np.cos',
            r'\\tan': 'np.tan',
            r'\\exp': 'np.exp',
            r'\\log': 'np.log',
            r'\\ln': 'np.log',
            r'\\pi': 'np.pi',
            r'\^{([^}]+)}': '**(\1)',
            r'_\{([^}]+)\}': '_\1'  # Convert subscripts to variable suffixes
        }

        # Known constants in heat transfer
        self.known_constants = {
            'sigma': {
                'mathematica': 'StefanBoltzmannConstant',
                'python': '5.670374419e-8',  # W/(m²·K⁴)
                'description': 'Stefan-Boltzmann constant'
            },
            'g': {
                'mathematica': '9.81',
                'python': '9.81',
                'description': 'Gravitational acceleration (m/s²)'
            },
            'pi': {
                'mathematica': 'Pi',
                'python': 'np.pi',
                'description': 'Pi constant'
            }
        }

    def generate_code(self, equation: Dict, classification_data: Dict) -> CodeGenerationResult:
        """
        Generate Mathematica and Python code for an equation.

        Args:
            equation: Original equation dictionary with LaTeX
            classification_data: Classification results with features

        Returns:
            CodeGenerationResult with generated code
        """
        eq_num = equation.get('equation_number', 'unknown')
        latex = equation.get('latex', '')

        errors = []
        warnings = []

        # Extract variable information from classification
        features = classification_data.get('features', {})
        symbols = features.get('symbols', {})

        output_var = symbols.get('output_variable')
        input_vars = symbols.get('input_variables', [])

        if not output_var:
            errors.append("No output variable identified")
            return CodeGenerationResult(
                equation_number=eq_num,
                success=False,
                mathematica_code=None,
                python_code=None,
                test_cases=[],
                errors=errors,
                warnings=warnings
            )

        # Generate Mathematica code
        mathematica_code = self._generate_mathematica(
            eq_num, latex, output_var, input_vars
        )

        # Generate Python code
        python_code = self._generate_python(
            eq_num, latex, output_var, input_vars
        )

        # Generate test cases
        test_cases = self._generate_test_cases(
            eq_num, output_var, input_vars
        )

        return CodeGenerationResult(
            equation_number=eq_num,
            success=True,
            mathematica_code=mathematica_code,
            python_code=python_code,
            test_cases=test_cases,
            errors=errors,
            warnings=warnings
        )

    def _generate_mathematica(
        self,
        eq_num: str,
        latex: str,
        output_var: str,
        input_vars: List[str]
    ) -> str:
        """
        Generate Mathematica function code.

        Args:
            eq_num: Equation number
            latex: LaTeX equation string
            output_var: Output variable name
            input_vars: List of input variable names

        Returns:
            Mathematica function code as string
        """
        # Parse equation (split on =)
        if '=' not in latex:
            return f"(* Error: Equation {eq_num} has no equals sign *)"

        parts = latex.split('=', 1)
        if len(parts) != 2:
            return f"(* Error: Equation {eq_num} has multiple equals signs *)"

        left, right = parts[0].strip(), parts[1].strip()

        # Convert LaTeX to Mathematica syntax
        expression = self._latex_to_mathematica_expr(right)

        # Clean input variable names
        clean_inputs = [self._clean_variable_name(v) for v in input_vars if v]
        clean_inputs = [v for v in clean_inputs if v and len(v) > 0]

        if not clean_inputs:
            clean_inputs = ['x']  # Fallback

        # Generate function name
        func_name = f"Equation{eq_num}".replace('-', '').replace('.', '_')

        # Build Mathematica function
        params = ', '.join([f"{v}_" for v in clean_inputs])

        code = f"""(* Equation {eq_num}: {latex[:60]}... *)
{func_name}[{params}] := Module[{{}},
  (* Heat transfer calculation *)
  {expression}
]

(* Usage example *)
(* result = {func_name}[{', '.join(['value' + str(i+1) for i in range(len(clean_inputs))])}] *)
"""

        return code

    def _generate_python(
        self,
        eq_num: str,
        latex: str,
        output_var: str,
        input_vars: List[str]
    ) -> str:
        """
        Generate Python function code.

        Args:
            eq_num: Equation number
            latex: LaTeX equation string
            output_var: Output variable name
            input_vars: List of input variable names

        Returns:
            Python function code as string
        """
        # Parse equation
        if '=' not in latex:
            return f"# Error: Equation {eq_num} has no equals sign"

        parts = latex.split('=', 1)
        if len(parts) != 2:
            return f"# Error: Equation {eq_num} has multiple equals signs"

        left, right = parts[0].strip(), parts[1].strip()

        # Convert LaTeX to Python syntax
        expression = self._latex_to_python_expr(right)

        # Clean input variable names
        clean_inputs = [self._clean_variable_name(v) for v in input_vars if v]
        clean_inputs = [v for v in clean_inputs if v and len(v) > 0]

        if not clean_inputs:
            clean_inputs = ['x']  # Fallback

        # Generate function name
        func_name = f"equation_{eq_num}".replace('-', '_').replace('.', '_')

        # Build Python function with type hints
        params = ', '.join([f"{v}: float" for v in clean_inputs])

        code = f"""def {func_name}({params}) -> float:
    \"\"\"
    Equation {eq_num}: {latex[:60]}...

    Args:
        {chr(10).join([f"{v}: {v.upper()} parameter" for v in clean_inputs])}

    Returns:
        Calculated value

    Example:
        >>> result = {func_name}({', '.join(['1.0' for _ in clean_inputs])})
    \"\"\"
    import numpy as np

    result = {expression}
    return result
"""

        return code

    def _latex_to_mathematica_expr(self, latex: str) -> str:
        """Convert LaTeX expression to Mathematica syntax."""
        expr = latex

        # Apply transformation rules
        for pattern, replacement in self.latex_to_mathematica.items():
            expr = re.sub(pattern, replacement, expr)

        # Clean up LaTeX artifacts
        expr = self._clean_latex_artifacts(expr)

        # Replace known constants
        for const, info in self.known_constants.items():
            if const in expr:
                expr = expr.replace(const, info['mathematica'])

        return expr

    def _latex_to_python_expr(self, latex: str) -> str:
        """Convert LaTeX expression to Python/NumPy syntax."""
        expr = latex

        # Apply transformation rules
        for pattern, replacement in self.latex_to_python.items():
            expr = re.sub(pattern, replacement, expr)

        # Clean up LaTeX artifacts
        expr = self._clean_latex_artifacts(expr)

        # Replace known constants
        for const, info in self.known_constants.items():
            if const in expr:
                expr = expr.replace(const, info['python'])

        # Replace multiplication signs
        expr = expr.replace('\\times', '*')
        expr = expr.replace('\\cdot', '*')

        return expr

    def _clean_latex_artifacts(self, expr: str) -> str:
        """Remove LaTeX formatting artifacts."""
        # Remove common LaTeX commands
        artifacts = [
            r'\\left', r'\\right', r'\\big', r'\\Big',
            r'\\bigg', r'\\Bigg', r'\\,', r'\\:', r'\\;',
            r'\\!', r'\\quad', r'\\qquad', r'\\phantom'
        ]

        for artifact in artifacts:
            expr = expr.replace(artifact, '')

        # Remove curly braces that aren't needed
        expr = re.sub(r'\{([^{}]*)\}', r'\1', expr)

        return expr.strip()

    def _clean_variable_name(self, var: str) -> str:
        """Clean variable name for use in code."""
        # Remove LaTeX artifacts
        clean = re.sub(r'\\[a-zA-Z]+', '', var)
        clean = re.sub(r'[{}]', '', clean)
        clean = re.sub(r'[^a-zA-Z0-9_]', '_', clean)

        # Ensure it starts with a letter
        if clean and not clean[0].isalpha():
            clean = 'var_' + clean

        return clean if clean else 'x'

    def _generate_test_cases(
        self,
        eq_num: str,
        output_var: str,
        input_vars: List[str]
    ) -> List[Dict]:
        """
        Generate test cases for the equation.

        Args:
            eq_num: Equation number
            output_var: Output variable name
            input_vars: List of input variable names

        Returns:
            List of test case dictionaries
        """
        test_cases = []

        # Generate simple test cases with representative values
        test_values = [
            [1.0] * len(input_vars),
            [10.0] * len(input_vars),
            [100.0] * len(input_vars)
        ]

        for i, values in enumerate(test_values, 1):
            test_case = {
                'case_number': i,
                'description': f'Test case {i} for equation {eq_num}',
                'inputs': {var: val for var, val in zip(input_vars, values)},
                'expected_output': None,  # Will be calculated when code is executed
                'notes': 'Automatically generated test case'
            }
            test_cases.append(test_case)

        return test_cases


def main():
    """Test the code generator on sample equations."""
    print("ComputationalCodeGeneratorAgent - Test Run\n")
    print("="*60)

    # Load sample computational equation
    sample_equation = {
        'equation_number': '11',
        'latex': 'q_{12}\\;=\\;A_{1}\\:F_{12}\\:\\sigma\\:\\left(\\!\\:T_{1}^{4}\\:-\\:T_{2}^{4}\\right)',
        'status': 'success'
    }

    sample_classification = {
        'features': {
            'symbols': {
                'output_variable': 'q_{12}',
                'input_variables': ['A_{1}', 'F_{12}', 'sigma', 'T_{1}', 'T_{2}'],
                'has_heat_transfer_symbol': True
            }
        }
    }

    generator = ComputationalCodeGeneratorAgent()
    result = generator.generate_code(sample_equation, sample_classification)

    print(f"Equation {result.equation_number}")
    print(f"Success: {result.success}\n")

    if result.mathematica_code:
        print("MATHEMATICA CODE:")
        # Replace Unicode characters with ASCII for console output
        code_ascii = result.mathematica_code.replace('σ', 'sigma').replace('ε', 'epsilon').replace('α', 'alpha').replace('ρ', 'rho').replace('μ', 'mu').replace('Δ', 'Delta')
        print(code_ascii)
        print()

    if result.python_code:
        print("PYTHON CODE:")
        # Replace Unicode characters with ASCII for console output
        code_ascii = result.python_code.replace('σ', 'sigma').replace('ε', 'epsilon').replace('α', 'alpha').replace('ρ', 'rho').replace('μ', 'mu').replace('Δ', 'Delta')
        print(code_ascii)
        print()

    if result.test_cases:
        print(f"TEST CASES: {len(result.test_cases)} generated")
        for test in result.test_cases:
            print(f"  - {test['description']}")

    print("\n" + "="*60)


if __name__ == '__main__':
    main()
