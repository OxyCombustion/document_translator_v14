#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Citation Graph Analyzer - Internal Corpus Citation Analysis

Analyzes citation relationships within document corpus to calculate
importance scores using PageRank and other graph algorithms.

Author: Claude Code
Date: 2025-10-13
Version: 1.0
"""

import sys
import os
import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set
from datetime import datetime
from dataclasses import dataclass, field, asdict
import networkx as nx
import numpy as np

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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DocumentNode:
    """Represents a document in the citation graph."""
    doc_id: str
    title: str
    doi: Optional[str] = None
    year: Optional[int] = None
    authors: List[str] = field(default_factory=list)
    venue: Optional[str] = None
    extracted: bool = False  # Whether we've extracted content from this doc
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CitationEdge:
    """Represents a citation relationship."""
    source_id: str  # Document doing the citing
    target_id: str  # Document being cited
    context: Optional[str] = None  # Citation context text
    section: Optional[str] = None  # Section where citation appears
    confidence: float = 1.0  # Confidence in citation extraction


@dataclass
class GraphMetrics:
    """Metrics calculated from citation graph."""
    pagerank: Dict[str, float] = field(default_factory=dict)
    in_degree: Dict[str, int] = field(default_factory=dict)
    out_degree: Dict[str, int] = field(default_factory=dict)
    hub_score: Dict[str, float] = field(default_factory=dict)
    authority_score: Dict[str, float] = field(default_factory=dict)
    clustering_coefficient: Dict[str, float] = field(default_factory=dict)
    betweenness_centrality: Dict[str, float] = field(default_factory=dict)


class CitationGraphAnalyzer:
    """
    Analyzes internal citation relationships within document corpus.

    Uses graph algorithms to identify important documents and calculate
    influence metrics based on citation patterns.
    """

    def __init__(
        self,
        db_path: Path = None,
        damping_factor: float = 0.85,
        max_iterations: int = 100,
        tolerance: float = 1e-6
    ):
        """
        Initialize citation graph analyzer.

        Args:
            db_path: Path to SQLite database for persistence
            damping_factor: PageRank damping factor (default 0.85)
            max_iterations: Max iterations for PageRank convergence
            tolerance: Convergence tolerance for PageRank
        """
        self.db_path = Path(db_path or "cache/citation_graph.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.damping_factor = damping_factor
        self.max_iterations = max_iterations
        self.tolerance = tolerance

        # Initialize graph
        self.graph = nx.DiGraph()

        # Document registry
        self.documents: Dict[str, DocumentNode] = {}

        # Citation registry
        self.citations: List[CitationEdge] = []

        # Cached metrics
        self.metrics: Optional[GraphMetrics] = None

        # Initialize database
        self._init_database()

        # Load existing graph
        self._load_graph()

    def _init_database(self):
        """Initialize SQLite database for persistence."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                title TEXT,
                doi TEXT,
                year INTEGER,
                authors TEXT,
                venue TEXT,
                extracted INTEGER,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Citations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS citations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT,
                target_id TEXT,
                context TEXT,
                section TEXT,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES documents(doc_id),
                FOREIGN KEY (target_id) REFERENCES documents(doc_id),
                UNIQUE(source_id, target_id, context)
            )
        ''')

        # Graph metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS graph_metrics (
                doc_id TEXT PRIMARY KEY,
                pagerank REAL,
                in_degree INTEGER,
                out_degree INTEGER,
                hub_score REAL,
                authority_score REAL,
                clustering_coefficient REAL,
                betweenness_centrality REAL,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
            )
        ''')

        # Indices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_citations_source ON citations(source_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_citations_target ON citations(target_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_doi ON documents(doi)')

        conn.commit()
        conn.close()

    def _load_graph(self):
        """Load existing graph from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Load documents
        cursor.execute('SELECT * FROM documents')
        for row in cursor.fetchall():
            doc = DocumentNode(
                doc_id=row[0],
                title=row[1],
                doi=row[2],
                year=row[3],
                authors=json.loads(row[4]) if row[4] else [],
                venue=row[5],
                extracted=bool(row[6]),
                metadata=json.loads(row[7]) if row[7] else {}
            )
            self.documents[doc.doc_id] = doc
            self.graph.add_node(doc.doc_id, **asdict(doc))

        # Load citations
        cursor.execute('SELECT source_id, target_id, context, section, confidence FROM citations')
        for row in cursor.fetchall():
            citation = CitationEdge(
                source_id=row[0],
                target_id=row[1],
                context=row[2],
                section=row[3],
                confidence=row[4]
            )
            self.citations.append(citation)
            self.graph.add_edge(
                citation.source_id,
                citation.target_id,
                context=citation.context,
                section=citation.section,
                confidence=citation.confidence
            )

        conn.close()

        logger.info(f"Loaded citation graph: {len(self.documents)} documents, {len(self.citations)} citations")

    def add_document(
        self,
        doc_id: str,
        title: str,
        doi: Optional[str] = None,
        year: Optional[int] = None,
        authors: Optional[List[str]] = None,
        venue: Optional[str] = None,
        extracted: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentNode:
        """
        Add a document to the citation graph.

        Args:
            doc_id: Unique document identifier
            title: Document title
            doi: Digital Object Identifier
            year: Publication year
            authors: List of author names
            venue: Publication venue
            extracted: Whether we've extracted content from this doc
            metadata: Additional metadata

        Returns:
            DocumentNode object
        """
        doc = DocumentNode(
            doc_id=doc_id,
            title=title,
            doi=doi,
            year=year,
            authors=authors or [],
            venue=venue,
            extracted=extracted,
            metadata=metadata or {}
        )

        # Add to registry
        self.documents[doc_id] = doc

        # Add to graph
        self.graph.add_node(doc_id, **asdict(doc))

        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO documents
            (doc_id, title, doi, year, authors, venue, extracted, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            doc_id,
            title,
            doi,
            year,
            json.dumps(authors or []),
            venue,
            int(extracted),
            json.dumps(metadata or {})
        ))

        conn.commit()
        conn.close()

        # Invalidate cached metrics
        self.metrics = None

        return doc

    def add_citation(
        self,
        source_id: str,
        target_id: str,
        context: Optional[str] = None,
        section: Optional[str] = None,
        confidence: float = 1.0
    ) -> CitationEdge:
        """
        Add a citation relationship to the graph.

        Args:
            source_id: Document doing the citing
            target_id: Document being cited
            context: Citation context text
            section: Section where citation appears
            confidence: Confidence in citation extraction

        Returns:
            CitationEdge object
        """
        citation = CitationEdge(
            source_id=source_id,
            target_id=target_id,
            context=context,
            section=section,
            confidence=confidence
        )

        # Add to registry
        self.citations.append(citation)

        # Add to graph
        self.graph.add_edge(
            source_id,
            target_id,
            context=context,
            section=section,
            confidence=confidence
        )

        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO citations
                (source_id, target_id, context, section, confidence)
                VALUES (?, ?, ?, ?, ?)
            ''', (source_id, target_id, context, section, confidence))
            conn.commit()
        except sqlite3.IntegrityError:
            # Citation already exists
            logger.debug(f"Citation {source_id} -> {target_id} already exists")

        conn.close()

        # Invalidate cached metrics
        self.metrics = None

        return citation

    def add_citations_from_extraction(
        self,
        doc_id: str,
        extracted_citations: List[Dict[str, Any]]
    ):
        """
        Add citations from extraction results.

        Args:
            doc_id: Document ID that contains the citations
            extracted_citations: List of citation dictionaries from CitationExtractionAgent
        """
        for citation in extracted_citations:
            # Try to resolve target document
            target_id = None

            # Try DOI first
            if citation.get('doi'):
                target_id = self._resolve_document_by_doi(citation['doi'])

            # Try title if no DOI
            if not target_id and citation.get('title'):
                target_id = self._resolve_document_by_title(citation['title'])

            # Create placeholder if not found
            if not target_id:
                target_id = self._create_placeholder_document(citation)

            # Add citation edge
            self.add_citation(
                source_id=doc_id,
                target_id=target_id,
                context=citation.get('context'),
                section=citation.get('section'),
                confidence=citation.get('confidence', 1.0)
            )

    def _resolve_document_by_doi(self, doi: str) -> Optional[str]:
        """Find document by DOI."""
        for doc_id, doc in self.documents.items():
            if doc.doi and doc.doi.lower() == doi.lower():
                return doc_id
        return None

    def _resolve_document_by_title(self, title: str) -> Optional[str]:
        """Find document by title (fuzzy matching)."""
        title_lower = title.lower().strip()

        # Exact match first
        for doc_id, doc in self.documents.items():
            if doc.title.lower().strip() == title_lower:
                return doc_id

        # Fuzzy match (simple similarity)
        best_match = None
        best_score = 0.8  # Minimum similarity threshold

        for doc_id, doc in self.documents.items():
            score = self._title_similarity(title, doc.title)
            if score > best_score:
                best_score = score
                best_match = doc_id

        return best_match

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate simple title similarity."""
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def _create_placeholder_document(self, citation: Dict[str, Any]) -> str:
        """Create placeholder document for unresolved citation."""
        # Generate ID from available info
        if citation.get('doi'):
            doc_id = f"doi_{citation['doi'].replace('/', '_')}"
        elif citation.get('title'):
            doc_id = f"ref_{hash(citation['title']) % 1000000}"
        else:
            doc_id = f"unknown_{len(self.documents)}"

        # Create document if doesn't exist
        if doc_id not in self.documents:
            self.add_document(
                doc_id=doc_id,
                title=citation.get('title', 'Unknown'),
                doi=citation.get('doi'),
                year=citation.get('year'),
                authors=citation.get('authors', []),
                venue=citation.get('venue'),
                extracted=False,
                metadata={'placeholder': True, 'citation_data': citation}
            )

        return doc_id

    def calculate_metrics(self, force_recalculate: bool = False) -> GraphMetrics:
        """
        Calculate all graph metrics.

        Args:
            force_recalculate: Force recalculation even if cached

        Returns:
            GraphMetrics object with all calculated metrics
        """
        if self.metrics and not force_recalculate:
            return self.metrics

        metrics = GraphMetrics()

        # Skip if graph is empty
        if not self.graph.nodes():
            logger.warning("Citation graph is empty")
            return metrics

        # PageRank
        try:
            metrics.pagerank = nx.pagerank(
                self.graph,
                alpha=self.damping_factor,
                max_iter=self.max_iterations,
                tol=self.tolerance
            )
        except nx.PowerIterationFailedConvergence:
            logger.warning("PageRank did not converge, using partial results")
            metrics.pagerank = nx.pagerank(
                self.graph,
                alpha=self.damping_factor,
                max_iter=self.max_iterations * 2,
                tol=self.tolerance * 10
            )

        # Degree metrics
        metrics.in_degree = dict(self.graph.in_degree())
        metrics.out_degree = dict(self.graph.out_degree())

        # HITS (Hub and Authority scores)
        try:
            hubs, authorities = nx.hits(
                self.graph,
                max_iter=self.max_iterations,
                tol=self.tolerance
            )
            metrics.hub_score = hubs
            metrics.authority_score = authorities
        except nx.PowerIterationFailedConvergence:
            logger.warning("HITS did not converge, using defaults")
            metrics.hub_score = {n: 1.0/len(self.graph) for n in self.graph.nodes()}
            metrics.authority_score = {n: 1.0/len(self.graph) for n in self.graph.nodes()}

        # Clustering coefficient
        metrics.clustering_coefficient = nx.clustering(self.graph)

        # Betweenness centrality (expensive for large graphs)
        if len(self.graph) < 1000:
            metrics.betweenness_centrality = nx.betweenness_centrality(self.graph)
        else:
            # Sample for large graphs
            k = min(100, len(self.graph))
            metrics.betweenness_centrality = nx.betweenness_centrality(
                self.graph,
                k=k,
                normalized=True
            )

        # Cache metrics
        self.metrics = metrics

        # Save to database
        self._save_metrics(metrics)

        return metrics

    def _save_metrics(self, metrics: GraphMetrics):
        """Save calculated metrics to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Clear old metrics
        cursor.execute('DELETE FROM graph_metrics')

        # Insert new metrics
        for doc_id in self.graph.nodes():
            cursor.execute('''
                INSERT INTO graph_metrics
                (doc_id, pagerank, in_degree, out_degree, hub_score,
                 authority_score, clustering_coefficient, betweenness_centrality)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                doc_id,
                metrics.pagerank.get(doc_id, 0.0),
                metrics.in_degree.get(doc_id, 0),
                metrics.out_degree.get(doc_id, 0),
                metrics.hub_score.get(doc_id, 0.0),
                metrics.authority_score.get(doc_id, 0.0),
                metrics.clustering_coefficient.get(doc_id, 0.0),
                metrics.betweenness_centrality.get(doc_id, 0.0)
            ))

        conn.commit()
        conn.close()

    def get_document_importance(self, doc_id: str) -> Dict[str, Any]:
        """
        Get importance metrics for a specific document.

        Args:
            doc_id: Document identifier

        Returns:
            Dictionary of importance metrics
        """
        if doc_id not in self.documents:
            return {}

        # Calculate metrics if needed
        metrics = self.calculate_metrics()

        return {
            'pagerank': metrics.pagerank.get(doc_id, 0.0),
            'in_degree': metrics.in_degree.get(doc_id, 0),
            'out_degree': metrics.out_degree.get(doc_id, 0),
            'hub_score': metrics.hub_score.get(doc_id, 0.0),
            'authority_score': metrics.authority_score.get(doc_id, 0.0),
            'clustering_coefficient': metrics.clustering_coefficient.get(doc_id, 0.0),
            'betweenness_centrality': metrics.betweenness_centrality.get(doc_id, 0.0)
        }

    def get_top_documents(
        self,
        metric: str = 'pagerank',
        n: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Get top N documents by a specific metric.

        Args:
            metric: Metric to rank by (pagerank, authority_score, etc.)
            n: Number of top documents to return

        Returns:
            List of (doc_id, score) tuples
        """
        metrics = self.calculate_metrics()

        metric_dict = getattr(metrics, metric, {})
        if not metric_dict:
            logger.warning(f"Metric '{metric}' not found")
            return []

        # Sort by metric value
        sorted_docs = sorted(
            metric_dict.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_docs[:n]

    def get_citation_context(
        self,
        source_id: str,
        target_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get citation contexts between two documents.

        Args:
            source_id: Source document ID
            target_id: Target document ID

        Returns:
            List of citation contexts
        """
        contexts = []

        for citation in self.citations:
            if citation.source_id == source_id and citation.target_id == target_id:
                contexts.append({
                    'context': citation.context,
                    'section': citation.section,
                    'confidence': citation.confidence
                })

        return contexts

    def export_graph(self, output_path: Path):
        """
        Export citation graph to various formats.

        Args:
            output_path: Output file path (extension determines format)
        """
        output_path = Path(output_path)
        ext = output_path.suffix.lower()

        if ext == '.json':
            # Export as node-link JSON
            data = nx.node_link_data(self.graph)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        elif ext == '.gexf':
            # Export as GEXF (Gephi format)
            nx.write_gexf(self.graph, output_path)

        elif ext == '.graphml':
            # Export as GraphML
            nx.write_graphml(self.graph, output_path)

        elif ext == '.dot':
            # Export as DOT (Graphviz format)
            nx.drawing.nx_pydot.write_dot(self.graph, output_path)

        else:
            raise ValueError(f"Unsupported export format: {ext}")

        logger.info(f"Exported citation graph to {output_path}")

    def visualize_subgraph(
        self,
        center_doc_id: str,
        depth: int = 2
    ) -> nx.DiGraph:
        """
        Get subgraph centered on a document.

        Args:
            center_doc_id: Central document ID
            depth: How many hops from center to include

        Returns:
            NetworkX DiGraph of subgraph
        """
        if center_doc_id not in self.graph:
            return nx.DiGraph()

        # Get nodes within depth hops
        nodes = {center_doc_id}
        for _ in range(depth):
            new_nodes = set()
            for node in nodes:
                # Add predecessors and successors
                new_nodes.update(self.graph.predecessors(node))
                new_nodes.update(self.graph.successors(node))
            nodes.update(new_nodes)

        # Create subgraph
        subgraph = self.graph.subgraph(nodes).copy()

        return subgraph


def main():
    """Test citation graph analyzer."""
    print("Testing Citation Graph Analyzer...")

    # Initialize analyzer
    analyzer = CitationGraphAnalyzer(
        db_path=Path("cache/test_citation_graph.db")
    )

    # Add some test documents
    print("\n=== Adding Test Documents ===")

    doc1 = analyzer.add_document(
        doc_id="doc1",
        title="Deep Learning for Natural Language Processing",
        doi="10.1234/example1",
        year=2023,
        authors=["Smith, J.", "Doe, A."],
        venue="NeurIPS",
        extracted=True
    )
    print(f"Added: {doc1.title}")

    doc2 = analyzer.add_document(
        doc_id="doc2",
        title="Attention Is All You Need",
        doi="10.1234/example2",
        year=2017,
        authors=["Vaswani, A.", "et al."],
        venue="NeurIPS",
        extracted=False
    )
    print(f"Added: {doc2.title}")

    doc3 = analyzer.add_document(
        doc_id="doc3",
        title="BERT: Pre-training of Deep Bidirectional Transformers",
        doi="10.1234/example3",
        year=2018,
        authors=["Devlin, J.", "et al."],
        venue="NAACL",
        extracted=False
    )
    print(f"Added: {doc3.title}")

    # Add citations
    print("\n=== Adding Citations ===")

    analyzer.add_citation(
        source_id="doc1",
        target_id="doc2",
        context="Transformers have revolutionized NLP (Vaswani et al., 2017)",
        section="Introduction",
        confidence=0.95
    )
    print("doc1 -> doc2")

    analyzer.add_citation(
        source_id="doc1",
        target_id="doc3",
        context="BERT demonstrated the power of pre-training (Devlin et al., 2018)",
        section="Related Work",
        confidence=0.98
    )
    print("doc1 -> doc3")

    analyzer.add_citation(
        source_id="doc3",
        target_id="doc2",
        context="Building on the transformer architecture",
        section="Methods",
        confidence=0.92
    )
    print("doc3 -> doc2")

    # Add from extraction results
    print("\n=== Adding from Extraction Results ===")
    extracted_citations = [
        {
            'title': 'GPT-3: Language Models are Few-Shot Learners',
            'doi': '10.1234/gpt3',
            'year': 2020,
            'authors': ['Brown, T.', 'et al.'],
            'context': 'Large language models like GPT-3',
            'section': 'Discussion',
            'confidence': 0.88
        }
    ]

    analyzer.add_citations_from_extraction("doc1", extracted_citations)
    print("Added citation to GPT-3 paper")

    # Calculate metrics
    print("\n=== Calculating Metrics ===")
    metrics = analyzer.calculate_metrics()

    print("\nPageRank Scores:")
    for doc_id, score in sorted(metrics.pagerank.items(), key=lambda x: x[1], reverse=True):
        doc = analyzer.documents[doc_id]
        print(f"  {doc_id}: {score:.4f} - {doc.title[:50]}...")

    print("\nIn-Degree (times cited):")
    for doc_id, degree in sorted(metrics.in_degree.items(), key=lambda x: x[1], reverse=True):
        doc = analyzer.documents[doc_id]
        print(f"  {doc_id}: {degree} - {doc.title[:50]}...")

    print("\nAuthority Scores:")
    for doc_id, score in sorted(metrics.authority_score.items(), key=lambda x: x[1], reverse=True):
        doc = analyzer.documents[doc_id]
        print(f"  {doc_id}: {score:.4f} - {doc.title[:50]}...")

    # Get top documents
    print("\n=== Top Documents by PageRank ===")
    top_docs = analyzer.get_top_documents(metric='pagerank', n=3)
    for doc_id, score in top_docs:
        doc = analyzer.documents[doc_id]
        print(f"  {score:.4f}: {doc.title}")

    # Get importance for specific document
    print("\n=== Document Importance: doc1 ===")
    importance = analyzer.get_document_importance("doc1")
    for metric, value in importance.items():
        if isinstance(value, float):
            print(f"  {metric}: {value:.4f}")
        else:
            print(f"  {metric}: {value}")

    # Export graph
    print("\n=== Exporting Graph ===")
    export_path = Path("results/test_citation_graph.json")
    export_path.parent.mkdir(exist_ok=True)
    analyzer.export_graph(export_path)
    print(f"Exported to {export_path}")

    print("\n✅ Citation Graph Analyzer test complete")


if __name__ == "__main__":
    main()