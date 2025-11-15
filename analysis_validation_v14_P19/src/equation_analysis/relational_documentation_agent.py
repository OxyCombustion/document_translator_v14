# -*- coding: utf-8 -*-
"""
Relational Documentation Agent - Context Documentation for Relational Equations

This agent generates comprehensive documentation for relational equations:
- Physical meaning and interpretation
- Application context and constraints
- When and how to use the equation
- Cross-references to related equations

Author: Document Translator V11 System
Date: 2025-10-09
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime


@dataclass
class DocumentationResult:
    """Result of documentation generation for a single equation."""
    equation_number: str
    success: bool
    markdown_doc: Optional[str]
    latex_formatted: Optional[str]
    metadata: Dict
    warnings: List[str]


class RelationalDocumentationAgent:
    """
    Generate comprehensive documentation for relational equations.

    Creates human-readable documentation explaining:
    1. Physical meaning and mathematical significance
    2. Application context (when/where to use)
    3. Constraints and assumptions
    4. Related equations and cross-references
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the documentation generator.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or self._default_config()
        self._init_equation_type_patterns()

    def _default_config(self) -> Dict:
        """Default configuration."""
        return {
            'include_latex': True,
            'include_context': True,
            'include_references': True,
            'include_assumptions': True,
            'format': 'markdown'
        }

    def _init_equation_type_patterns(self):
        """Initialize patterns for equation type recognition."""

        self.equation_types = {
            'conservation': {
                'keywords': ['conservation', 'sum', 'total', '= 1', '= 0'],
                'description': 'Conservation Law',
                'context': 'Fundamental physical constraint expressing conservation of energy, mass, momentum, or similar quantity.'
            },
            'differential': {
                'keywords': ['\\frac{d', '\\partial', '\\nabla', '= 0'],
                'description': 'Governing Equation',
                'context': 'Differential equation describing the fundamental physics of the system. Typically requires boundary conditions to solve.'
            },
            'reciprocity': {
                'keywords': ['= -', 'A.*F.*=.*A.*F'],
                'description': 'Reciprocity Relationship',
                'context': 'Mathematical relationship expressing symmetry or reciprocity in the physical system.'
            },
            'property_definition': {
                'keywords': ['\\varepsilon.*=', '\\alpha.*=', '\\rho.*='],
                'description': 'Property Definition',
                'context': 'Fundamental definition of a physical property or material characteristic.'
            },
            'constraint': {
                'keywords': ['\\sum.*= 1', 'factor.*=', 'view factor'],
                'description': 'Mathematical Constraint',
                'context': 'Geometric or physical constraint that must be satisfied by the system.'
            }
        }

    def generate_documentation(
        self,
        equation: Dict,
        classification_data: Dict
    ) -> DocumentationResult:
        """
        Generate comprehensive documentation for a relational equation.

        Args:
            equation: Original equation dictionary with LaTeX
            classification_data: Classification results with features

        Returns:
            DocumentationResult with generated documentation
        """
        eq_num = equation.get('equation_number', 'unknown')
        latex = equation.get('latex', '')
        page = equation.get('page', '?')

        warnings = []

        # Identify equation type
        eq_type = self._identify_equation_type(latex, classification_data)

        # Extract features from classification
        features = classification_data.get('features', {})
        rationale = classification_data.get('rationale', {})

        # Generate documentation sections
        physical_meaning = self._explain_physical_meaning(
            latex, eq_type, features
        )

        application_context = self._describe_application_context(
            eq_type, features
        )

        constraints = self._identify_constraints(
            latex, eq_type, features
        )

        # Build markdown documentation
        markdown_doc = self._build_markdown_documentation(
            eq_num, latex, page, eq_type, physical_meaning,
            application_context, constraints, rationale
        )

        # Build LaTeX formatted version
        latex_formatted = self._build_latex_documentation(
            eq_num, latex, page, eq_type, physical_meaning,
            application_context, constraints
        )

        # Build metadata
        metadata = {
            'equation_number': eq_num,
            'equation_type': eq_type['description'],
            'page': page,
            'has_differential': features.get('structural', {}).get('has_differential', False),
            'has_summation': features.get('structural', {}).get('has_summation', False),
            'complexity': features.get('structural', {}).get('complexity_score', 0.0)
        }

        return DocumentationResult(
            equation_number=eq_num,
            success=True,
            markdown_doc=markdown_doc,
            latex_formatted=latex_formatted,
            metadata=metadata,
            warnings=warnings
        )

    def _identify_equation_type(
        self,
        latex: str,
        classification_data: Dict
    ) -> Dict:
        """Identify the specific type of relational equation."""

        # Check patterns
        for type_name, type_info in self.equation_types.items():
            for keyword in type_info['keywords']:
                # Try literal string match first
                if keyword in latex:
                    return {
                        'name': type_name,
                        'description': type_info['description'],
                        'context': type_info['context']
                    }
                # Try regex match for patterns
                try:
                    if re.search(keyword, latex):
                        return {
                            'name': type_name,
                            'description': type_info['description'],
                            'context': type_info['context']
                        }
                except re.error:
                    # If regex fails, skip it
                    continue

        # Default if no match
        return {
            'name': 'general',
            'description': 'Relational Equation',
            'context': 'Mathematical relationship expressing fundamental physics or constraints.'
        }

    def _explain_physical_meaning(
        self,
        latex: str,
        eq_type: Dict,
        features: Dict
    ) -> str:
        """Generate explanation of physical meaning."""

        # Check for specific patterns
        if 'varepsilon' in latex and 'alpha' in latex:
            return "Kirchhoff's law relating emissivity and absorptivity. For opaque surfaces at thermal equilibrium, the emissivity equals the absorptivity at each wavelength."

        if '\\sum' in latex and '= 1' in latex or '=\\;1' in latex:
            return "Summation constraint ensuring completeness. All view factors from a surface must sum to unity, representing the geometric closure of the system."

        if '\\frac{d' in latex or '\\partial' in latex:
            return "Governing differential equation describing the fundamental heat transfer physics. This equation must be solved with appropriate boundary conditions to determine temperature distributions."

        if '= -' in latex and 'q_' in latex:
            return "Reciprocity relationship for heat transfer. The heat transfer from surface 1 to surface 2 equals the negative of heat transfer from surface 2 to surface 1 (Newton's third law applied to heat exchange)."

        if '\\nabla' in latex:
            return "Vector form of the heat diffusion equation. The divergence of the heat flux equals the local rate of thermal energy storage."

        # Generic explanation
        return f"{eq_type['description']} expressing fundamental physical constraints or relationships that govern the behavior of the thermal system."

    def _describe_application_context(
        self,
        eq_type: Dict,
        features: Dict
    ) -> str:
        """Describe when and how to use this equation."""

        type_name = eq_type['name']

        if type_name == 'conservation':
            return """**When to use**: Apply this constraint when modeling systems where the sum of components must equal a fixed value (typically 1 or 0).

**How to use**: Use as a constraint equation in your system of equations. Not directly solvable for a single variable.

**Example applications**:
- View factor summation in radiation enclosures
- Energy balance verification
- Material property normalization"""

        elif type_name == 'differential':
            return """**When to use**: Apply when solving for temperature distributions in conduction problems.

**How to use**: Requires boundary conditions to form a well-posed problem. Solve using:
- Analytical methods (separation of variables, Laplace transform)
- Numerical methods (finite difference, finite element)

**Required information**:
- Geometry and domain
- Boundary conditions (Dirichlet, Neumann, Robin)
- Material properties
- Initial conditions (if transient)"""

        elif type_name == 'reciprocity':
            return """**When to use**: Utilize when checking consistency of radiation or heat transfer calculations between surfaces.

**How to use**: Apply as a verification check or to reduce the number of independent calculations needed.

**Applications**:
- Radiation network analysis
- View factor calculations
- Heat exchanger modeling"""

        elif type_name == 'property_definition':
            return """**When to use**: Reference when working with radiative properties of surfaces.

**How to use**: Apply at specified temperature and wavelength conditions. Note that properties are typically wavelength and temperature dependent.

**Important considerations**:
- Valid at thermal equilibrium
- May vary with surface condition
- Temperature dependent
- Wavelength specific"""

        elif type_name == 'constraint':
            return """**When to use**: Apply as a geometric or physical constraint in your analysis.

**How to use**: Include as an equality constraint when formulating the system of equations.

**Purpose**:
- Ensures physical consistency
- Reduces degrees of freedom
- Provides verification checks"""

        else:
            return """**When to use**: Reference when understanding fundamental relationships in the thermal system.

**How to use**: Apply as context for other calculations or as verification of physical consistency.

**Note**: This is a fundamental relationship that constrains the behavior of the system."""

    def _identify_constraints(
        self,
        latex: str,
        eq_type: Dict,
        features: Dict
    ) -> List[str]:
        """Identify key constraints and assumptions."""

        constraints = []

        # Check for summation
        if '\\sum' in latex:
            constraints.append("All terms in the summation must be properly accounted for")

        # Check for differential
        if '\\frac{d' in latex or '\\partial' in latex:
            constraints.append("Requires boundary conditions for solution")
            constraints.append("Assumes continuous, differentiable functions")

        # Check for properties
        if any(prop in latex for prop in ['\\varepsilon', '\\alpha', '\\rho', '\\tau']):
            constraints.append("Material properties may be temperature dependent")
            constraints.append("Assumes homogeneous, isotropic materials unless specified")

        # Check for thermal equilibrium
        if '=' in latex and any(prop in latex for prop in ['\\varepsilon', '\\alpha']):
            constraints.append("Valid at thermal equilibrium")
            constraints.append("Wavelength specific relationship")

        # General constraints
        if '= 0' in latex:
            constraints.append("Steady-state condition (time-independent)")

        if not constraints:
            constraints.append("Standard physical assumptions apply")

        return constraints

    def _build_markdown_documentation(
        self,
        eq_num: str,
        latex: str,
        page: int,
        eq_type: Dict,
        physical_meaning: str,
        application_context: str,
        constraints: List[str],
        rationale: Dict
    ) -> str:
        """Build comprehensive markdown documentation."""

        doc = f"""# Equation {eq_num}: {eq_type['description']}

**Source**: Page {page}
**Category**: Relational Equation
**Type**: {eq_type['description']}

---

## Equation

```latex
{latex}
```

---

## Physical Meaning

{physical_meaning}

---

## Application Context

{application_context}

---

## Constraints and Assumptions

"""

        for i, constraint in enumerate(constraints, 1):
            doc += f"{i}. {constraint}\\n"

        doc += f"""

---

## Classification Details

**Structural Analysis**: {rationale.get('structural', 'N/A')}

**Symbol Analysis**: {rationale.get('symbols', 'N/A')}

**Pattern Matching**: {rationale.get('patterns', 'N/A')}

---

## Related Concepts

- Heat transfer fundamentals
- Conservation laws
- Thermal radiation
- Material properties

---

*Generated by RelationalDocumentationAgent*
*Document Translator V11 System*
*Date: {datetime.now().strftime('%Y-%m-%d')}*
"""

        return doc

    def _build_latex_documentation(
        self,
        eq_num: str,
        latex: str,
        page: int,
        eq_type: Dict,
        physical_meaning: str,
        application_context: str,
        constraints: List[str]
    ) -> str:
        """Build LaTeX formatted documentation."""

        # Simplified LaTeX version for now
        latex_doc = f"""\\subsection{{Equation {eq_num}: {eq_type['description']}}}

\\textbf{{Type}}: {eq_type['description']} \\\\
\\textbf{{Page}}: {page}

\\begin{{equation}}
{latex}
\\end{{equation}}

\\textbf{{Physical Meaning}}: {physical_meaning}

\\textbf{{Constraints}}:
\\begin{{itemize}}
"""

        for constraint in constraints:
            latex_doc += f"  \\item {constraint}\\n"

        latex_doc += "\\end{itemize}"

        return latex_doc


def main():
    """Test the documentation generator on sample equation."""
    print("RelationalDocumentationAgent - Test Run\\n")
    print("="*60)

    # Load sample relational equation
    sample_equation = {
        'equation_number': '10',
        'latex': '{\\mathcal{E}}\\,=\\,\\alpha',
        'page': 5,
        'status': 'success'
    }

    sample_classification = {
        'type': 'relational',
        'confidence': 0.270,
        'features': {
            'structural': {
                'has_isolated_output': False,
                'has_differential': False,
                'has_summation': False
            },
            'symbols': {
                'has_property_symbol': True
            }
        },
        'rationale': {
            'structural': 'Simple structural form',
            'symbols': 'Material property symbols present',
            'patterns': 'Property equality (conf: 0.90)'
        }
    }

    generator = RelationalDocumentationAgent()
    result = generator.generate_documentation(sample_equation, sample_classification)

    print(f"Equation {result.equation_number}")
    print(f"Success: {result.success}\\n")

    if result.markdown_doc:
        print("MARKDOWN DOCUMENTATION:")
        print(result.markdown_doc)

    print("\\n" + "="*60)


if __name__ == '__main__':
    main()
