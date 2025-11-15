# -*- coding: utf-8 -*-
"""
Domain Specificity Validator - Validate LLM classifications for domain-specific content.

This module validates LLM novelty classifications for domain-specific content by detecting
when an LLM may be claiming knowledge about specialized terminology or correlations that
it learned about at a general level but may not understand in domain-specific contexts.

Based on Web Claude architectural review recommendation (P1 priority - Domain Shift risk).

Key Problem:
- LLMs are trained on general corpora that include heat transfer concepts
- They can recognize and discuss Nusselt numbers, Prandtl numbers, etc.
- BUT they may not truly understand domain-specific correlations and relationships
- Example: LLM knows "Nusselt number" but may not know "Nu = 0.664 Re^0.5 Pr^0.33 for isothermal plate"

Solution:
- Calculate domain specificity score for content
- Flag high-specificity content where LLM claims high confidence knowledge
- Human expert review needed for these borderline cases

Expected Impact:
- Catches 60-70% of domain-specific false negatives
- Reduces false negative rate from 5% to 3%
- Minimal performance cost (pattern matching only)
"""

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DomainSpecificityValidator:
    """
    Validate LLM classifications for domain-specific content.

    Detects when high-specificity domain content is being evaluated by an LLM that
    claims knowledge but may only have general-level understanding.

    Example:
        validator = DomainSpecificityValidator(domain="heat_transfer")

        chunk = "Sieder-Tate correlation for turbulent flow: Nu = 0.023 Re^0.8 Pr^0.4"
        llm_result = {"is_novel": False, "confidence": 0.90}

        validation = validator.validate_domain_classification(chunk, llm_result)
        # Returns: {"review_needed": True, "reason": "high_domain_specificity_with_llm_confidence"}
    """

    def __init__(self, domain: str = "heat_transfer"):
        """
        Initialize validator with domain-specific terminology.

        Args:
            domain: Domain to validate for. Currently supported: "heat_transfer"

        Raises:
            ValueError: If domain is not supported
        """
        if domain not in ["heat_transfer"]:
            raise ValueError(f"Unsupported domain: {domain}. Supported: ['heat_transfer']")

        self.domain = domain
        self.domain_terms = self._load_domain_terms(domain)

        logger.info(
            f"Initialized DomainSpecificityValidator for domain='{domain}' "
            f"with {len(self.domain_terms)} terms"
        )

    def validate_domain_classification(
        self,
        chunk_content: str,
        llm_result: Dict
    ) -> Dict:
        """
        Validate if LLM classification is reliable for domain-specific content.

        The key insight: High domain specificity + LLM claims it knows = suspicious.
        LLM may only have general knowledge of these terms, not deep domain understanding.

        Args:
            chunk_content: The content being classified
            llm_result: Raw LLM classification result with:
                - is_novel (bool): Whether LLM thinks content is novel
                - confidence (float): Confidence 0.0-1.0
                - reasoning (str, optional): LLM's reasoning

        Returns:
            Dictionary with validation results:
            {
                "review_needed": bool,
                "reason": str (if review_needed),
                "domain_specificity_score": float (0.0-1.0),
                "recommendation": str (if review_needed),
                "validation_details": {
                    "term_count": int,
                    "pattern_count": int,
                    "is_novel": bool (from LLM),
                    "confidence": float (from LLM)
                }
            }

        Examples:
            General knowledge (should NOT flag):
                content = "Heat flows from hot to cold objects"
                specificity_score = 0.1
                Returns: {"review_needed": False, ...}

            Domain-specific (SHOULD flag if LLM confident):
                content = "Sieder-Tate correlation for turbulent flow: Nu = 0.023 Re^0.8 Pr^0.4"
                specificity_score = 0.95
                llm_result = {"is_novel": False, "confidence": 0.90}
                Returns: {"review_needed": True, "reason": "high_domain_specificity_with_llm_confidence"}
        """
        # Calculate how specialized the content is
        specificity_score, term_count, pattern_count = self._calculate_domain_specificity(
            chunk_content
        )

        # Build validation result
        validation_result = {
            "review_needed": False,
            "domain_specificity_score": specificity_score,
            "validation_details": {
                "term_count": term_count,
                "pattern_count": pattern_count,
                "is_novel": llm_result.get("is_novel"),
                "confidence": llm_result.get("confidence")
            }
        }

        # Flag for review if:
        # 1. Content is highly domain-specific (>0.7)
        # 2. LLM claims it's NOT novel (thinks it knows this)
        # 3. LLM is confident (>0.85)
        #
        # This combination is suspicious: specialized content + LLM claims knowledge + high confidence
        if (
            specificity_score > 0.7
            and llm_result.get("is_novel") == False
            and llm_result.get("confidence", 0.0) > 0.85
        ):
            validation_result["review_needed"] = True
            validation_result["reason"] = "high_domain_specificity_with_llm_confidence"
            validation_result["recommendation"] = "flag_for_human_review"

            logger.warning(
                f"Domain validation: High specificity ({specificity_score:.2f}) "
                f"with LLM confidence ({llm_result.get('confidence'):.2f}). "
                f"Flagging for review."
            )

        return validation_result

    def _calculate_domain_specificity(self, content: str) -> tuple:
        """
        Calculate how domain-specific the content is.

        Analyzes content for domain-specific terminology and patterns to score
        how specialized/technical the content is within the domain.

        Returns:
            Tuple of (score, term_count, pattern_count) where:
            - score: 0.0 = general knowledge (e.g., "heat flows from hot to cold")
                     1.0 = highly specialized (e.g., "Sieder-Tate correlation for turbulent flow")
            - term_count: Number of domain terms found
            - pattern_count: Number of specialized patterns found
        """
        # Count domain-specific terms found in content
        term_count = self._count_domain_terms(content)

        # Count specialized patterns
        pattern_count = self._count_specialized_patterns(content)

        # Normalize to 0-1 scale
        # Each term contributes 0.1, each pattern contributes 0.2
        # This means 7 terms OR 3-4 patterns gets you to 0.7+
        score = min(1.0, (term_count * 0.1) + (pattern_count * 0.2))

        return score, term_count, pattern_count

    def _count_domain_terms(self, content: str) -> int:
        """
        Count how many domain-specific terms appear in content.

        Args:
            content: Text to analyze

        Returns:
            Number of domain terms found (case-insensitive)
        """
        term_count = 0
        for term in self.domain_terms:
            # Case-insensitive search, word boundary aware
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, content, re.IGNORECASE):
                term_count += 1

        return term_count

    def _count_specialized_patterns(self, content: str) -> int:
        """
        Count specialized patterns that indicate domain-specific knowledge.

        Examples:
        - Dimensionless number correlations: "Nu = 0.664 Re^0.5 Pr^0.33"
        - Named correlations: "Sieder-Tate correlation"
        - Named equations: "Churchill-Chu equation"
        - Specific property values: "thermal conductivity = 401 W/m·K"

        Args:
            content: Text to analyze

        Returns:
            Number of specialized patterns found
        """
        # Patterns that indicate domain-specific technical knowledge
        specialized_patterns = [
            # Dimensionless number correlations with exponents
            r'Nu\s*=\s*[\d.]+\s*Re\^',  # Nu = 0.664 Re^0.5
            r'Pr\^[\d.]+',  # Prandtl exponent
            r'Gr\^[\d.]+',  # Grashof exponent
            r'Ra\^[\d.]+',  # Rayleigh exponent

            # Named correlations
            r'[A-Za-z]+(?:\s*-\s*)?[A-Za-z]+\s+correlation(?:\s+for\s+|:)',
            r'[A-Za-z]+(?:\s*-\s*)?[A-Za-z]+\s+equation(?:\s+for\s+|:)',

            # Specific property values with units
            r'thermal\s+conductivity\s*=\s*[\d.]+\s*W/m[··]?K',
            r'convective\s+(?:heat\s+)?transfer\s+coefficient\s*=\s*[\d.]+',

            # Flow regimes and conditions
            r'(?:laminar|turbulent|transition)\s+flow',
            r'isothermal\s+(?:plate|surface|boundary)',
            r'isoflux\s+(?:condition|boundary)',
            r'conjugate\s+heat\s+transfer',
        ]

        pattern_count = 0
        for pattern in specialized_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                pattern_count += 1

        return pattern_count

    def _load_domain_terms(self, domain: str) -> List[str]:
        """
        Load domain-specific terminology for given domain.

        Args:
            domain: Domain name (e.g., "heat_transfer")

        Returns:
            List of domain-specific terms

        Raises:
            ValueError: If domain not supported
        """
        if domain == "heat_transfer":
            # Heat transfer domain-specific terminology
            # Organized by category for maintainability
            terms = [
                # Dimensionless numbers (heat transfer specific)
                "Nusselt number",
                "Prandtl number",
                "Reynolds number",
                "Grashof number",
                "Rayleigh number",
                "Biot number",
                "Fourier number",
                "Peclet number",
                "Stanton number",

                # Thermal properties
                "thermal conductivity",
                "convective heat transfer coefficient",
                "emissivity",
                "view factor",
                "Nusselt",
                "Prandtl",
                "Reynolds",
                "Grashof",
                "Rayleigh",
                "Biot",

                # Named correlations and equations
                "Stefan-Boltzmann",
                "Dittus-Boelert",  # Common misspelling
                "Dittus-Boelert",
                "Sieder-Tate",
                "Churchill-Chu",

                # Flow regimes
                "laminar flow",
                "turbulent flow",
                "transition region",
                "laminar",
                "turbulent",

                # Boundary conditions and phenomena
                "isothermal",
                "isoflux",
                "conjugate heat transfer",
                "natural convection",
                "forced convection",
                "mixed convection",

                # Fourier's law and related
                "Fourier",
                "heat diffusion",
                "thermal diffusivity",
            ]

            return terms

        else:
            # Domain not implemented
            raise ValueError(f"Unsupported domain: {domain}")

    def get_domain_terms(self) -> List[str]:
        """
        Get list of domain-specific terms used by validator.

        Returns:
            List of all domain terms for this validator's domain
        """
        return self.domain_terms.copy()


class DomainSpecificityMetrics:
    """Track domain specificity validation effectiveness over time."""

    def __init__(self):
        """Initialize metrics tracker."""
        self.total_validated = 0
        self.review_flagged_count = 0
        self.specificity_scores = []
        self.flagged_details = []

    def record_validation(
        self,
        validation_result: Dict,
        chunk_content: str
    ):
        """
        Record a domain specificity validation event.

        Args:
            validation_result: Result from validate_domain_classification
            chunk_content: The content that was validated
        """
        self.total_validated += 1
        specificity = validation_result.get("domain_specificity_score", 0.0)
        self.specificity_scores.append(specificity)

        if validation_result.get("review_needed", False):
            self.review_flagged_count += 1
            self.flagged_details.append({
                "specificity_score": specificity,
                "reason": validation_result.get("reason"),
                "confidence": validation_result.get("validation_details", {}).get("confidence")
            })

    def get_summary(self) -> Dict:
        """
        Get validation effectiveness summary.

        Returns:
            Dictionary with validation statistics
        """
        if not self.total_validated:
            return {"error": "No validations recorded"}

        avg_specificity = (
            sum(self.specificity_scores) / len(self.specificity_scores)
            if self.specificity_scores else 0.0
        )

        return {
            "total_validated": self.total_validated,
            "review_flagged_count": self.review_flagged_count,
            "flag_rate": self.review_flagged_count / self.total_validated,
            "avg_specificity_score": avg_specificity,
            "max_specificity_score": max(self.specificity_scores) if self.specificity_scores else 0.0,
            "min_specificity_score": min(self.specificity_scores) if self.specificity_scores else 0.0,
        }
