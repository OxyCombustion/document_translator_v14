#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Citation Graph Builder for RAG Bundles
Extracts citations from JSONL chunks and builds relationship graph
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


class CitationExtractor:
    """Extract citations from text using regex patterns"""

    def __init__(self):
        # Citation patterns (case-insensitive)
        self.patterns = {
            'figure': [
                re.compile(r'\bFig\.?\s*(\d+[a-z]?)\b', re.IGNORECASE),
                re.compile(r'\bFigure\s+(\d+[a-z]?)\b', re.IGNORECASE),
            ],
            'table': [
                re.compile(r'\bTable\s+(\d+[a-z]?)\b', re.IGNORECASE),
            ],
            'equation': [
                re.compile(r'\bEquation\s+(\d+[a-z]?)\b', re.IGNORECASE),
                re.compile(r'\bEq\.?\s*(\d+[a-z]?)\b', re.IGNORECASE),
            ],
            'chapter': [
                re.compile(r'\bChapter\s+(\d+)\b', re.IGNORECASE),
                re.compile(r'\bCh\.?\s*(\d+)\b', re.IGNORECASE),
            ],
            'reference': [
                re.compile(r'\bReferences?\s+(\d+(?:\s+and\s+\d+)?)\b', re.IGNORECASE),
                re.compile(r'\bRefs?\.?\s*(\d+(?:\s+and\s+\d+)?)\b', re.IGNORECASE),
            ]
        }

    def extract_citations(self, text: str) -> Dict[str, Set[str]]:
        """Extract all citations from text"""
        citations = defaultdict(set)

        for citation_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                for match in matches:
                    # Handle "X and Y" references
                    if ' and ' in match:
                        parts = match.split(' and ')
                        for part in parts:
                            citations[citation_type].add(part.strip())
                    else:
                        citations[citation_type].add(match)

        return {k: sorted(v) for k, v in citations.items()}


class CitationGraphBuilder:
    """Build citation graph from RAG bundles"""

    def __init__(self, jsonl_path: str, inventory_path: str):
        self.jsonl_path = Path(jsonl_path)
        self.inventory_path = Path(inventory_path)
        self.extractor = CitationExtractor()

        # Load reference inventory
        with open(self.inventory_path, 'r', encoding='utf-8') as f:
            self.inventory = json.load(f)

        # Graph data structures
        self.chunks = []
        self.citations_by_chunk = {}
        self.citations_by_object = defaultdict(lambda: defaultdict(list))
        self.cross_references = []
        self.stats = defaultdict(int)

    def load_chunks(self):
        """Load all chunks from JSONL file"""
        print(f"Loading chunks from {self.jsonl_path}...")

        with open(self.jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        chunk = json.loads(line)
                        self.chunks.append(chunk)
                    except json.JSONDecodeError as e:
                        print(f"WARNING: Failed to parse line {line_num}: {e}")

        print(f"Loaded {len(self.chunks)} chunks")

    def extract_all_citations(self):
        """Extract citations from all chunks"""
        print("\nExtracting citations from chunks...")

        for chunk in self.chunks:
            chunk_id = chunk.get('chunk_id', 'unknown')
            text = chunk.get('text', '')

            # Extract citations from text
            citations = self.extractor.extract_citations(text)

            # Store citations by chunk
            self.citations_by_chunk[chunk_id] = citations

            # Update stats
            for citation_type, refs in citations.items():
                self.stats[f'total_{citation_type}'] += len(refs)
                self.stats['total_citations'] += len(refs)

                # Store reverse mapping (object -> chunks)
                for ref in refs:
                    self.citations_by_object[citation_type][ref].append(chunk_id)

                    # Create cross-reference entry
                    self.cross_references.append({
                        'from_chunk': chunk_id,
                        'to_object': f'{citation_type}_{ref}',
                        'object_type': citation_type,
                        'object_id': ref,
                        'mention_count': text.lower().count(ref.lower())
                    })

        print(f"Extracted {self.stats['total_citations']} total citations")

    def validate_against_inventory(self) -> Dict:
        """Compare extracted citations with reference inventory"""
        print("\nValidating citations against inventory...")

        validation = {
            'matched': defaultdict(list),
            'orphaned': defaultdict(list),  # Cited but not in inventory
            'unused': defaultdict(list),    # In inventory but not cited
        }

        # Map citation types to inventory keys
        type_mapping = {
            'figure': 'figures',
            'table': 'tables',
            'equation': 'equations'
        }

        for citation_type, inventory_key in type_mapping.items():
            if inventory_key in self.inventory['inventory']:
                inventory_refs = set(self.inventory['inventory'][inventory_key]['all_referenced'])
                cited_refs = set(self.citations_by_object[citation_type].keys())

                # Find matches, orphans, and unused
                matched = cited_refs & inventory_refs
                orphaned = cited_refs - inventory_refs
                unused = inventory_refs - cited_refs

                validation['matched'][citation_type] = sorted(matched)
                validation['orphaned'][citation_type] = sorted(orphaned)
                validation['unused'][citation_type] = sorted(unused)

                print(f"\n{citation_type.upper()}:")
                print(f"  Matched: {len(matched)}")
                print(f"  Orphaned (cited but not in inventory): {len(orphaned)}")
                if orphaned:
                    print(f"    {orphaned}")
                print(f"  Unused (in inventory but not cited): {len(unused)}")
                if len(unused) <= 10:
                    print(f"    {unused}")

        return validation

    def find_top_referenced(self, n: int = 10) -> Dict[str, List[Tuple[str, int]]]:
        """Find most referenced objects by type"""
        top_refs = {}

        for obj_type, refs in self.citations_by_object.items():
            # Count chunks that reference each object
            ref_counts = [(ref, len(chunks)) for ref, chunks in refs.items()]
            ref_counts.sort(key=lambda x: x[1], reverse=True)
            top_refs[obj_type] = ref_counts[:n]

        return top_refs

    def find_chunks_without_citations(self) -> List[str]:
        """Find chunks with no citations"""
        chunks_without = []

        for chunk_id, citations in self.citations_by_chunk.items():
            total = sum(len(refs) for refs in citations.values())
            if total == 0:
                chunks_without.append(chunk_id)

        return chunks_without

    def build_graph(self) -> Dict:
        """Build complete citation graph"""
        print("\nBuilding citation graph...")

        # Get document name from JSONL path
        doc_name = self.jsonl_path.stem.replace('_rag_bundles', '')

        # Build graph structure
        graph = {
            'document': self.inventory['pdf_source'],
            'total_chunks': len(self.chunks),
            'citation_stats': {
                'total_citations': self.stats['total_citations'],
                'by_type': {
                    'figure': self.stats.get('total_figure', 0),
                    'table': self.stats.get('total_table', 0),
                    'equation': self.stats.get('total_equation', 0),
                    'chapter': self.stats.get('total_chapter', 0),
                    'reference': self.stats.get('total_reference', 0),
                }
            },
            'citations_by_chunk': {
                chunk_id: {
                    'figures': citations.get('figure', []),
                    'tables': citations.get('table', []),
                    'equations': citations.get('equation', []),
                    'chapters': citations.get('chapter', []),
                    'references': citations.get('reference', []),
                }
                for chunk_id, citations in self.citations_by_chunk.items()
            },
            'citations_by_object': {
                obj_type: dict(refs)
                for obj_type, refs in self.citations_by_object.items()
            },
            'cross_references': self.cross_references,
        }

        return graph

    def generate_report(self, graph: Dict, validation: Dict) -> str:
        """Generate validation report"""
        report = []
        report.append("=" * 80)
        report.append("CITATION GRAPH VALIDATION REPORT")
        report.append("=" * 80)
        report.append(f"\nDocument: {graph['document']}")
        report.append(f"Total Chunks: {graph['total_chunks']}")
        report.append(f"Total Citations: {graph['citation_stats']['total_citations']}")

        report.append("\n" + "-" * 80)
        report.append("CITATIONS BY TYPE")
        report.append("-" * 80)
        for obj_type, count in graph['citation_stats']['by_type'].items():
            report.append(f"{obj_type.capitalize()}: {count}")

        # Top referenced objects
        report.append("\n" + "-" * 80)
        report.append("TOP REFERENCED OBJECTS (by chunk count)")
        report.append("-" * 80)
        top_refs = self.find_top_referenced(10)
        for obj_type, refs in top_refs.items():
            if refs:
                report.append(f"\n{obj_type.upper()}:")
                for ref, count in refs:
                    report.append(f"  {ref}: referenced in {count} chunks")

        # Chunks without citations
        chunks_without = self.find_chunks_without_citations()
        report.append("\n" + "-" * 80)
        report.append(f"CHUNKS WITHOUT CITATIONS: {len(chunks_without)}")
        report.append("-" * 80)
        if chunks_without:
            for chunk_id in chunks_without[:10]:
                report.append(f"  {chunk_id}")
            if len(chunks_without) > 10:
                report.append(f"  ... and {len(chunks_without) - 10} more")

        # Validation results
        report.append("\n" + "-" * 80)
        report.append("VALIDATION AGAINST INVENTORY")
        report.append("-" * 80)
        for obj_type in ['figure', 'table', 'equation']:
            matched = validation['matched'].get(obj_type, [])
            orphaned = validation['orphaned'].get(obj_type, [])
            unused = validation['unused'].get(obj_type, [])

            report.append(f"\n{obj_type.upper()}:")
            report.append(f"  Matched: {len(matched)}")
            report.append(f"  Orphaned (cited but not in inventory): {len(orphaned)}")
            if orphaned:
                report.append(f"    {orphaned}")
            report.append(f"  Unused (in inventory but not cited): {len(unused)}")
            if unused and len(unused) <= 15:
                report.append(f"    {unused}")
            elif unused:
                report.append(f"    {unused[:15]} ... and {len(unused) - 15} more")

        report.append("\n" + "=" * 80)

        return "\n".join(report)

    def run(self, output_path: str):
        """Run complete citation graph building process"""
        # Load and process
        self.load_chunks()
        self.extract_all_citations()

        # Build graph
        graph = self.build_graph()

        # Validate
        validation = graph['validation'] = self.validate_against_inventory()

        # Generate report
        report = self.generate_report(graph, validation)
        print("\n" + report)

        # Save graph
        output_path = Path(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)

        print(f"\nCitation graph saved to: {output_path}")

        # Save report
        report_path = output_path.parent / f"{output_path.stem}_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"Validation report saved to: {report_path}")

        return graph, report


def main():
    """Main entry point"""
    # File paths
    jsonl_path = "/home/thermodynamics/document_translator_v14/test_output_rag/rag_bundles.jsonl"
    inventory_path = "/home/thermodynamics/document_translator_v14/test_output_orchestrator/reference_inventory.json"
    output_path = "/home/thermodynamics/document_translator_v14/test_output_rag/citation_graph.json"

    # Build citation graph
    builder = CitationGraphBuilder(jsonl_path, inventory_path)
    graph, report = builder.run(output_path)

    return graph, report


if __name__ == '__main__':
    main()
