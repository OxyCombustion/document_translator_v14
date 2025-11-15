# -*- coding: utf-8 -*-
"""
Context Enhancer for RAG Micro-Bundles
Adds usage guidance, semantic tags, and related entities to bundles.

This module implements Phase 3 of the micro-bundle generation pipeline:
- Generate actionable usage guidance (when_to_use, prerequisites, examples)
- Extract semantic tags from content for retrieval
- Link related entities based on relationships

Each bundle becomes immediately actionable with clear guidance on:
- When to use this equation/table/concept
- What prerequisites are needed
- Example calculations with typical values
- Limitations and valid ranges
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
import logging
from typing import Dict, List, Optional, Any, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class ContextEnhancer:
    """
    Enhance micro-bundles with usage guidance and semantic context.

    Responsibilities:
    - Generate usage_guidance for each bundle type
    - Extract semantic_tags for retrieval optimization
    - Link related_entities based on relationships
    - Make bundles immediately actionable for users
    """

    def __init__(self, config: Dict, semantic_registry: Optional[Any] = None):
        """
        Initialize context enhancer.

        Args:
            config: Configuration dictionary from YAML
            semantic_registry: Optional SemanticRegistry for variable lookups
        """
        self.config = config
        self.semantic_registry = semantic_registry
        self.enhancement_config = config.get('context_enhancement', {})

        logger.info("ContextEnhancer initialized")

    def enhance_equation_bundle(self, bundle: Any) -> Any:
        """
        Add context to equation bundle.

        Adds:
        - usage_guidance: when_to_use, prerequisites, example, limitations
        - semantic_tags: extracted from equation, variables, context
        - related_entities: related equations, tables

        Args:
            bundle: MicroBundle to enhance

        Returns:
            Enhanced MicroBundle
        """
        logger.debug(f"Enhancing equation bundle: {bundle.bundle_id}")

        # Generate usage guidance
        if self.enhancement_config.get('usage_guidance', {}).get('enabled', True):
            bundle.usage_guidance = self._generate_usage_guidance('equation', bundle.content)

        # Extract semantic tags
        if self.enhancement_config.get('semantic_tags', {}).get('enabled', True):
            bundle.semantic_tags = self._extract_semantic_tags(bundle)

        # Find related entities
        bundle.embedding_metadata['related_entities'] = self._find_related_entities(
            bundle.entity_id,
            bundle.content
        )

        logger.debug(f"Enhanced equation bundle: {len(bundle.semantic_tags)} tags, "
                     f"{len(bundle.embedding_metadata.get('related_entities', []))} related entities")

        return bundle

    def enhance_table_bundle(self, bundle: Any) -> Any:
        """
        Add context to table bundle.

        Adds:
        - usage_guidance: when_to_use, how_to_read, example, notes
        - semantic_tags: extracted from table title, columns, data
        - related_entities: equations using this table

        Args:
            bundle: MicroBundle to enhance

        Returns:
            Enhanced MicroBundle
        """
        logger.debug(f"Enhancing table bundle: {bundle.bundle_id}")

        # Generate usage guidance
        if self.enhancement_config.get('usage_guidance', {}).get('enabled', True):
            bundle.usage_guidance = self._generate_usage_guidance('table', bundle.content)

        # Extract semantic tags
        if self.enhancement_config.get('semantic_tags', {}).get('enabled', True):
            bundle.semantic_tags = self._extract_semantic_tags(bundle)

        # Find related entities
        bundle.embedding_metadata['related_entities'] = self._find_related_entities(
            bundle.entity_id,
            bundle.content
        )

        logger.debug(f"Enhanced table bundle: {len(bundle.semantic_tags)} tags, "
                     f"{len(bundle.embedding_metadata.get('related_entities', []))} related entities")

        return bundle

    def enhance_concept_bundle(self, bundle: Any) -> Any:
        """
        Add context to concept bundle.

        Adds:
        - usage_guidance: definition, typical_values, context_of_use
        - semantic_tags: extracted from definition, related concepts
        - related_entities: equations using this variable

        Args:
            bundle: MicroBundle to enhance

        Returns:
            Enhanced MicroBundle
        """
        logger.debug(f"Enhancing concept bundle: {bundle.bundle_id}")

        # Generate usage guidance
        if self.enhancement_config.get('usage_guidance', {}).get('enabled', True):
            bundle.usage_guidance = self._generate_usage_guidance('concept', bundle.content)

        # Extract semantic tags
        if self.enhancement_config.get('semantic_tags', {}).get('enabled', True):
            bundle.semantic_tags = self._extract_semantic_tags(bundle)

        # Find related entities
        bundle.embedding_metadata['related_entities'] = self._find_related_entities(
            bundle.entity_id,
            bundle.content
        )

        logger.debug(f"Enhanced concept bundle: {len(bundle.semantic_tags)} tags, "
                     f"{len(bundle.embedding_metadata.get('related_entities', []))} related entities")

        return bundle

    def _generate_usage_guidance(self, bundle_type: str, content: Dict) -> Dict[str, Any]:
        """
        Generate usage guidance based on bundle type and content.

        For equations:
        - when_to_use: Physical situation description
        - prerequisites: Required inputs
        - example: Numerical example with typical values
        - limitations: Assumptions, valid ranges

        For tables:
        - when_to_use: When you need this data
        - how_to_read: How to interpret rows/columns
        - example: Sample lookup
        - notes: Important caveats

        For concepts:
        - definition: Clear explanation
        - typical_values: Common ranges
        - context_of_use: Where it appears

        Args:
            bundle_type: Type of bundle (equation|table|concept)
            content: Bundle content dictionary

        Returns:
            Dictionary with usage guidance fields
        """
        if bundle_type == 'equation':
            return self._generate_equation_guidance(content)
        elif bundle_type == 'table':
            return self._generate_table_guidance(content)
        elif bundle_type == 'concept':
            return self._generate_concept_guidance(content)
        else:
            return {}

    def _generate_equation_guidance(self, content: Dict) -> Dict[str, Any]:
        """Generate usage guidance for equation."""
        equation = content.get('equation', {})
        variables = content.get('variables', [])
        data_deps = content.get('data_dependencies', [])

        guidance = {}

        # When to use (from description or infer from variables)
        description = equation.get('description', '')
        if description:
            guidance['when_to_use'] = description
        else:
            # Infer from variable names
            var_names = [v.get('name', '') for v in variables if v.get('name')]
            if var_names:
                guidance['when_to_use'] = f"Use when calculating relationships between {', '.join(var_names[:3])}"
            else:
                guidance['when_to_use'] = "Apply this equation for heat transfer calculations"

        # Prerequisites (from variables)
        prerequisites = []
        for var in variables:
            if var.get('role') in ['input', 'parameter']:
                var_name = var.get('name') or var.get('symbol')
                data_source = var.get('data_source')
                if data_source:
                    prerequisites.append(f"{var_name} (from {data_source})")
                else:
                    prerequisites.append(var_name)

        if prerequisites:
            guidance['prerequisites'] = prerequisites
        else:
            guidance['prerequisites'] = ["Input variables as specified in equation"]

        # Example (numerical calculation)
        guidance['example'] = self._generate_numerical_example(equation, variables)

        # Limitations (from data dependencies or infer)
        limitations = []

        # Check for regime applicability from data sources
        for dep in data_deps:
            target = dep.get('target', '')
            if 'table' in target.lower():
                limitations.append(f"Valid only within ranges specified in {target}")

        # Default limitations
        if not limitations:
            limitations = [
                "Verify assumptions apply to your specific case",
                "Check that all variables are in consistent units"
            ]

        guidance['limitations'] = limitations

        return guidance

    def _generate_table_guidance(self, content: Dict) -> Dict[str, Any]:
        """Generate usage guidance for table."""
        table = content.get('table', {})
        used_by = content.get('used_by_equations', [])

        guidance = {}

        # When to use
        caption = table.get('caption', '')
        if caption:
            guidance['when_to_use'] = f"Use when you need data: {caption}"
        else:
            if used_by:
                eq_ids = ', '.join([e.get('entity_id', '') for e in used_by[:3]])
                guidance['when_to_use'] = f"Provides data for equations: {eq_ids}"
            else:
                guidance['when_to_use'] = "Reference table for property values"

        # How to read
        if used_by:
            var_used = used_by[0].get('variable', 'unknown')
            lookup = used_by[0].get('usage', 'lookup')
            guidance['how_to_read'] = f"Lookup {var_used} using {lookup} method"
        else:
            guidance['how_to_read'] = "Locate row/column for your conditions, read value at intersection"

        # Example
        if caption and 'temperature' in caption.lower():
            guidance['example'] = "Example: For air at 300K, find corresponding property value in row"
        elif caption:
            guidance['example'] = f"Refer to table caption for usage: {caption}"
        else:
            guidance['example'] = "Identify your conditions, lookup corresponding value"

        # Notes
        notes = []
        if 'interpolation' in caption.lower():
            notes.append("Linear interpolation may be needed between values")
        if used_by:
            notes.append(f"Used by {len(used_by)} equation(s) in this document")

        guidance['notes'] = notes if notes else ["Verify units match your calculation requirements"]

        return guidance

    def _generate_concept_guidance(self, content: Dict) -> Dict[str, Any]:
        """Generate usage guidance for concept."""
        concept = content.get('concept', {})
        used_in = content.get('used_in_equations', [])

        guidance = {}

        # Definition
        definition = concept.get('definition', '')
        name = concept.get('name', '')
        symbol = concept.get('symbol', '')

        if definition:
            guidance['definition'] = definition
        elif name:
            guidance['definition'] = f"{name} ({symbol}): dimensionless parameter in heat transfer"
        else:
            guidance['definition'] = "Physical property or parameter"

        # Typical values (from usage examples or heuristics)
        units = concept.get('units', '')
        if units:
            guidance['typical_values'] = f"Measured in {units}"
        else:
            # Check if dimensionless
            if any(term in name.lower() for term in ['number', 'ratio', 'factor', 'coefficient']):
                guidance['typical_values'] = "Dimensionless quantity, typically O(1)"
            else:
                guidance['typical_values'] = "Consult reference tables for typical ranges"

        # Context of use
        if used_in:
            eq_count = len(used_in)
            guidance['context_of_use'] = f"Appears in {eq_count} equation(s) in this chapter"

            # Add specific equations
            eq_ids = [eq.get('entity_id', '') for eq in used_in[:3]]
            guidance['used_in_equations'] = eq_ids
        else:
            guidance['context_of_use'] = "Defined in nomenclature section"

        return guidance

    def _generate_numerical_example(self, equation: Dict, variables: List[Dict]) -> str:
        """
        Generate numerical example for equation.

        Args:
            equation: Equation content
            variables: List of variables

        Returns:
            String with example calculation
        """
        latex = equation.get('latex', '')
        eq_num = equation.get('equation_number', '')

        if not variables:
            return f"Apply equation {eq_num} with your specific values"

        # Build example string
        example_parts = []
        example_parts.append(f"Example using typical values:")

        # Add sample values for first few variables
        for var in variables[:3]:
            name = var.get('name') or var.get('symbol', 'var')
            # Generate reasonable example values based on common heat transfer parameters
            if 'temperature' in name.lower():
                example_parts.append(f"  {name} = 300 K")
            elif 'conductivity' in name.lower():
                example_parts.append(f"  {name} = 0.6 W/(m·K)")
            elif 'area' in name.lower():
                example_parts.append(f"  {name} = 1.0 m²")
            elif 'length' in name.lower() or 'thickness' in name.lower():
                example_parts.append(f"  {name} = 0.1 m")
            else:
                example_parts.append(f"  {name} = [value]")

        return "\n".join(example_parts)

    def _extract_semantic_tags(self, bundle: Any) -> List[str]:
        """
        Extract semantic tags for retrieval.

        Sources:
        - Variable names (emissivity, conductivity)
        - Physical concepts (radiation, conduction)
        - Equation types (conservation, correlation)
        - Material types (metal, fluid)

        Args:
            bundle: MicroBundle

        Returns:
            List of lowercase tags
        """
        tags = set()

        # Extract from existing semantic_tags if present
        if bundle.semantic_tags:
            tags.update(bundle.semantic_tags)

        # Extract from bundle type
        tags.add(bundle.bundle_type)

        # Type-specific extraction
        if bundle.bundle_type == 'equation':
            tags.update(self._extract_equation_tags(bundle.content))
        elif bundle.bundle_type == 'table':
            tags.update(self._extract_table_tags(bundle.content))
        elif bundle.bundle_type == 'concept':
            tags.update(self._extract_concept_tags(bundle.content))

        # Clean and limit tags
        max_tags = self.enhancement_config.get('semantic_tags', {}).get('max_tags', 10)
        tags = [tag.lower().strip() for tag in tags if tag]
        tags = [tag for tag in tags if len(tag) > 2]  # Remove very short tags

        # Prioritize domain-specific tags
        domain_tags = [tag for tag in tags if any(
            term in tag for term in ['heat', 'transfer', 'thermal', 'temperature',
                                     'conduction', 'convection', 'radiation']
        )]

        # Return domain tags first, then others, up to max
        result = domain_tags + [tag for tag in tags if tag not in domain_tags]
        return result[:max_tags]

    def _extract_equation_tags(self, content: Dict) -> Set[str]:
        """Extract tags from equation content."""
        tags = set()

        equation = content.get('equation', {})
        variables = content.get('variables', [])

        # From description
        description = equation.get('description', '')
        if description:
            tags.update(self._extract_keywords_from_text(description))

        # From variable names
        for var in variables:
            name = var.get('name', '')
            if name:
                # Split compound names (e.g., "thermal_conductivity" -> ["thermal", "conductivity"])
                tags.update(name.lower().replace('_', ' ').split())

        # From section
        section = equation.get('section', '')
        if section:
            tags.update(self._extract_keywords_from_text(section))

        return tags

    def _extract_table_tags(self, content: Dict) -> Set[str]:
        """Extract tags from table content."""
        tags = set()

        table = content.get('table', {})

        # From caption
        caption = table.get('caption', '')
        if caption:
            tags.update(self._extract_keywords_from_text(caption))

        # From section
        section = table.get('section', '')
        if section:
            tags.update(self._extract_keywords_from_text(section))

        return tags

    def _extract_concept_tags(self, content: Dict) -> Set[str]:
        """Extract tags from concept content."""
        tags = set()

        concept = content.get('concept', {})

        # From name
        name = concept.get('name', '')
        if name:
            tags.update(name.lower().replace('_', ' ').split())

        # From definition
        definition = concept.get('definition', '')
        if definition:
            tags.update(self._extract_keywords_from_text(definition))

        return tags

    def _extract_keywords_from_text(self, text: str) -> Set[str]:
        """
        Extract meaningful keywords from text.

        Args:
            text: Input text

        Returns:
            Set of keywords
        """
        if not text:
            return set()

        # Remove common words (stopwords)
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'this', 'that', 'these', 'those', 'it', 'its'
        }

        # Extract words (alphanumeric sequences)
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())

        # Filter stopwords and short words
        keywords = {w for w in words if len(w) > 3 and w not in stopwords}

        return keywords

    def _find_related_entities(self, entity_id: str, content: Dict) -> List[str]:
        """
        Find related entities based on relationships.

        Related = entities that:
        - Share variables
        - Same section/topic
        - Sequential equations (eq:9, eq:10, eq:11)
        - Referenced together

        Args:
            entity_id: Current entity ID
            content: Bundle content with relationships

        Returns:
            List of related entity IDs
        """
        related = set()

        # From data dependencies
        data_deps = content.get('data_dependencies', [])
        for dep in data_deps:
            target = dep.get('target')
            if target:
                related.add(target)

        # From cross-references
        cross_refs = content.get('cross_references', [])
        for ref in cross_refs:
            source = ref.get('source')
            if source and source != entity_id:
                related.add(source)

        # From used_by_equations (for tables)
        used_by = content.get('used_by_equations', [])
        for eq in used_by:
            eq_id = eq.get('entity_id')
            if eq_id:
                related.add(eq_id)

        # From used_in_equations (for concepts)
        used_in = content.get('used_in_equations', [])
        for eq in used_in:
            eq_id = eq.get('entity_id')
            if eq_id:
                related.add(eq_id)

        # Sequential entities (e.g., eq:9 relates to eq:8, eq:10)
        if ':' in entity_id:
            prefix, num_str = entity_id.split(':')
            try:
                num = int(''.join(c for c in num_str if c.isdigit()))
                related.add(f"{prefix}:{num-1}")
                related.add(f"{prefix}:{num+1}")
            except ValueError:
                pass

        # Remove self
        related.discard(entity_id)

        return list(related)
