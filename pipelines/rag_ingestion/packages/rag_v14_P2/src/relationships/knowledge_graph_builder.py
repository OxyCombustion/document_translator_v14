# -*- coding: utf-8 -*-
"""
Knowledge Graph Builder - Constructs typed-edge multi-digraph from relationships.

This module builds a NetworkX MultiDiGraph from relationship JSON files, creating
a knowledge graph with typed nodes and typed edges suitable for:
- Graph database import (Neo4j, ArangoDB)
- Visualization (Gephi, Cytoscape)
- Graph analytics (PageRank, community detection)
- RAG retrieval (multi-hop queries)

Architecture:
- Single Responsibility: Graph construction only (no export logic)
- Dependency Injection: Relationships injected via constructor
- Open/Closed: Extensible through node/edge type registration
- Low Coupling: Uses standard NetworkX interface
- High Cohesion: All methods focused on graph building

Key Features:
- Typed nodes (Equation, Table, Figure, Variable, Reference, Chunk)
- Typed edges (DEFINES_VARIABLE, REQUIRES_DATA_FROM, REFERENCES, CITES, USES_VARIABLE)
- Metadata preservation (confidence, validation_status, page, section)
- Bi-directional edge support (source → target, target ← source backlinks)
- Graph integrity validation (no dangling edges, all nodes defined)

Author: V12 Development Team
Created: 2025-11-06
Last Updated: 2025-11-06
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
import json
import logging

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

# Third-party imports
import networkx as nx

# Configure logging
logger = logging.getLogger(__name__)


# ========== Custom Exceptions ==========

class KnowledgeGraphError(Exception):
    """Base exception for knowledge graph errors."""
    pass


class GraphIntegrityError(KnowledgeGraphError):
    """Raised when graph integrity check fails."""
    pass


# ========== Data Structures ==========

@dataclass
class GraphNode:
    """
    Typed node in knowledge graph.

    Attributes:
        node_id: Unique namespaced ID (e.g., "eq:9", "tbl:3")
        node_type: Type (equation, table, figure, variable, reference, chunk)
        metadata: Additional properties (page, section, title, latex, etc.)
    """
    node_id: str
    node_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for NetworkX node attributes."""
        return {
            'id': self.node_id,
            'type': self.node_type,
            **self.metadata
        }


@dataclass
class GraphEdge:
    """
    Typed edge in knowledge graph.

    Attributes:
        source: Source node ID (namespaced)
        target: Target node ID (namespaced)
        edge_type: Relationship type (DEFINES_VARIABLE, REQUIRES_DATA_FROM, etc.)
        metadata: Additional properties (confidence, validation_status, etc.)
    """
    source: str
    target: str
    edge_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for NetworkX edge attributes."""
        return {
            'type': self.edge_type,
            **self.metadata
        }


# ========== Knowledge Graph Builder ==========

class KnowledgeGraphBuilder:
    """
    Builds typed-edge NetworkX MultiDiGraph from relationship files.

    The knowledge graph represents semantic relationships between document entities:
    - Nodes: Equations, tables, figures, variables, references, chunks
    - Edges: DEFINES_VARIABLE, REQUIRES_DATA_FROM, REFERENCES, CITES, etc.
    - Metadata: Confidence scores, validation status, page/section info

    Example:
        >>> builder = KnowledgeGraphBuilder()
        >>> builder.load_relationships_from_files(relationship_dir)
        >>> graph = builder.build_graph()
        >>> print(f"Graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    """

    def __init__(self):
        """Initialize knowledge graph builder."""
        self.graph = nx.MultiDiGraph()
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []

        # Statistics
        self.stats = {
            'nodes_by_type': {},
            'edges_by_type': {},
            'integrity_checks': []
        }

        logger.info("Knowledge Graph Builder initialized")

    def load_relationships_from_files(
        self,
        relationship_dir: Path
    ) -> None:
        """
        Load all relationship JSON files from directory.

        Args:
            relationship_dir: Directory containing relationship JSON files
                Expected files:
                - variable_definitions.json
                - data_dependencies.json
                - cross_references.json
                - citations.json

        Raises:
            KnowledgeGraphError: If loading fails
        """
        try:
            relationship_dir = Path(relationship_dir)

            # Load variable definitions
            var_def_file = relationship_dir / 'variable_definitions.json'
            if var_def_file.exists():
                with open(var_def_file, 'r', encoding='utf-8') as f:
                    var_defs = json.load(f)
                self._load_variable_definitions(var_defs)
                logger.info(f"Loaded {len(var_defs)} variable definitions")

            # Load data dependencies
            data_dep_file = relationship_dir / 'data_dependencies.json'
            if data_dep_file.exists():
                with open(data_dep_file, 'r', encoding='utf-8') as f:
                    data_deps = json.load(f)
                self._load_data_dependencies(data_deps)
                logger.info(f"Loaded {len(data_deps)} data dependencies")

            # Load cross-references
            xref_file = relationship_dir / 'cross_references.json'
            if xref_file.exists():
                with open(xref_file, 'r', encoding='utf-8') as f:
                    xrefs = json.load(f)
                self._load_cross_references(xrefs)
                logger.info(f"Loaded {len(xrefs)} cross-references")

            # Load citations
            cite_file = relationship_dir / 'citations.json'
            if cite_file.exists():
                with open(cite_file, 'r', encoding='utf-8') as f:
                    cites = json.load(f)
                self._load_citations(cites)
                logger.info(f"Loaded {len(cites)} citations")

        except Exception as e:
            raise KnowledgeGraphError(f"Failed to load relationships: {e}") from e

    def _load_variable_definitions(
        self,
        var_defs: List[Dict[str, Any]]
    ) -> None:
        """Load variable definition relationships."""
        for var_def in var_defs:
            # Add variable node
            var_id = var_def['variable_id']
            self._add_node(
                node_id=var_id,
                node_type='variable',
                metadata={
                    'symbol': var_def.get('symbol', ''),
                    'name': var_def.get('name', ''),
                    'definition': var_def.get('definition_text', ''),
                    'units': var_def.get('units', {}),
                    'page': var_def.get('page', 0),
                    'section': var_def.get('section', '')
                }
            )

            # Add edges from defining location to variable
            if 'source' in var_def:
                source_id = var_def['source']
                self._add_edge(
                    source=source_id,
                    target=var_id,
                    edge_type='DEFINES_VARIABLE',
                    metadata={
                        'confidence': var_def.get('confidence', 1.0),
                        'validation_status': var_def.get('validation_status', 'unknown')
                    }
                )

    def _load_data_dependencies(
        self,
        data_deps: List[Dict[str, Any]]
    ) -> None:
        """Load data dependency relationships."""
        for data_dep in data_deps:
            source = data_dep['source']
            target = data_dep['target']

            # Add edge: equation REQUIRES_DATA_FROM table
            self._add_edge(
                source=source,
                target=target,
                edge_type='REQUIRES_DATA_FROM',
                metadata={
                    'variable_linkage': data_dep.get('variable_linkage', []),
                    'confidence': data_dep.get('confidence', 1.0),
                    'validation_status': data_dep.get('validation_status', 'unknown')
                }
            )

            # Add reverse edge: table PROVIDES_DATA_FOR equation
            self._add_edge(
                source=target,
                target=source,
                edge_type='PROVIDES_DATA_FOR',
                metadata={
                    'variable_linkage': data_dep.get('variable_linkage', []),
                    'confidence': data_dep.get('confidence', 1.0)
                }
            )

    def _load_cross_references(
        self,
        xrefs: List[Dict[str, Any]]
    ) -> None:
        """Load cross-reference relationships."""
        for xref in xrefs:
            source = xref['source_location']['entity_id']
            target = xref['target']['entity_id']

            # Add edge: source REFERENCES target
            self._add_edge(
                source=source,
                target=target,
                edge_type='REFERENCES',
                metadata={
                    'reference_phrase': xref['reference_phrase']['raw_text'],
                    'intent': xref.get('intent', 'unknown'),
                    'confidence': xref.get('confidence', 1.0),
                    'page': xref['source_location'].get('page', 0)
                }
            )

    def _load_citations(
        self,
        cites: List[Dict[str, Any]]
    ) -> None:
        """Load citation relationships."""
        for cite in cites:
            source = cite['source_location']['entity_id']
            target = cite['citation']['reference_id']

            # Add reference node if not exists
            self._add_node(
                node_id=target,
                node_type='reference',
                metadata=cite['citation'].get('metadata', {})
            )

            # Add edge: source CITES reference
            self._add_edge(
                source=source,
                target=target,
                edge_type='CITES',
                metadata={
                    'citation_marker': cite['citation_marker']['raw_text'],
                    'context': cite.get('context', ''),
                    'confidence': cite.get('confidence', 1.0),
                    'page': cite['source_location'].get('page', 0)
                }
            )

    def _add_node(
        self,
        node_id: str,
        node_type: str,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Add node to graph (if not already present).

        Args:
            node_id: Unique namespaced ID
            node_type: Type (equation, table, figure, etc.)
            metadata: Additional properties
        """
        if node_id not in self.nodes:
            node = GraphNode(
                node_id=node_id,
                node_type=node_type,
                metadata=metadata
            )
            self.nodes[node_id] = node

            # Update statistics
            if node_type not in self.stats['nodes_by_type']:
                self.stats['nodes_by_type'][node_type] = 0
            self.stats['nodes_by_type'][node_type] += 1

    def _add_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Add edge to graph.

        Args:
            source: Source node ID
            target: Target node ID
            edge_type: Relationship type
            metadata: Additional properties
        """
        edge = GraphEdge(
            source=source,
            target=target,
            edge_type=edge_type,
            metadata=metadata
        )
        self.edges.append(edge)

        # Update statistics
        if edge_type not in self.stats['edges_by_type']:
            self.stats['edges_by_type'][edge_type] = 0
        self.stats['edges_by_type'][edge_type] += 1

    def build_graph(self) -> nx.MultiDiGraph:
        """
        Build NetworkX MultiDiGraph from loaded relationships.

        Returns:
            NetworkX MultiDiGraph with typed nodes and edges

        Raises:
            GraphIntegrityError: If graph integrity check fails
        """
        logger.info("Building knowledge graph...")

        # Add all nodes
        for node_id, node in self.nodes.items():
            self.graph.add_node(node_id, **node.to_dict())

        # Add all edges
        for edge in self.edges:
            self.graph.add_edge(
                edge.source,
                edge.target,
                **edge.to_dict()
            )

        # Validate graph integrity
        self._validate_graph_integrity()

        logger.info(f"✓ Graph built: {self.graph.number_of_nodes()} nodes, "
                   f"{self.graph.number_of_edges()} edges")

        return self.graph

    def _validate_graph_integrity(self) -> None:
        """
        Validate graph integrity (no dangling edges).

        Raises:
            GraphIntegrityError: If validation fails
        """
        issues = []

        # Check for dangling edges
        all_nodes = set(self.nodes.keys())
        for edge in self.edges:
            if edge.source not in all_nodes:
                issues.append(f"Dangling edge source: {edge.source}")
            if edge.target not in all_nodes:
                issues.append(f"Dangling edge target: {edge.target}")

        if issues:
            error_msg = f"Graph integrity check failed: {len(issues)} issues\n" + \
                       "\n".join(issues[:10])  # Show first 10 issues
            raise GraphIntegrityError(error_msg)

        self.stats['integrity_checks'].append({
            'timestamp': '2025-11-06',
            'status': 'pass',
            'issues': []
        })

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get graph statistics.

        Returns:
            Dictionary with graph metrics:
            - nodes_by_type: Count of each node type
            - edges_by_type: Count of each edge type
            - graph_density: Edge density
            - average_degree: Average node degree
            - connected_components: Number of connected components
        """
        if self.graph.number_of_nodes() == 0:
            return {
                'nodes': 0,
                'edges': 0,
                'error': 'Graph not built yet'
            }

        # Basic counts
        stats = {
            'nodes': {
                'total': self.graph.number_of_nodes(),
                'by_type': self.stats['nodes_by_type']
            },
            'edges': {
                'total': self.graph.number_of_edges(),
                'by_type': self.stats['edges_by_type']
            }
        }

        # Graph metrics
        try:
            stats['metrics'] = {
                'density': nx.density(self.graph),
                'average_degree': sum(dict(self.graph.degree()).values()) / self.graph.number_of_nodes(),
                'connected_components': nx.number_weakly_connected_components(self.graph)
            }
        except Exception as e:
            logger.warning(f"Could not compute graph metrics: {e}")
            stats['metrics'] = {'error': str(e)}

        return stats


# ========== Main Entry Point ==========

def main():
    """Main entry point for testing."""
    # Test with sample data
    relationship_dir = Path("relationships")
    if not relationship_dir.exists():
        print(f"❌ Relationship directory not found: {relationship_dir}")
        return 1

    builder = KnowledgeGraphBuilder()
    builder.load_relationships_from_files(relationship_dir)
    graph = builder.build_graph()

    stats = builder.get_statistics()
    print("\n" + "=" * 80)
    print("KNOWLEDGE GRAPH STATISTICS")
    print("=" * 80)
    print(json.dumps(stats, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
