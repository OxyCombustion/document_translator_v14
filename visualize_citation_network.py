#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Citation Network Visualizer
Creates a visual representation of the citation network
"""

import json
from collections import defaultdict
from pathlib import Path


def create_mermaid_graph(citation_graph_path: str, output_path: str, max_nodes: int = 50):
    """Create a Mermaid diagram of the citation network"""

    # Load citation graph
    with open(citation_graph_path, 'r', encoding='utf-8') as f:
        graph = json.load(f)

    # Start Mermaid graph
    mermaid = ["```mermaid", "graph TD"]

    # Add title
    mermaid.append("    %% Citation Network - Top Referenced Objects")

    # Get top objects by citation count
    top_objects = []

    for obj_type in ['figure', 'table', 'equation']:
        if obj_type in graph['citations_by_object']:
            for obj_id, chunks in graph['citations_by_object'][obj_type].items():
                top_objects.append((obj_type, obj_id, len(chunks)))

    # Sort by chunk count (descending)
    top_objects.sort(key=lambda x: x[2], reverse=True)
    top_objects = top_objects[:max_nodes]

    # Create nodes for top objects
    mermaid.append("\n    %% Object Nodes")
    for obj_type, obj_id, count in top_objects:
        node_id = f"{obj_type}_{obj_id}".replace(' ', '_')
        label = f"{obj_type.capitalize()} {obj_id}"

        # Color by type
        if obj_type == 'figure':
            style = "fill:#e1f5ff,stroke:#0288d1,stroke-width:2px"
        elif obj_type == 'table':
            style = "fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px"
        elif obj_type == 'equation':
            style = "fill:#fff3e0,stroke:#f57c00,stroke-width:2px"
        else:
            style = "fill:#e0e0e0,stroke:#616161,stroke-width:2px"

        mermaid.append(f"    {node_id}[\"{label}<br/>({count} chunks)\"]")
        mermaid.append(f"    style {node_id} {style}")

    # Create chunk nodes (only show chunks that cite top objects)
    mermaid.append("\n    %% Chunk Nodes (Top 20)")
    chunk_citation_counts = defaultdict(int)

    for obj_type, obj_id, count in top_objects:
        if obj_type in graph['citations_by_object']:
            if obj_id in graph['citations_by_object'][obj_type]:
                for chunk_id in graph['citations_by_object'][obj_type][obj_id]:
                    chunk_citation_counts[chunk_id] += 1

    # Get top chunks
    top_chunks = sorted(chunk_citation_counts.items(), key=lambda x: x[1], reverse=True)[:20]

    for chunk_id, cite_count in top_chunks:
        node_id = chunk_id.replace('-', '_').replace(' ', '_')
        # Simplify chunk label
        label = chunk_id.replace('unit_001_page_', 'p').replace('unit_002_page_', 'p')
        mermaid.append(f"    {node_id}[\"{label}\"]")
        mermaid.append(f"    style {node_id} fill:#e8f5e9,stroke:#388e3c,stroke-width:1px")

    # Create edges (chunk -> object)
    mermaid.append("\n    %% Citation Edges")
    edge_count = 0
    max_edges = 100  # Limit edges for readability

    for obj_type, obj_id, count in top_objects:
        if edge_count >= max_edges:
            break

        if obj_type in graph['citations_by_object']:
            if obj_id in graph['citations_by_object'][obj_type]:
                for chunk_id in graph['citations_by_object'][obj_type][obj_id]:
                    if chunk_id in dict(top_chunks):
                        chunk_node = chunk_id.replace('-', '_').replace(' ', '_')
                        obj_node = f"{obj_type}_{obj_id}".replace(' ', '_')
                        mermaid.append(f"    {chunk_node} --> {obj_node}")
                        edge_count += 1

                        if edge_count >= max_edges:
                            break

    mermaid.append("```")

    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(mermaid))

    print(f"Mermaid diagram saved to: {output_path}")
    print(f"Nodes: {len(top_objects)} objects + {len(top_chunks)} chunks")
    print(f"Edges: {edge_count}")


def create_citation_statistics_table(citation_graph_path: str, output_path: str):
    """Create a detailed statistics table"""

    # Load citation graph
    with open(citation_graph_path, 'r', encoding='utf-8') as f:
        graph = json.load(f)

    lines = []
    lines.append("# Citation Network Statistics\n")

    # Overall stats
    lines.append("## Overall Statistics\n")
    lines.append(f"- **Total Chunks**: {graph['total_chunks']}")
    lines.append(f"- **Total Citations**: {graph['citation_stats']['total_citations']}")
    lines.append(f"- **Average Citations/Chunk**: {graph['citation_stats']['total_citations'] / graph['total_chunks']:.2f}\n")

    # Citations by type
    lines.append("## Citations by Type\n")
    lines.append("| Type | Count | % of Total |")
    lines.append("|------|-------|------------|")

    total = graph['citation_stats']['total_citations']
    for obj_type, count in graph['citation_stats']['by_type'].items():
        percentage = (count / total * 100) if total > 0 else 0
        lines.append(f"| {obj_type.capitalize()} | {count} | {percentage:.1f}% |")

    # Top cited objects per type
    for obj_type in ['figure', 'table', 'equation', 'chapter']:
        if obj_type in graph['citations_by_object']:
            lines.append(f"\n## Top {obj_type.capitalize()}s\n")
            lines.append("| Object | Chunk Count |")
            lines.append("|--------|-------------|")

            # Sort by chunk count
            items = [(obj_id, len(chunks)) for obj_id, chunks in graph['citations_by_object'][obj_type].items()]
            items.sort(key=lambda x: x[1], reverse=True)

            for obj_id, count in items[:15]:
                lines.append(f"| {obj_type.capitalize()} {obj_id} | {count} |")

    # Chunks with most citations
    lines.append("\n## Chunks with Most Citations\n")
    lines.append("| Chunk | Figure | Table | Equation | Chapter | Reference | Total |")
    lines.append("|-------|--------|-------|----------|---------|-----------|-------|")

    chunk_totals = []
    for chunk_id, citations in graph['citations_by_chunk'].items():
        total_citations = sum(len(refs) for refs in citations.values())
        chunk_totals.append((
            chunk_id,
            len(citations['figures']),
            len(citations['tables']),
            len(citations['equations']),
            len(citations['chapters']),
            len(citations['references']),
            total_citations
        ))

    chunk_totals.sort(key=lambda x: x[6], reverse=True)

    for chunk_id, fig, tab, eq, ch, ref, total in chunk_totals[:20]:
        # Simplify chunk ID
        short_id = chunk_id.replace('unit_001_page_', 'p').replace('unit_002_page_', 'p')
        lines.append(f"| {short_id} | {fig} | {tab} | {eq} | {ch} | {ref} | **{total}** |")

    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"\nStatistics table saved to: {output_path}")


def main():
    """Main entry point"""
    citation_graph_path = "/home/thermodynamics/document_translator_v14/test_output_rag/citation_graph.json"
    output_dir = Path("/home/thermodynamics/document_translator_v14/test_output_rag")

    # Create Mermaid diagram
    mermaid_path = output_dir / "citation_network_diagram.md"
    create_mermaid_graph(citation_graph_path, mermaid_path, max_nodes=30)

    # Create statistics table
    stats_path = output_dir / "citation_statistics.md"
    create_citation_statistics_table(citation_graph_path, stats_path)

    print("\n✅ Visualization complete!")
    print(f"\nGenerated files:")
    print(f"  - {mermaid_path}")
    print(f"  - {stats_path}")


if __name__ == '__main__':
    main()
