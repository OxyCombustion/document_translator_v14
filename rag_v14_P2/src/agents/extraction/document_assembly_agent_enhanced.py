#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Document Assembly Agent - With Citation Integration

This enhanced version integrates CitationExtractionAgent into the assembly
pipeline to build complete cross-reference graphs with citation relationships.

Key Enhancements:
-----------------
- Runs CitationExtractionAgent after content extraction
- Updates all objects with bidirectional citation references
- Includes citation edges in cross-reference graph
- Generates enhanced statistics with citation metrics

Author: Claude Opus 4.1
Date: 2025-10-08
Version: 2.0
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
from datetime import datetime

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

# Import CitationExtractionAgent
from .citation_extraction_agent import CitationExtractionAgent


class EnhancedDocumentAssemblyAgent:
    """
    Enhanced orchestrator for complete RAG package assembly with citations.

    Takes outputs from all extraction agents and:
    1. Processes citations to build bidirectional references
    2. Builds enhanced cross-reference graph with citation edges
    3. Generates JSONL for vector databases with complete references
    4. Creates comprehensive retrieval index
    5. Provides detailed statistics including citation metrics

    Usage Example:
    --------------
    >>> assembler = EnhancedDocumentAssemblyAgent(
    ...     equations_file=Path("results/equations.json"),
    ...     tables_file=Path("results/tables.json"),
    ...     figures_file=Path("results/figures.json"),
    ...     text_file=Path("results/text.json"),
    ...     output_dir=Path("results/assembled")
    ... )
    >>> assembler.assemble()
    """

    def __init__(
        self,
        equations_file: Path,
        tables_file: Path,
        figures_file: Path,
        text_file: Path,
        output_dir: Path
    ):
        """Initialize enhanced document assembler."""
        self.equations_file = equations_file
        self.tables_file = tables_file
        self.figures_file = figures_file
        self.text_file = text_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load all extraction results
        self.equations = self._load_json(equations_file) if equations_file.exists() else []
        self.tables = self._load_json(tables_file) if tables_file.exists() else []
        self.figures = self._load_json(figures_file) if figures_file.exists() else []
        self.text = self._load_json(text_file) if text_file.exists() else []

        # Initialize citation agent
        self.citation_agent = CitationExtractionAgent()

    def _load_json(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load extraction results from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('objects', [])
        except Exception as e:
            print(f"⚠️  Failed to load {file_path}: {e}")
            return []

    def assemble(self) -> Dict[str, Any]:
        """
        Assemble complete RAG package with citation integration.

        Returns:
            Dictionary with assembly results and statistics
        """
        print("="*70)
        print("ENHANCED DOCUMENT ASSEMBLY")
        print("="*70)

        # Step 1: Process citations (NEW)
        print("\n1. Extracting and mapping citations...")
        updated_objects = self._process_citations()
        print(f"   ✅ Citations processed")
        print(f"   ✅ References updated bidirectionally")

        # Step 2: Build enhanced cross-reference graph
        print("\n2. Building enhanced cross-reference graph...")
        graph = self._build_enhanced_cross_reference_graph()
        print(f"   ✅ Graph nodes: {len(graph['nodes'])}")
        print(f"   ✅ Graph edges: {len(graph['edges'])}")
        print(f"   ✅ Citation edges: {graph['statistics']['citation_edges']}")

        # Step 3: Generate JSONL for vector database
        print("\n3. Generating JSONL for vector database...")
        jsonl_path = self.output_dir / "document_package.jsonl"
        self._generate_enhanced_jsonl(jsonl_path)
        print(f"   ✅ JSONL: {jsonl_path}")

        # Step 4: Create enhanced retrieval index
        print("\n4. Creating enhanced retrieval index...")
        index = self._create_enhanced_retrieval_index()
        index_path = self.output_dir / "retrieval_index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Index: {index_path}")

        # Step 5: Save enhanced cross-reference graph
        print("\n5. Saving enhanced cross-reference graph...")
        graph_path = self.output_dir / "cross_reference_graph.json"
        with open(graph_path, 'w', encoding='utf-8') as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Graph: {graph_path}")

        # Step 6: Save citation report (NEW)
        print("\n6. Generating citation report...")
        citation_report_path = self.output_dir / "citation_report.json"
        citation_report = self.citation_agent.generate_report(citation_report_path)
        print(f"   ✅ Citation report: {citation_report_path}")

        # Step 7: Save document metadata
        print("\n7. Saving document citation metadata...")
        doc_metadata = self._get_enhanced_document_metadata()
        if doc_metadata:
            citation_path = self.output_dir / "document_citation.json"
            with open(citation_path, 'w', encoding='utf-8') as f:
                json.dump(doc_metadata, f, indent=2, ensure_ascii=False)
            print(f"   ✅ Citation: {citation_path}")
        else:
            print(f"   ℹ️  No document metadata available")

        # Generate enhanced summary
        summary = self._generate_enhanced_summary()
        summary_path = self.output_dir / "assembly_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Assembly complete: {summary_path}")

        self._print_enhanced_summary(summary)

        return summary

    def _process_citations(self) -> Dict[str, List[Any]]:
        """
        Process citations using CitationExtractionAgent.

        Returns:
            Dictionary with updated objects containing citation references
        """
        # Convert dictionaries back to ExtractedObject format if needed
        # (CitationExtractionAgent expects ExtractedObject instances)

        # For now, pass the loaded dictionaries directly
        # In production, would convert to ExtractedObject instances

        updated_objects = self.citation_agent.process_extractions(
            equations=self.equations,
            tables=self.tables,
            figures=self.figures,
            text_chunks=self.text
        )

        # Update stored objects
        self.equations = updated_objects['equations']
        self.tables = updated_objects['tables']
        self.figures = updated_objects['figures']
        self.text = updated_objects['text']

        return updated_objects

    def _build_enhanced_cross_reference_graph(self) -> Dict[str, Any]:
        """
        Build cross-reference graph with citation edges.

        Returns:
            Graph structure with nodes, edges, and statistics
        """
        nodes = []
        edges = []
        citation_edge_count = 0

        # Create nodes for all objects
        all_objects = self.equations + self.tables + self.figures + self.text

        for obj in all_objects:
            node = {
                'id': obj.get('id'),
                'type': obj.get('type'),
                'page': obj.get('page'),
                'label': self._get_object_label(obj),
                'citation_count': obj.get('references', {}).get('citation_count', 0),
                'has_caption': bool(obj.get('content', {}).get('caption')) if obj.get('type') == 'figure' else None
            }
            nodes.append(node)

        # Create edges based on references
        for obj in all_objects:
            obj_id = obj.get('id')
            references = obj.get('references', {})

            # Citation edges (from text to objects)
            if 'cites' in references:
                for target_id in references['cites']:
                    edges.append({
                        'source': obj_id,
                        'target': target_id,
                        'type': 'cites',
                        'weight': 1
                    })
                    citation_edge_count += 1

            # Reverse citation edges (from objects to text)
            if 'cited_by' in references:
                for source_id in references['cited_by']:
                    # Don't duplicate if already added above
                    if not any(e['source'] == source_id and e['target'] == obj_id for e in edges):
                        edges.append({
                            'source': source_id,
                            'target': obj_id,
                            'type': 'cites',
                            'weight': 1
                        })
                        citation_edge_count += 1

            # Related object edges
            for ref_type in ['related_equations', 'related_tables', 'related_figures']:
                if ref_type in references:
                    for related_id in references[ref_type]:
                        edges.append({
                            'source': obj_id,
                            'target': related_id,
                            'type': 'related',
                            'weight': 0.5
                        })

        # Calculate graph statistics
        statistics = {
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'citation_edges': citation_edge_count,
            'related_edges': len(edges) - citation_edge_count,
            'nodes_by_type': {
                'equation': sum(1 for n in nodes if n['type'] == 'equation'),
                'table': sum(1 for n in nodes if n['type'] == 'table'),
                'figure': sum(1 for n in nodes if n['type'] == 'figure'),
                'text': sum(1 for n in nodes if n['type'] == 'text')
            },
            'most_cited_objects': self._get_most_cited_objects(nodes, 5)
        }

        return {
            'nodes': nodes,
            'edges': edges,
            'statistics': statistics,
            'metadata': {
                'created': datetime.now().isoformat(),
                'version': '2.0',
                'includes_citations': True
            }
        }

    def _get_object_label(self, obj: Dict[str, Any]) -> str:
        """Generate human-readable label for object."""
        obj_type = obj.get('type', 'unknown')
        obj_id = obj.get('id', '')

        if obj_type == 'equation':
            content = obj.get('content', {})
            if isinstance(content, dict) and 'latex' in content:
                return f"Equation: {content['latex'][:50]}..."
            return f"Equation {obj_id}"

        elif obj_type == 'figure':
            caption = obj.get('content', {}).get('caption', '')
            if caption:
                return f"Figure: {caption[:50]}..."
            return f"Figure {obj_id}"

        elif obj_type == 'table':
            caption = obj.get('content', {}).get('caption', '')
            if caption:
                return f"Table: {caption[:50]}..."
            return f"Table {obj_id}"

        elif obj_type == 'text':
            text = obj.get('content', {}).get('text', '')
            if text:
                return f"Text: {text[:50]}..."
            return f"Text chunk {obj_id}"

        return obj_id

    def _get_most_cited_objects(self, nodes: List[Dict], limit: int = 5) -> List[Dict]:
        """Get the most frequently cited objects."""
        cited_nodes = [n for n in nodes if n['citation_count'] > 0]
        sorted_nodes = sorted(cited_nodes, key=lambda x: x['citation_count'], reverse=True)

        return [
            {
                'id': node['id'],
                'type': node['type'],
                'citation_count': node['citation_count'],
                'label': node['label'][:50]
            }
            for node in sorted_nodes[:limit]
        ]

    def _generate_enhanced_jsonl(self, output_path: Path):
        """Generate JSONL with complete citation references."""
        all_objects = self.equations + self.tables + self.figures + self.text

        with open(output_path, 'w', encoding='utf-8') as f:
            for obj in all_objects:
                # Enhance object with citation summary
                enhanced_obj = {
                    **obj,
                    'citation_summary': {
                        'citation_count': obj.get('references', {}).get('citation_count', 0),
                        'cited_by': obj.get('references', {}).get('cited_by', []),
                        'cites': obj.get('references', {}).get('cites', []),
                        'pages_mentioned': obj.get('references', {}).get('mentioned_on_pages', [])
                    }
                }
                f.write(json.dumps(enhanced_obj, ensure_ascii=False) + '\n')

    def _create_enhanced_retrieval_index(self) -> Dict[str, Any]:
        """Create retrieval index with citation metadata."""
        all_objects = self.equations + self.tables + self.figures + self.text

        index = {
            'metadata': {
                'created': datetime.now().isoformat(),
                'total_objects': len(all_objects),
                'includes_citations': True
            },
            'by_type': {},
            'by_page': {},
            'by_citation_count': {},
            'highly_cited': []
        }

        # Index by type
        for obj_type in ['equation', 'table', 'figure', 'text']:
            index['by_type'][obj_type] = [
                obj['id'] for obj in all_objects if obj.get('type') == obj_type
            ]

        # Index by page
        for obj in all_objects:
            page = str(obj.get('page', 0))
            if page not in index['by_page']:
                index['by_page'][page] = []
            index['by_page'][page].append(obj['id'])

        # Index by citation count
        for obj in all_objects:
            count = obj.get('references', {}).get('citation_count', 0)
            count_key = f"{count}_citations"
            if count_key not in index['by_citation_count']:
                index['by_citation_count'][count_key] = []
            index['by_citation_count'][count_key].append(obj['id'])

        # Highly cited objects (5+ citations)
        index['highly_cited'] = [
            obj['id'] for obj in all_objects
            if obj.get('references', {}).get('citation_count', 0) >= 5
        ]

        return index

    def _get_enhanced_document_metadata(self) -> Optional[Dict[str, Any]]:
        """Get enhanced document metadata including citation statistics."""
        # Try to get metadata from any extracted object
        for obj in self.equations + self.tables + self.figures + self.text:
            if 'document_id' in obj or 'zotero_key' in obj:
                return {
                    'document_id': obj.get('document_id'),
                    'zotero_key': obj.get('zotero_key'),
                    'extraction_date': datetime.now().isoformat(),
                    'statistics': {
                        'total_equations': len(self.equations),
                        'total_tables': len(self.tables),
                        'total_figures': len(self.figures),
                        'total_text_chunks': len(self.text),
                        'total_citations': self.citation_agent.stats['total_citations'],
                        'figure_citations': self.citation_agent.stats['figure_citations'],
                        'table_citations': self.citation_agent.stats['table_citations'],
                        'equation_citations': self.citation_agent.stats['equation_citations']
                    }
                }
        return None

    def _generate_enhanced_summary(self) -> Dict[str, Any]:
        """Generate enhanced assembly summary with citation metrics."""
        all_objects = self.equations + self.tables + self.figures + self.text

        # Count figures with captions
        figures_with_captions = sum(
            1 for obj in self.figures
            if obj.get('content', {}).get('caption')
        )

        # Count objects with citations
        objects_with_citations = sum(
            1 for obj in all_objects
            if obj.get('references', {}).get('citation_count', 0) > 0
        )

        return {
            'timestamp': datetime.now().isoformat(),
            'statistics': {
                'total_objects': len(all_objects),
                'equations': len(self.equations),
                'tables': len(self.tables),
                'figures': len(self.figures),
                'text_chunks': len(self.text),
                'figures_with_captions': figures_with_captions,
                'caption_coverage': f"{figures_with_captions}/{len(self.figures)}" if self.figures else "N/A",
                'objects_with_citations': objects_with_citations,
                'total_citations': self.citation_agent.stats['total_citations'],
                'citation_types': {
                    'figure': self.citation_agent.stats['figure_citations'],
                    'table': self.citation_agent.stats['table_citations'],
                    'equation': self.citation_agent.stats['equation_citations']
                }
            },
            'outputs': {
                'jsonl': str(self.output_dir / "document_package.jsonl"),
                'graph': str(self.output_dir / "cross_reference_graph.json"),
                'index': str(self.output_dir / "retrieval_index.json"),
                'citation_report': str(self.output_dir / "citation_report.json")
            }
        }

    def _print_enhanced_summary(self, summary: Dict[str, Any]):
        """Print enhanced summary to console."""
        print("\n" + "="*70)
        print("ASSEMBLY SUMMARY")
        print("="*70)

        stats = summary['statistics']
        print(f"\nContent extracted:")
        print(f"  Equations: {stats['equations']}")
        print(f"  Tables: {stats['tables']}")
        print(f"  Figures: {stats['figures']} ({stats['figures_with_captions']} with captions)")
        print(f"  Text chunks: {stats['text_chunks']}")

        print(f"\nCitation analysis:")
        print(f"  Total citations: {stats['total_citations']}")
        print(f"  Objects with citations: {stats['objects_with_citations']}")
        print(f"  Citation breakdown:")
        print(f"    - Figure citations: {stats['citation_types']['figure']}")
        print(f"    - Table citations: {stats['citation_types']['table']}")
        print(f"    - Equation citations: {stats['citation_types']['equation']}")

        print(f"\nOutputs generated:")
        for name, path in summary['outputs'].items():
            print(f"  {name}: {Path(path).name}")

        print("="*70)