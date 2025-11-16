# -*- coding: utf-8 -*-
"""
Bundle Builders for RAG Micro-Bundles
Creates typed bundles (equation, table, concept) from relationships.

This module implements three specialized builders:
- EquationBundleBuilder: Complete equation + variables + data sources + citations
- TableBundleBuilder: Complete table + equations using it + cross-references
- ConceptBundleBuilder: Variable definition + all equations using it + examples

Each builder creates self-contained bundles optimized for embedding.
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

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


# Data Structures
@dataclass
class MicroBundle:
    """Base structure for all micro-bundles."""
    bundle_id: str  # e.g., "bundle:eq9_complete"
    bundle_type: str  # equation | table | concept
    entity_id: str  # e.g., "eq:9", "tbl:3", "var:epsilon"

    content: Dict[str, Any]  # Type-specific content
    usage_guidance: Dict[str, Any]  # How to use this entity
    semantic_tags: List[str]  # Keywords for retrieval
    embedding_metadata: Dict[str, Any]  # Metadata for vector databases

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def estimate_token_count(self) -> int:
        """
        Estimate token count for this bundle.
        Uses rough approximation: 4 chars per token.
        """
        json_str = json.dumps(self.to_dict())
        chars_per_token = 4
        return len(json_str) // chars_per_token


class EquationBundleBuilder:
    """
    Builder for equation micro-bundles.

    Creates self-contained cards combining:
    - Equation content (latex, description, page)
    - Variables with definitions
    - Data dependencies (tables providing values)
    - Cross-references (where equation is mentioned)
    - Citations (methodology sources)
    - Usage guidance
    """

    def __init__(self, config: Dict, semantic_registry: Optional[Any] = None):
        """
        Initialize equation bundle builder.

        Args:
            config: Configuration dictionary
            semantic_registry: Optional SemanticRegistry for variable lookups
        """
        self.config = config
        self.semantic_registry = semantic_registry
        self.bundle_config = config['content_inclusion']['equation_bundle']

        logger.info("EquationBundleBuilder initialized")

    def build_bundle(
        self,
        entity_id: str,
        relationships: List[Dict],
        entity_data: Optional[Dict] = None
    ) -> MicroBundle:
        """
        Build complete equation bundle.

        Args:
            entity_id: Equation ID (e.g., "eq:9")
            relationships: All relationships involving this equation
            entity_data: Optional metadata about equation

        Returns:
            Complete MicroBundle for this equation
        """
        logger.debug(f"Building equation bundle for {entity_id}")

        # Extract relationship types
        variable_defs = [r for r in relationships if r.get('edge_type') == 'DEFINES_VARIABLE']
        data_deps = [r for r in relationships if r.get('edge_type') == 'REQUIRES_DATA_FROM']
        cross_refs = [r for r in relationships if r.get('edge_type') == 'REFERENCES']
        citations = [r for r in relationships if r.get('edge_type') == 'CITES']

        # Build content sections
        content = {
            'equation': self._extract_equation_content(entity_id, entity_data, relationships)
        }

        if self.bundle_config['include_variables']:
            content['variables'] = self._extract_variables(entity_id, relationships)

        if self.bundle_config['include_data_dependencies']:
            content['data_dependencies'] = self._extract_data_dependencies(data_deps)

        if self.bundle_config['include_cross_references']:
            content['cross_references'] = self._extract_cross_references(cross_refs)

        if self.bundle_config['include_citations']:
            content['citations'] = self._extract_citations(citations)

        # Usage guidance (Phase 3)
        usage_guidance = {}  # Will be filled in Phase 3

        # Semantic tags
        semantic_tags = self._extract_semantic_tags(entity_id, relationships)

        # Embedding metadata
        embedding_metadata = self._create_embedding_metadata(
            entity_id,
            len(relationships),
            "equation"
        )

        # Create bundle
        bundle = MicroBundle(
            bundle_id=f"bundle:{entity_id}_complete",
            bundle_type="equation",
            entity_id=entity_id,
            content=content,
            usage_guidance=usage_guidance,
            semantic_tags=semantic_tags,
            embedding_metadata=embedding_metadata
        )

        logger.debug(f"Created equation bundle: {bundle.bundle_id}, ~{bundle.estimate_token_count()} tokens")

        return bundle

    def _extract_equation_content(
        self,
        entity_id: str,
        entity_data: Optional[Dict],
        relationships: List[Dict]
    ) -> Dict:
        """Extract equation primary content."""
        # If we have entity_data, use it
        if entity_data:
            return {
                'entity_id': entity_id,
                'equation_number': entity_data.get('equation_number'),
                'latex': entity_data.get('latex'),
                'description': entity_data.get('description'),
                'page': entity_data.get('page'),
                'section': entity_data.get('section')
            }

        # Otherwise extract from relationships
        # Look for equation info in data_dependencies or other relationships
        for rel in relationships:
            if 'equation' in rel and rel['equation'].get('entity_id') == entity_id:
                eq_data = rel['equation']
                return {
                    'entity_id': entity_id,
                    'equation_number': self._extract_equation_number(entity_id),
                    'latex': eq_data.get('metadata', {}).get('latex'),
                    'description': eq_data.get('metadata', {}).get('description'),
                    'page': eq_data.get('page'),
                    'section': eq_data.get('section')
                }

        # Fallback: minimal info
        return {
            'entity_id': entity_id,
            'equation_number': self._extract_equation_number(entity_id),
            'latex': None,
            'description': None,
            'page': None,
            'section': None
        }

    def _extract_equation_number(self, entity_id: str) -> Optional[int]:
        """Extract equation number from entity_id (e.g., eq:9 → 9)."""
        try:
            if ':' in entity_id:
                num_str = entity_id.split(':')[1]
                # Handle letter suffixes (eq:9a → 9)
                num_str = ''.join(c for c in num_str if c.isdigit())
                return int(num_str) if num_str else None
        except:
            return None
        return None

    def _extract_variables(self, entity_id: str, relationships: List[Dict]) -> List[Dict]:
        """Extract all variables used in equation."""
        variables = []

        # From data dependencies
        for rel in relationships:
            if rel.get('edge_type') == 'REQUIRES_DATA_FROM' and rel.get('source') == entity_id:
                var_linkages = rel.get('variable_linkage', [])
                for var in var_linkages:
                    variables.append({
                        'symbol': var.get('symbol'),
                        'var_id': var.get('variable_id'),
                        'name': var.get('name'),
                        'role': var.get('equation_role', 'parameter'),
                        'data_source': rel.get('target')  # Where to get value
                    })

        return variables

    def _extract_data_dependencies(self, data_deps: List[Dict]) -> List[Dict]:
        """Extract data dependency relationships."""
        dependencies = []

        for rel in data_deps:
            dep = {
                'relationship_id': rel.get('relationship_id'),
                'target': rel.get('target'),
                'variable': rel.get('variable_linkage', [{}])[0].get('variable_id'),
                'lookup_method': rel.get('variable_linkage', [{}])[0].get('lookup_method')
            }

            # Add table info if available
            if 'table' in rel:
                dep['target_caption'] = rel['table'].get('metadata', {}).get('caption')

            dependencies.append(dep)

        return dependencies

    def _extract_cross_references(self, cross_refs: List[Dict]) -> List[Dict]:
        """Extract cross-reference relationships."""
        references = []

        for rel in cross_refs:
            ref = {
                'source': rel.get('source'),
                'reference_phrase': rel.get('reference_phrase', {}).get('raw_text'),
                'context': rel.get('context_snippet', {}).get('before', '')
            }
            references.append(ref)

        return references

    def _extract_citations(self, citations: List[Dict]) -> List[Dict]:
        """Extract citation relationships."""
        cites = []

        for rel in citations:
            cite = {
                'ref_id': rel.get('target') if isinstance(rel.get('target'), str) else rel.get('target', [])[0],
                'citation_marker': rel.get('citation_context', {}).get('citation_marker'),
                'purpose': rel.get('citation_purpose', {}).get('primary', 'unknown')
            }
            cites.append(cite)

        return cites

    def _extract_semantic_tags(self, entity_id: str, relationships: List[Dict]) -> List[str]:
        """Extract semantic tags from relationships."""
        tags = set()

        # From relationships
        for rel in relationships:
            if 'equation' in rel:
                eq_tags = rel['equation'].get('metadata', {}).get('semantic_tags', [])
                tags.update(eq_tags)

        return list(tags)

    def _create_embedding_metadata(
        self,
        entity_id: str,
        relationship_count: int,
        entity_type: str
    ) -> Dict:
        """Create embedding metadata for vector databases."""
        return {
            'chunk_id': entity_id.replace(':', '_'),
            'doc_id': self.config.get('embedding_metadata', {}).get('document', {}).get('default_doc_id', 'unknown'),
            'entity_type': entity_type,
            'confidence': 0.90,  # Default, will be calculated from relationships in Phase 3
            'token_count_estimate': 0,  # Will be calculated after bundle complete
            'creation_date': datetime.now().isoformat(),
            'relationships_count': relationship_count
        }


class TableBundleBuilder:
    """
    Builder for table micro-bundles.

    Creates self-contained cards combining:
    - Table content (caption, dimensions, sample data)
    - Equations using this table
    - Cross-references
    - Citations
    - Usage guidance
    """

    def __init__(self, config: Dict):
        """Initialize table bundle builder."""
        self.config = config
        self.bundle_config = config['content_inclusion']['table_bundle']

        logger.info("TableBundleBuilder initialized")

    def build_bundle(
        self,
        entity_id: str,
        relationships: List[Dict],
        entity_data: Optional[Dict] = None
    ) -> MicroBundle:
        """Build complete table bundle."""
        logger.debug(f"Building table bundle for {entity_id}")

        # Extract relationship types
        data_deps = [r for r in relationships if r.get('edge_type') == 'REQUIRES_DATA_FROM' and r.get('target') == entity_id]
        cross_refs = [r for r in relationships if r.get('edge_type') == 'REFERENCES' and r.get('target') == entity_id]
        citations = [r for r in relationships if r.get('edge_type') == 'CITES' and r.get('source') == entity_id]

        # Build content
        content = {
            'table': self._extract_table_content(entity_id, entity_data, relationships)
        }

        if self.bundle_config['include_used_by_equations']:
            content['used_by_equations'] = self._extract_used_by_equations(data_deps)

        if self.bundle_config['include_cross_references']:
            content['cross_references'] = self._extract_cross_references(cross_refs)

        if self.bundle_config['include_citations']:
            content['citations'] = self._extract_citations(citations)

        # Usage guidance (Phase 3)
        usage_guidance = {}

        # Semantic tags
        semantic_tags = self._extract_semantic_tags(entity_id, relationships)

        # Embedding metadata
        embedding_metadata = self._create_embedding_metadata(
            entity_id,
            len(relationships),
            "table"
        )

        # Create bundle
        bundle = MicroBundle(
            bundle_id=f"bundle:{entity_id}_complete",
            bundle_type="table",
            entity_id=entity_id,
            content=content,
            usage_guidance=usage_guidance,
            semantic_tags=semantic_tags,
            embedding_metadata=embedding_metadata
        )

        logger.debug(f"Created table bundle: {bundle.bundle_id}, ~{bundle.estimate_token_count()} tokens")

        return bundle

    def _extract_table_content(
        self,
        entity_id: str,
        entity_data: Optional[Dict],
        relationships: List[Dict]
    ) -> Dict:
        """Extract table primary content."""
        # From entity_data if available
        if entity_data:
            return {
                'entity_id': entity_id,
                'table_number': entity_data.get('table_number'),
                'caption': entity_data.get('caption'),
                'page': entity_data.get('page'),
                'section': entity_data.get('section')
            }

        # From relationships
        for rel in relationships:
            if 'table' in rel and rel['table'].get('entity_id') == entity_id:
                table_data = rel['table']
                return {
                    'entity_id': entity_id,
                    'table_number': self._extract_table_number(entity_id),
                    'caption': table_data.get('metadata', {}).get('caption'),
                    'page': table_data.get('page'),
                    'section': table_data.get('section')
                }

        # Fallback
        return {
            'entity_id': entity_id,
            'table_number': self._extract_table_number(entity_id),
            'caption': None,
            'page': None,
            'section': None
        }

    def _extract_table_number(self, entity_id: str) -> Optional[int]:
        """Extract table number from entity_id (e.g., tbl:3 → 3)."""
        try:
            if ':' in entity_id:
                num_str = entity_id.split(':')[1]
                return int(num_str) if num_str.isdigit() else None
        except:
            return None
        return None

    def _extract_used_by_equations(self, data_deps: List[Dict]) -> List[Dict]:
        """Extract equations that use this table."""
        equations = []

        for rel in data_deps:
            eq = {
                'entity_id': rel.get('source'),
                'variable': rel.get('variable_linkage', [{}])[0].get('variable_id'),
                'usage': rel.get('variable_linkage', [{}])[0].get('lookup_method')
            }

            # Add equation info if available
            if 'equation' in rel:
                eq['latex'] = rel['equation'].get('metadata', {}).get('latex')
                eq['description'] = rel['equation'].get('metadata', {}).get('description')

            equations.append(eq)

        return equations

    def _extract_cross_references(self, cross_refs: List[Dict]) -> List[Dict]:
        """Extract cross-references to this table."""
        references = []

        for rel in cross_refs:
            ref = {
                'source': rel.get('source'),
                'reference_phrase': rel.get('reference_phrase', {}).get('raw_text'),
                'context': rel.get('context_snippet', {}).get('before', '')
            }
            references.append(ref)

        return references

    def _extract_citations(self, citations: List[Dict]) -> List[Dict]:
        """Extract citations from this table."""
        cites = []

        for rel in citations:
            cite = {
                'ref_id': rel.get('target') if isinstance(rel.get('target'), str) else rel.get('target', [])[0],
                'citation_marker': rel.get('citation_context', {}).get('citation_marker')
            }
            cites.append(cite)

        return cites

    def _extract_semantic_tags(self, entity_id: str, relationships: List[Dict]) -> List[str]:
        """Extract semantic tags."""
        tags = set()

        for rel in relationships:
            if 'table' in rel:
                table_tags = rel['table'].get('metadata', {}).get('semantic_tags', [])
                tags.update(table_tags)

        return list(tags)

    def _create_embedding_metadata(
        self,
        entity_id: str,
        relationship_count: int,
        entity_type: str
    ) -> Dict:
        """Create embedding metadata."""
        return {
            'chunk_id': entity_id.replace(':', '_'),
            'doc_id': self.config.get('embedding_metadata', {}).get('document', {}).get('default_doc_id', 'unknown'),
            'entity_type': entity_type,
            'confidence': 0.90,
            'token_count_estimate': 0,
            'creation_date': datetime.now().isoformat(),
            'relationships_count': relationship_count
        }


class ConceptBundleBuilder:
    """
    Builder for concept micro-bundles (variable definitions).

    Creates self-contained cards combining:
    - Variable definition (symbol, name, units, description)
    - All equations using this variable
    - Usage examples
    - Related concepts
    """

    def __init__(self, config: Dict):
        """Initialize concept bundle builder."""
        self.config = config
        self.bundle_config = config['content_inclusion']['concept_bundle']
        self.min_usage_count = config['bundle_types']['concept']['min_usage_count']

        logger.info(f"ConceptBundleBuilder initialized (min usage: {self.min_usage_count})")

    def should_create_bundle(self, relationships: List[Dict]) -> bool:
        """
        Check if concept bundle should be created.
        Only create for high-value concepts (used in 3+ equations).
        """
        usage_count = len([r for r in relationships if r.get('edge_type') == 'USES_VARIABLE'])
        return usage_count >= self.min_usage_count

    def build_bundle(
        self,
        entity_id: str,
        relationships: List[Dict],
        entity_data: Optional[Dict] = None
    ) -> Optional[MicroBundle]:
        """Build complete concept bundle."""
        if not self.should_create_bundle(relationships):
            logger.debug(f"Skipping concept bundle for {entity_id} (usage count too low)")
            return None

        logger.debug(f"Building concept bundle for {entity_id}")

        # Extract relationships
        var_defs = [r for r in relationships if r.get('edge_type') == 'DEFINES_VARIABLE' and r.get('target') == entity_id]
        uses = [r for r in relationships if r.get('edge_type') == 'USES_VARIABLE']

        # Build content
        content = {
            'concept': self._extract_concept_content(entity_id, var_defs, entity_data)
        }

        if self.bundle_config['include_all_equations']:
            content['used_in_equations'] = self._extract_equation_usage(uses)

        # Usage guidance (Phase 3)
        usage_guidance = {}

        # Semantic tags
        semantic_tags = self._extract_semantic_tags(entity_id, relationships)

        # Embedding metadata
        embedding_metadata = self._create_embedding_metadata(
            entity_id,
            len(relationships),
            "concept"
        )

        # Create bundle
        bundle = MicroBundle(
            bundle_id=f"bundle:{entity_id}_complete",
            bundle_type="concept",
            entity_id=entity_id,
            content=content,
            usage_guidance=usage_guidance,
            semantic_tags=semantic_tags,
            embedding_metadata=embedding_metadata
        )

        logger.debug(f"Created concept bundle: {bundle.bundle_id}, ~{bundle.estimate_token_count()} tokens")

        return bundle

    def _extract_concept_content(
        self,
        entity_id: str,
        var_defs: List[Dict],
        entity_data: Optional[Dict]
    ) -> Dict:
        """Extract concept (variable) primary content."""
        # From entity_data if available
        if entity_data:
            return {
                'variable_id': entity_id,
                'symbol': entity_data.get('symbol'),
                'name': entity_data.get('name'),
                'definition': entity_data.get('definition'),
                'units': entity_data.get('units')
            }

        # From variable definitions
        if var_defs:
            var_def = var_defs[0]  # Use first definition
            var_data = var_def.get('variable', {})
            return {
                'variable_id': entity_id,
                'symbol': var_data.get('symbol'),
                'name': var_data.get('name'),
                'definition': var_data.get('definition'),
                'units': var_data.get('units')
            }

        # Fallback
        return {
            'variable_id': entity_id,
            'symbol': None,
            'name': None,
            'definition': None,
            'units': None
        }

    def _extract_equation_usage(self, uses: List[Dict]) -> List[Dict]:
        """Extract equations using this variable."""
        equations = []

        for rel in uses:
            eq = {
                'entity_id': rel.get('source'),
                'role': rel.get('variable', {}).get('role', 'unknown')
            }

            # Add equation info if available
            if 'equation' in rel:
                eq['latex'] = rel['equation'].get('metadata', {}).get('latex')

            equations.append(eq)

        return equations

    def _extract_semantic_tags(self, entity_id: str, relationships: List[Dict]) -> List[str]:
        """Extract semantic tags."""
        tags = set()

        for rel in relationships:
            if 'variable' in rel:
                var_tags = rel['variable'].get('semantic_tags', [])
                tags.update(var_tags)

        return list(tags)

    def _create_embedding_metadata(
        self,
        entity_id: str,
        relationship_count: int,
        entity_type: str
    ) -> Dict:
        """Create embedding metadata."""
        return {
            'chunk_id': entity_id.replace(':', '_'),
            'doc_id': self.config.get('embedding_metadata', {}).get('document', {}).get('default_doc_id', 'unknown'),
            'entity_type': entity_type,
            'confidence': 0.90,
            'token_count_estimate': 0,
            'creation_date': datetime.now().isoformat(),
            'relationships_count': relationship_count
        }
