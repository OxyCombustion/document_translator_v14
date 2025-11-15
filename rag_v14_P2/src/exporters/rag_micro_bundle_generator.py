# -*- coding: utf-8 -*-
"""
RAG Micro-Bundle Generator
Aggregates semantic relationships into self-contained embedding-ready cards.

This module creates micro-bundles for RAG (Retrieval-Augmented Generation) systems:
- Equation cards: Complete equation + variables + data sources + citations
- Table cards: Complete table + equations using it + cross-references
- Concept cards: Variable definition + all equations using it + examples

Each bundle is optimized for embedding (384-768 tokens) and contains everything
needed to answer questions about that entity without requiring graph traversal.

Architecture:
- Phase 1: Relationship Aggregator (load and index relationships)
- Phase 2: Bundle Builders (create typed bundles)
- Phase 3: Context Enhancement (add usage guidance)
- Phase 4: JSONL Export (streaming format with metadata)

Dependencies:
- Relationship JSON files (4 files in relationships/)
- SemanticRegistry (variable lookups)
- Configuration: config/rag/micro_bundle_config.yaml
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
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

import yaml

try:
    # Try absolute import first
    from src.exporters.bundle_builders import (
        EquationBundleBuilder,
        TableBundleBuilder,
        ConceptBundleBuilder,
        MicroBundle
    )
except ModuleNotFoundError:
    # Fall back to relative import when running as script
    from bundle_builders import (
        EquationBundleBuilder,
        TableBundleBuilder,
        ConceptBundleBuilder,
        MicroBundle
    )

logger = logging.getLogger(__name__)


# Custom Exceptions
class MicroBundleError(Exception):
    """Base exception for micro-bundle generation errors."""
    pass


class RelationshipLoadError(MicroBundleError):
    """Raised when relationship files cannot be loaded."""
    pass


class BundleValidationError(MicroBundleError):
    """Raised when bundle validation fails."""
    pass


# Data Structures
@dataclass
class RelationshipIndex:
    """Index of all relationships organized by entity."""

    # entity_id -> List[relationships where entity is source]
    by_source: Dict[str, List[Dict]] = field(default_factory=lambda: defaultdict(list))

    # entity_id -> List[relationships where entity is target]
    by_target: Dict[str, List[Dict]] = field(default_factory=lambda: defaultdict(list))

    # entity_id -> List[all relationships involving entity]
    by_entity: Dict[str, List[Dict]] = field(default_factory=lambda: defaultdict(list))

    # relationship_type -> count
    type_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Total relationship count
    total_relationships: int = 0


@dataclass
class BundleStatistics:
    """Statistics about generated bundles."""

    total_bundles: int = 0
    bundles_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Token counts
    average_token_count: float = 0.0
    min_token_count: int = 0
    max_token_count: int = 0
    token_distribution: Dict[str, int] = field(default_factory=dict)  # bin_label -> count

    # Relationships
    average_relationships_per_bundle: float = 0.0
    relationship_coverage: float = 0.0  # % of relationships included

    # Validation
    bundles_exceeding_max: int = 0
    bundles_below_min: int = 0
    bundles_optimal: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_bundles": self.total_bundles,
            "bundles_by_type": dict(self.bundles_by_type),
            "token_counts": {
                "average": self.average_token_count,
                "min": self.min_token_count,
                "max": self.max_token_count,
                "distribution": self.token_distribution
            },
            "relationships": {
                "average_per_bundle": self.average_relationships_per_bundle,
                "coverage_percentage": self.relationship_coverage
            },
            "validation": {
                "exceeding_max": self.bundles_exceeding_max,
                "below_min": self.bundles_below_min,
                "optimal_range": self.bundles_optimal
            }
        }


class RelationshipAggregator:
    """
    Phase 1: Load and index all relationship JSON files.

    Responsibilities:
    - Load 4 relationship JSON files
    - Build relationship index (entity_id -> relationships)
    - Group relationships by source and target entity
    - Provide lookup methods for bundle builders
    """

    def __init__(self, config: Dict):
        """
        Initialize relationship aggregator.

        Args:
            config: Configuration dictionary from YAML
        """
        self.config = config
        self.relationship_sources = config['relationship_sources']
        self.index = RelationshipIndex()

        # Loaded relationships by type
        self.variable_definitions: List[Dict] = []
        self.data_dependencies: List[Dict] = []
        self.cross_references: List[Dict] = []
        self.citations: List[Dict] = []

        logger.info("RelationshipAggregator initialized")

    def load_all_relationships(self) -> RelationshipIndex:
        """
        Load all relationship files and build index.

        Returns:
            RelationshipIndex with complete relationship data

        Raises:
            RelationshipLoadError: If files cannot be loaded
        """
        logger.info("Loading all relationship files...")

        # Load each relationship type
        if self.relationship_sources['variable_definitions']['enabled']:
            self.variable_definitions = self._load_file(
                self.relationship_sources['variable_definitions']['file'],
                'variable_definitions'
            )

        if self.relationship_sources['data_dependencies']['enabled']:
            self.data_dependencies = self._load_file(
                self.relationship_sources['data_dependencies']['file'],
                'data_dependencies'
            )

        if self.relationship_sources['cross_references']['enabled']:
            self.cross_references = self._load_file(
                self.relationship_sources['cross_references']['file'],
                'cross_references'
            )

        if self.relationship_sources['citations']['enabled']:
            self.citations = self._load_file(
                self.relationship_sources['citations']['file'],
                'citations'
            )

        # Build index
        self._build_index()

        logger.info(f"Loaded {self.index.total_relationships} relationships total")
        logger.info(f"Relationship types: {dict(self.index.type_counts)}")

        return self.index

    def _load_file(self, filepath: str, rel_type: str) -> List[Dict]:
        """
        Load single relationship JSON file.

        Args:
            filepath: Path to JSON file
            rel_type: Relationship type for logging

        Returns:
            List of relationship dictionaries

        Raises:
            RelationshipLoadError: If file cannot be loaded
        """
        path = Path(filepath)

        if not path.exists():
            logger.warning(f"Relationship file not found: {filepath}")
            return []

        try:
            with open(path, 'r', encoding='utf-8') as f:
                relationships = json.load(f)

            logger.info(f"Loaded {len(relationships)} {rel_type} relationships")
            return relationships

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in {filepath}: {e}"
            logger.error(error_msg)
            raise RelationshipLoadError(error_msg)
        except Exception as e:
            error_msg = f"Failed to load {filepath}: {e}"
            logger.error(error_msg)
            raise RelationshipLoadError(error_msg)

    def _build_index(self):
        """Build relationship index from loaded data."""
        logger.info("Building relationship index...")

        # Index all relationship types
        all_relationships = (
            self.variable_definitions +
            self.data_dependencies +
            self.cross_references +
            self.citations
        )

        for rel in all_relationships:
            # Extract source and target
            source = rel.get('source')
            target = rel.get('target')
            edge_type = rel.get('edge_type', 'UNKNOWN')

            # Handle target as list (e.g., citations with multiple refs)
            targets = [target] if not isinstance(target, list) else target

            # Index by source
            if source:
                self.index.by_source[source].append(rel)
                self.index.by_entity[source].append(rel)

            # Index by target(s)
            for t in targets:
                if t:
                    self.index.by_target[t].append(rel)
                    self.index.by_entity[t].append(rel)

            # Count by type
            self.index.type_counts[edge_type] += 1
            self.index.total_relationships += 1

        logger.info(f"Indexed {self.index.total_relationships} relationships")
        logger.info(f"Entities with relationships: {len(self.index.by_entity)}")

    def get_relationships_for_entity(self, entity_id: str) -> List[Dict]:
        """
        Get all relationships involving an entity.

        Args:
            entity_id: Entity ID (e.g., "eq:9", "tbl:3")

        Returns:
            List of relationships where entity is source or target
        """
        return self.index.by_entity.get(entity_id, [])

    def get_source_relationships(self, entity_id: str) -> List[Dict]:
        """Get relationships where entity is source."""
        return self.index.by_source.get(entity_id, [])

    def get_target_relationships(self, entity_id: str) -> List[Dict]:
        """Get relationships where entity is target."""
        return self.index.by_target.get(entity_id, [])

    def get_entities_with_relationships(self) -> Set[str]:
        """Get set of all entity IDs that have relationships."""
        return set(self.index.by_entity.keys())

    def get_relationship_types(self) -> Dict[str, int]:
        """Get count of relationships by type."""
        return dict(self.index.type_counts)


class MicroBundleExporter:
    """
    Phase 4: Export bundles to JSONL format with optimization.

    Responsibilities:
    - Validate token counts
    - Optimize oversized bundles (>1024 tokens)
    - Export to JSONL format (one bundle per line)
    - Generate comprehensive statistics
    - Add embedding metadata to each bundle
    """

    def __init__(self, config: Dict):
        """
        Initialize micro-bundle exporter.

        Args:
            config: Configuration dictionary from YAML
        """
        self.config = config
        self.bundle_size_config = config.get('bundle_size', {})
        self.statistics_config = config.get('statistics', {})

        # Token constraints
        self.target_min = self.bundle_size_config.get('target_min_tokens', 384)
        self.target_max = self.bundle_size_config.get('target_max_tokens', 768)
        self.absolute_max = self.bundle_size_config.get('absolute_max_tokens', 1024)
        self.chars_per_token = self.bundle_size_config.get('chars_per_token', 4)

        logger.info(f"MicroBundleExporter initialized (target: {self.target_min}-{self.target_max} tokens)")

    def export_to_jsonl(
        self,
        bundles: List[Any],
        output_path: Path
    ) -> Dict[str, Any]:
        """
        Export bundles to JSONL format.

        Steps:
        1. Validate each bundle
        2. Optimize oversized bundles (> 1024 tokens)
        3. Add embedding metadata
        4. Write to JSONL (one bundle per line)
        5. Generate statistics

        Args:
            bundles: List of MicroBundle objects
            output_path: Path to output JSONL file

        Returns:
            Statistics dictionary
        """
        logger.info(f"Exporting {len(bundles)} bundles to JSONL: {output_path}")

        optimized_bundles = []
        token_counts = []
        relationship_counts = []

        # Process each bundle
        for bundle in bundles:
            try:
                # Estimate token count
                token_count = self._estimate_token_count(bundle)

                # Optimize if oversized
                if token_count > self.absolute_max:
                    logger.debug(f"Optimizing oversized bundle {bundle.bundle_id}: {token_count} tokens")
                    bundle = self._optimize_bundle_size(bundle)
                    token_count = self._estimate_token_count(bundle)

                # Update embedding metadata with token count
                bundle.embedding_metadata['token_count_estimate'] = token_count

                # Track statistics
                token_counts.append(token_count)
                rel_count = bundle.embedding_metadata.get('relationships_count', 0)
                relationship_counts.append(rel_count)

                optimized_bundles.append(bundle)

            except Exception as e:
                logger.error(f"Failed to process bundle {bundle.bundle_id}: {e}")
                continue

        # Write to JSONL
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            for bundle in optimized_bundles:
                # Convert to dict and write as single line JSON
                bundle_dict = bundle.to_dict()
                json_line = json.dumps(bundle_dict, ensure_ascii=False)
                f.write(json_line + '\n')

        logger.info(f"✅ Exported {len(optimized_bundles)} bundles to {output_path}")

        # Generate statistics
        statistics = self._generate_statistics(optimized_bundles, token_counts, relationship_counts)

        return statistics

    def _estimate_token_count(self, bundle: Any) -> int:
        """
        Estimate token count for this bundle.
        Uses rough approximation: 4 chars per token.

        Args:
            bundle: MicroBundle object

        Returns:
            Estimated token count
        """
        json_str = json.dumps(bundle.to_dict(), ensure_ascii=False)
        return len(json_str) // self.chars_per_token

    def _optimize_bundle_size(self, bundle: Any) -> Any:
        """
        Optimize bundle if > 1024 tokens.

        Strategy:
        - Keep core content (equation, table, definition)
        - Summarize relationships (keep count, sample 2-3)
        - Truncate long text fields
        - Remove low-confidence relationships

        Args:
            bundle: MicroBundle to optimize

        Returns:
            Optimized bundle ≤ 1024 tokens
        """
        summarization_config = self.bundle_size_config.get('summarization', {})

        # Core content always kept
        # Optimize content sections
        content = bundle.content.copy()

        # Limit variables
        if 'variables' in content:
            max_vars = summarization_config.get('max_variable_descriptions', 10)
            if len(content['variables']) > max_vars:
                content['variables'] = content['variables'][:max_vars]
                content['variables_truncated'] = True

        # Limit cross-references
        if 'cross_references' in content:
            max_refs = summarization_config.get('max_cross_references', 5)
            if len(content['cross_references']) > max_refs:
                content['cross_references'] = content['cross_references'][:max_refs]
                content['cross_references_truncated'] = True

        # Limit citations
        if 'citations' in content:
            max_cites = summarization_config.get('max_citation_details', 3)
            if len(content['citations']) > max_cites:
                content['citations'] = content['citations'][:max_cites]
                content['citations_truncated'] = True

        # Truncate context snippets
        max_context = summarization_config.get('truncate_context_to_chars', 500)
        for ref in content.get('cross_references', []):
            if 'context' in ref and len(ref['context']) > max_context:
                ref['context'] = ref['context'][:max_context] + '...'

        # Update bundle
        bundle.content = content

        # If still too large, truncate core content
        current_size = self._estimate_token_count(bundle)
        if current_size > self.absolute_max:
            # Truncate equation latex if very long
            if 'equation' in content and 'latex' in content['equation']:
                latex = content['equation']['latex']
                if len(latex) > 1000:  # Truncate very long latex
                    content['equation']['latex'] = latex[:1000] + '...'
                    content['equation']['latex_truncated'] = True

            # Remove variable definitions if needed
            if 'variables' in content and len(content['variables']) > 5:
                content['variables'] = content['variables'][:5]
                content['variables_truncated'] = True

            bundle.content = content

        logger.debug(f"Optimized bundle {bundle.bundle_id} to {self._estimate_token_count(bundle)} tokens")

        return bundle

    def _generate_statistics(
        self,
        bundles: List[Any],
        token_counts: List[int],
        relationship_counts: List[int]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive statistics.

        Returns: {
            "total_bundles": int,
            "by_type": {"equation": int, "table": int, "concept": int},
            "token_stats": {
                "mean": float,
                "median": float,
                "min": int,
                "max": int,
                "in_optimal_range": int,  # 384-768
                "oversized": int           # > 1024
            },
            "relationships_stats": {
                "mean_per_bundle": float,
                "total_relationships": int,
                "by_type": {...}
            }
        }

        Args:
            bundles: List of bundles
            token_counts: List of token counts
            relationship_counts: List of relationship counts

        Returns:
            Statistics dictionary
        """
        if not bundles:
            # Return empty statistics structure
            return {
                'total_bundles': 0,
                'bundles_by_type': {},
                'token_stats': {
                    'mean': 0,
                    'median': 0,
                    'min': 0,
                    'max': 0,
                    'in_optimal_range': 0,
                    'below_min': 0,
                    'oversized': 0,
                    'distribution': {
                        'too_small': 0,
                        'optimal': 0,
                        'acceptable': 0,
                        'too_large': 0
                    }
                },
                'relationships_stats': {
                    'mean_per_bundle': 0,
                    'total_relationships': 0
                },
                'validation': {
                    'exceeding_max': 0,
                    'below_min': 0,
                    'optimal_range': 0
                }
            }

        # Bundle counts by type
        bundles_by_type = defaultdict(int)
        for bundle in bundles:
            bundles_by_type[bundle.bundle_type] += 1

        # Token statistics
        token_counts_sorted = sorted(token_counts)
        n = len(token_counts)
        median_token = token_counts_sorted[n // 2] if n > 0 else 0

        in_optimal = sum(1 for t in token_counts if self.target_min <= t <= self.target_max)
        below_min = sum(1 for t in token_counts if t < self.target_min)
        above_max = sum(1 for t in token_counts if t > self.absolute_max)

        # Token distribution by bins
        token_bins = self.statistics_config.get('token_bins', [
            {'min': 0, 'max': 384, 'label': 'too_small'},
            {'min': 384, 'max': 768, 'label': 'optimal'},
            {'min': 768, 'max': 1024, 'label': 'acceptable'},
            {'min': 1024, 'max': 9999, 'label': 'too_large'}
        ])

        distribution = {}
        for bin_def in token_bins:
            count = sum(1 for t in token_counts if bin_def['min'] <= t < bin_def['max'])
            distribution[bin_def['label']] = count

        # Relationship statistics
        total_relationships = sum(relationship_counts)
        avg_relationships = total_relationships / len(bundles) if bundles else 0

        statistics = {
            'total_bundles': len(bundles),
            'bundles_by_type': dict(bundles_by_type),
            'token_stats': {
                'mean': sum(token_counts) / len(token_counts) if token_counts else 0,
                'median': median_token,
                'min': min(token_counts) if token_counts else 0,
                'max': max(token_counts) if token_counts else 0,
                'in_optimal_range': in_optimal,
                'below_min': below_min,
                'oversized': above_max,
                'distribution': distribution
            },
            'relationships_stats': {
                'mean_per_bundle': avg_relationships,
                'total_relationships': total_relationships
            },
            'validation': {
                'exceeding_max': above_max,
                'below_min': below_min,
                'optimal_range': in_optimal
            }
        }

        return statistics


class MicroBundleGenerator:
    """
    Main generator for RAG micro-bundles.

    Coordinates all 4 phases:
    1. Relationship aggregation (RelationshipAggregator)
    2. Bundle building (delegated to bundle builders)
    3. Context enhancement (usage guidance, tags)
    4. JSONL export (streaming format)
    """

    def __init__(self, config_path: Path):
        """
        Initialize micro-bundle generator.

        Args:
            config_path: Path to micro_bundle_config.yaml
        """
        self.config_path = config_path
        self.config = self._load_config()

        # Components
        self.aggregator = RelationshipAggregator(self.config)
        self.statistics = BundleStatistics()

        # Bundle builders
        self.equation_builder = EquationBundleBuilder(self.config)
        self.table_builder = TableBundleBuilder(self.config)
        self.concept_builder = ConceptBundleBuilder(self.config)

        # Context enhancer (Phase 3)
        try:
            from src.exporters.context_enhancer import ContextEnhancer
            self.context_enhancer = ContextEnhancer(self.config)
        except ImportError:
            from context_enhancer import ContextEnhancer
            self.context_enhancer = ContextEnhancer(self.config)

        # Exporter (Phase 4)
        self.exporter = MicroBundleExporter(self.config)

        # Output directory
        self.output_dir = Path(self.config['output']['directory'])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"MicroBundleGenerator initialized with config: {config_path}")

    def _load_config(self) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info("Configuration loaded successfully")
            return config
        except Exception as e:
            error_msg = f"Failed to load config from {self.config_path}: {e}"
            logger.error(error_msg)
            raise MicroBundleError(error_msg)

    def generate_all_bundles(self) -> Dict:
        """
        Generate all micro-bundles (Phase 1-4 complete pipeline).

        Returns:
            Dictionary with statistics and output paths
        """
        logger.info("=" * 80)
        logger.info("Starting RAG Micro-Bundle Generation")
        logger.info("=" * 80)

        # Phase 1: Load and index relationships
        logger.info("\n[Phase 1] Loading relationships...")
        relationship_index = self.aggregator.load_all_relationships()

        logger.info(f"\nPhase 1 Complete:")
        logger.info(f"  - Total relationships: {relationship_index.total_relationships}")
        logger.info(f"  - Entities with relationships: {len(self.aggregator.get_entities_with_relationships())}")
        logger.info(f"  - Relationship types: {relationship_index.type_counts}")

        # Phase 2: Build micro-bundles
        logger.info("\n[Phase 2] Building micro-bundles...")
        bundles = self._build_all_bundles(relationship_index)

        logger.info(f"\nPhase 2 Complete:")
        logger.info(f"  - Total bundles: {len(bundles)}")
        logger.info(f"  - Equation bundles: {sum(1 for b in bundles if b.bundle_type == 'equation')}")
        logger.info(f"  - Table bundles: {sum(1 for b in bundles if b.bundle_type == 'table')}")
        logger.info(f"  - Concept bundles: {sum(1 for b in bundles if b.bundle_type == 'concept')}")

        # Phase 3: Context enhancement
        logger.info("\n[Phase 3] Enhancing bundles with usage guidance...")
        enhanced_bundles = self._enhance_all_bundles(bundles)

        logger.info(f"\nPhase 3 Complete:")
        logger.info(f"  - Bundles enhanced: {len(enhanced_bundles)}")
        logger.info(f"  - Average semantic tags: {sum(len(b.semantic_tags) for b in enhanced_bundles) / len(enhanced_bundles):.1f}")

        # Phase 4: JSONL export
        logger.info("\n[Phase 4] Exporting to JSONL format...")
        output_files = self.config['output']['files']
        jsonl_path = self.output_dir / output_files['micro_bundles']
        stats_path = self.output_dir / output_files['statistics']

        export_stats = self.exporter.export_to_jsonl(enhanced_bundles, jsonl_path)

        # Write statistics to file
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(export_stats, f, indent=2, ensure_ascii=False)

        logger.info(f"\nPhase 4 Complete:")
        logger.info(f"  - JSONL file: {jsonl_path}")
        logger.info(f"  - Statistics: {stats_path}")
        logger.info(f"  - Token stats: mean={export_stats['token_stats']['mean']:.0f}, "
                    f"median={export_stats['token_stats']['median']}, "
                    f"optimal={export_stats['token_stats']['in_optimal_range']}")

        # Return complete results
        result = {
            "phase_1_complete": True,
            "phase_2_complete": True,
            "phase_3_complete": True,
            "phase_4_complete": True,
            "relationships_loaded": relationship_index.total_relationships,
            "entities_indexed": len(self.aggregator.get_entities_with_relationships()),
            "relationship_types": dict(relationship_index.type_counts),
            "bundles_created": len(bundles),
            "bundles_enhanced": len(enhanced_bundles),
            "bundles_by_type": export_stats['bundles_by_type'],
            "token_stats": export_stats['token_stats'],
            "relationships_stats": export_stats['relationships_stats'],
            "output_files": {
                "jsonl": str(jsonl_path),
                "statistics": str(stats_path)
            }
        }

        return result

    def _build_all_bundles(self, relationship_index: RelationshipIndex) -> List[MicroBundle]:
        """
        Build all micro-bundles from relationship index.

        Args:
            relationship_index: Complete relationship index from Phase 1

        Returns:
            List of all generated bundles
        """
        bundles = []

        # Get all entities with relationships
        entities = self.aggregator.get_entities_with_relationships()

        logger.info(f"Building bundles for {len(entities)} entities...")

        # Categorize entities by type
        equations = [e for e in entities if e.startswith('eq:')]
        tables = [e for e in entities if e.startswith('tbl:')]
        variables = [e for e in entities if e.startswith('var:')]

        logger.info(f"  - {len(equations)} equations")
        logger.info(f"  - {len(tables)} tables")
        logger.info(f"  - {len(variables)} variables")

        # Build equation bundles
        if self.config['bundle_types']['equation']['enabled']:
            logger.info("Building equation bundles...")
            for entity_id in equations:
                relationships = self.aggregator.get_relationships_for_entity(entity_id)
                try:
                    bundle = self.equation_builder.build_bundle(entity_id, relationships)
                    bundles.append(bundle)
                except Exception as e:
                    logger.error(f"Failed to build equation bundle for {entity_id}: {e}")

        # Build table bundles
        if self.config['bundle_types']['table']['enabled']:
            logger.info("Building table bundles...")
            for entity_id in tables:
                relationships = self.aggregator.get_relationships_for_entity(entity_id)
                try:
                    bundle = self.table_builder.build_bundle(entity_id, relationships)
                    bundles.append(bundle)
                except Exception as e:
                    logger.error(f"Failed to build table bundle for {entity_id}: {e}")

        # Build concept bundles (only for high-value variables)
        if self.config['bundle_types']['concept']['enabled']:
            logger.info("Building concept bundles...")
            for entity_id in variables:
                relationships = self.aggregator.get_relationships_for_entity(entity_id)
                try:
                    bundle = self.concept_builder.build_bundle(entity_id, relationships)
                    if bundle:  # Only add if created (passes usage threshold)
                        bundles.append(bundle)
                except Exception as e:
                    logger.error(f"Failed to build concept bundle for {entity_id}: {e}")

        logger.info(f"Built {len(bundles)} total bundles")

        return bundles

    def _enhance_all_bundles(self, bundles: List[MicroBundle]) -> List[MicroBundle]:
        """
        Enhance all bundles with context (Phase 3).

        Args:
            bundles: List of bundles from Phase 2

        Returns:
            List of enhanced bundles
        """
        enhanced = []

        for bundle in bundles:
            try:
                if bundle.bundle_type == 'equation':
                    enhanced_bundle = self.context_enhancer.enhance_equation_bundle(bundle)
                elif bundle.bundle_type == 'table':
                    enhanced_bundle = self.context_enhancer.enhance_table_bundle(bundle)
                elif bundle.bundle_type == 'concept':
                    enhanced_bundle = self.context_enhancer.enhance_concept_bundle(bundle)
                else:
                    logger.warning(f"Unknown bundle type: {bundle.bundle_type}")
                    enhanced_bundle = bundle

                enhanced.append(enhanced_bundle)

            except Exception as e:
                logger.error(f"Failed to enhance bundle {bundle.bundle_id}: {e}")
                # Add unenhanced bundle
                enhanced.append(bundle)

        return enhanced


def main():
    """Example usage of MicroBundleGenerator."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    config_path = Path("config/rag/micro_bundle_config.yaml")

    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return

    generator = MicroBundleGenerator(config_path)
    result = generator.generate_all_bundles()

    print("\n" + "=" * 80)
    print("RAG MICRO-BUNDLE GENERATION COMPLETE (ALL 4 PHASES)")
    print("=" * 80)
    print(f"\n[Phase 1] Relationship Aggregation:")
    print(f"  ✅ Relationships loaded: {result['relationships_loaded']}")
    print(f"  ✅ Entities indexed: {result['entities_indexed']}")
    print(f"  ✅ Relationship types: {result['relationship_types']}")

    print(f"\n[Phase 2] Bundle Building:")
    print(f"  ✅ Bundles created: {result['bundles_created']}")
    print(f"  - Equation bundles: {result['bundles_by_type'].get('equation', 0)}")
    print(f"  - Table bundles: {result['bundles_by_type'].get('table', 0)}")
    print(f"  - Concept bundles: {result['bundles_by_type'].get('concept', 0)}")

    print(f"\n[Phase 3] Context Enhancement:")
    print(f"  ✅ Bundles enhanced: {result['bundles_enhanced']}")

    print(f"\n[Phase 4] JSONL Export:")
    print(f"  ✅ Output file: {result['output_files']['jsonl']}")
    print(f"  ✅ Statistics: {result['output_files']['statistics']}")
    print(f"\n📊 Token Statistics:")
    print(f"  - Mean: {result['token_stats']['mean']:.0f} tokens")
    print(f"  - Median: {result['token_stats']['median']} tokens")
    print(f"  - Min: {result['token_stats']['min']} tokens")
    print(f"  - Max: {result['token_stats']['max']} tokens")
    print(f"  - In optimal range (384-768): {result['token_stats']['in_optimal_range']}")
    print(f"  - Below min (<384): {result['token_stats']['below_min']}")
    print(f"  - Oversized (>1024): {result['token_stats']['oversized']}")
    print(f"\n📊 Distribution:")
    for label, count in result['token_stats']['distribution'].items():
        print(f"  - {label}: {count}")
    print(f"\n📊 Relationships:")
    print(f"  - Mean per bundle: {result['relationships_stats']['mean_per_bundle']:.1f}")
    print(f"  - Total relationships: {result['relationships_stats']['total_relationships']}")

    print("\n" + "=" * 80)
    print("✅ READY FOR RAG INGESTION")
    print("=" * 80)


if __name__ == "__main__":
    main()
