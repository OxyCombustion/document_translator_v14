#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Assembly Agent - RAG Package Orchestration

Assembles complete RAG-ready document package from all extraction agents.
Builds cross-reference graph and generates unified outputs.

Key Features:
-------------
- **Cross-Reference Graph**: Links equations ↔ text ↔ tables ↔ figures
- **JSONL Generation**: Vector database-ready format
- **Retrieval Index**: Metadata for efficient search
- **Multi-Format Output**: JSON, JSONL, graph visualization

Author: Claude Code
Date: 2025-10-03
Version: 1.0
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


class DocumentAssemblyAgent:
    """
    Orchestrates complete RAG package assembly.

    Takes outputs from all extraction agents and:
    1. Builds cross-reference graph
    2. Generates JSONL for vector databases
    3. Creates retrieval index
    4. Organizes complete package

    Usage Example:
    --------------
    >>> assembler = DocumentAssemblyAgent(
    ...     equations_file=Path("results/rag_extractions/equation_extraction_results.json"),
    ...     tables_file=Path("results/rag_extractions/table_extraction_results.json"),
    ...     figures_file=Path("results/rag_extractions/figure_extraction_results.json"),
    ...     text_file=Path("results/rag_extractions/text_extraction_results.json"),
    ...     output_dir=Path("results/rag_extractions/assembled")
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
        """Initialize document assembler."""
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
        Assemble complete RAG package.

        Returns:
            Dictionary with assembly results and statistics
        """
        print("="*70)
        print("DOCUMENT ASSEMBLY")
        print("="*70)

        # Build cross-reference graph
        print("\n1. Building cross-reference graph...")
        graph = self._build_cross_reference_graph()
        print(f"   ✅ Graph nodes: {len(graph['nodes'])}")
        print(f"   ✅ Graph edges: {len(graph['edges'])}")

        # Generate JSONL for vector database
        print("\n2. Generating JSONL for vector database...")
        jsonl_path = self.output_dir / "document_package.jsonl"
        self._generate_jsonl(jsonl_path)
        print(f"   ✅ JSONL: {jsonl_path}")

        # Create retrieval index
        print("\n3. Creating retrieval index...")
        index = self._create_retrieval_index()
        index_path = self.output_dir / "retrieval_index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Index: {index_path}")

        # Save cross-reference graph
        print("\n4. Saving cross-reference graph...")
        graph_path = self.output_dir / "cross_reference_graph.json"
        with open(graph_path, 'w', encoding='utf-8') as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Graph: {graph_path}")

        # Save document citation metadata (if available)
        print("\n5. Saving document citation metadata...")
        doc_metadata = self._get_document_metadata()
        if doc_metadata:
            citation_path = self.output_dir / "document_citation.json"
            with open(citation_path, 'w', encoding='utf-8') as f:
                json.dump(doc_metadata, f, indent=2, ensure_ascii=False)
            print(f"   ✅ Citation: {citation_path}")
        else:
            print(f"   ℹ️  No document metadata available")

        # Generate summary
        summary = self._generate_summary()

        print("\n" + "="*70)
        print("ASSEMBLY COMPLETE")
        print("="*70)
        print(f"  Total objects: {summary['total_objects']}")
        print(f"  Cross-references: {summary['total_references']}")
        print(f"  Output directory: {self.output_dir}")
        print("="*70)

        return summary

    def _build_cross_reference_graph(self) -> Dict[str, Any]:
        """
        Build graph of relationships between objects.

        Graph structure:
        - Nodes: All extracted objects (equations, tables, figures, text)
        - Edges: References between objects

        Returns:
            Dictionary with nodes and edges
        """
        graph = {
            "nodes": [],
            "edges": []
        }

        # Add all objects as nodes
        all_objects = self.equations + self.tables + self.figures + self.text

        for obj in all_objects:
            graph["nodes"].append({
                "id": obj["id"],
                "type": obj["type"],
                "page": obj["page"],
                "label": self._get_node_label(obj)
            })

        # Build edges from references
        for obj in all_objects:
            source_id = obj["id"]
            refs = obj.get("references", {})

            # Add edges for each reference type
            for ref_type, ref_list in refs.items():
                for target_id in ref_list:
                    # Find target node
                    target_exists = any(n["id"] == target_id for n in graph["nodes"])
                    if target_exists:
                        graph["edges"].append({
                            "source": source_id,
                            "target": target_id,
                            "type": ref_type,
                            "label": ref_type
                        })

        return graph

    def _get_node_label(self, obj: Dict[str, Any]) -> str:
        """Get human-readable label for node."""
        obj_type = obj["type"]
        obj_id = obj["id"]

        if obj_type == "equation":
            eq_num = obj.get("content", {}).get("equation_number", "?")
            return f"Equation {eq_num}"
        elif obj_type == "table":
            caption = obj.get("context", {}).get("caption", obj_id)
            return caption[:30] + "..." if len(caption) > 30 else caption
        elif obj_type == "figure":
            caption = obj.get("context", {}).get("caption", obj_id)
            return caption[:30] + "..." if len(caption) > 30 else caption
        elif obj_type == "text":
            text = obj.get("content", {}).get("text", "")
            return text[:30] + "..." if len(text) > 30 else text

        return obj_id

    def _generate_jsonl(self, output_path: Path):
        """
        Generate JSONL file for vector database ingestion.

        Each line is a JSON object ready for embedding and indexing.
        """
        all_objects = self.equations + self.tables + self.figures + self.text

        with open(output_path, 'w', encoding='utf-8') as f:
            for obj in all_objects:
                # Create simplified object for vector DB
                vector_obj = {
                    "id": obj["id"],
                    "type": obj["type"],
                    "page": obj["page"],
                    "content": self._get_content_for_embedding(obj),
                    "metadata": {
                        "bbox": obj.get("bbox", []),
                        "extraction_method": obj.get("metadata", {}).get("extraction_method", ""),
                        "confidence": obj.get("metadata", {}).get("confidence", 1.0)
                    },
                    "references": obj.get("references", {})
                }

                # Write as single line JSON
                f.write(json.dumps(vector_obj, ensure_ascii=False) + '\n')

    def _get_content_for_embedding(self, obj: Dict[str, Any]) -> str:
        """
        Extract text content suitable for embedding.

        Different strategies for different object types.
        """
        obj_type = obj["type"]
        content = obj.get("content", {})

        if obj_type == "equation":
            # For equations: LaTeX + description + context
            parts = []
            if "latex" in content:
                parts.append(f"LaTeX: {content['latex']}")
            if "text_description" in content:
                parts.append(content["text_description"])
            context = obj.get("context", {})
            if "before" in context:
                parts.append(context["before"][-100:])  # Last 100 chars
            if "after" in context:
                parts.append(context["after"][:100])  # First 100 chars
            return " ".join(parts)

        elif obj_type == "table":
            # For tables: Caption + headers + sample rows
            parts = []
            caption = obj.get("context", {}).get("caption", "")
            if caption:
                parts.append(caption)

            structured = content.get("structured_data", {})
            if "headers" in structured:
                parts.append(" | ".join(structured["headers"]))
            if "rows" in structured:
                # Include first 2 rows
                for row in structured["rows"][:2]:
                    parts.append(" | ".join(str(cell) for cell in row))

            return " ".join(parts)

        elif obj_type == "figure":
            # For figures: Caption only (image embeddings require vision models)
            return content.get("caption", "")

        elif obj_type == "text":
            # For text: Direct text content
            return content.get("text", "")

        return ""

    def _create_retrieval_index(self) -> Dict[str, Any]:
        """
        Create retrieval index with metadata for efficient search.

        Returns:
            Index dictionary with statistics and mappings
        """
        all_objects = self.equations + self.tables + self.figures + self.text

        index = {
            "metadata": {
                "created": datetime.now().isoformat(),
                "total_objects": len(all_objects),
                "version": "1.0"
            },
            "by_type": {},
            "by_page": {},
            "by_id": {}
        }

        # Index by type
        for obj_type in ["equation", "table", "figure", "text"]:
            objs = [o for o in all_objects if o["type"] == obj_type]
            index["by_type"][obj_type] = {
                "count": len(objs),
                "ids": [o["id"] for o in objs]
            }

        # Index by page
        pages = set(obj["page"] for obj in all_objects)
        for page in sorted(pages):
            objs = [o for o in all_objects if o["page"] == page]
            index["by_page"][page] = {
                "count": len(objs),
                "ids": [o["id"] for o in objs]
            }

        # Index by ID (for quick lookup)
        for obj in all_objects:
            index["by_id"][obj["id"]] = {
                "type": obj["type"],
                "page": obj["page"]
            }

        return index

    def _get_document_metadata(self) -> Optional[Dict[str, Any]]:
        """
        Extract document citation metadata from loaded files.

        Reads the document_metadata field from extraction results.
        All objects should have the same metadata since they're from
        the same source document.

        Returns:
            Document metadata dictionary or None if not available
        """
        # Try to get metadata from any extraction results file
        for file_path in [self.equations_file, self.tables_file, self.figures_file, self.text_file]:
            if file_path and file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        metadata = data.get('metadata', {}).get('document_metadata', {})
                        if metadata:
                            return metadata
                except Exception as e:
                    continue

        return None

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate assembly summary statistics."""
        all_objects = self.equations + self.tables + self.figures + self.text

        total_refs = sum(
            len(refs)
            for obj in all_objects
            for refs in obj.get("references", {}).values()
        )

        return {
            "total_objects": len(all_objects),
            "equations": len(self.equations),
            "tables": len(self.tables),
            "figures": len(self.figures),
            "text": len(self.text),
            "total_references": total_refs,
            "output_directory": str(self.output_dir)
        }


def main():
    """Test document assembly."""
    print("Testing Document Assembly Agent...")

    assembler = DocumentAssemblyAgent(
        equations_file=Path("results/rag_extractions/equation_extraction_results.json"),
        tables_file=Path("results/rag_extractions/table_extraction_results.json"),
        figures_file=Path("results/rag_extractions/figure_extraction_results.json"),
        text_file=Path("results/rag_extractions/text_extraction_results.json"),
        output_dir=Path("results/rag_extractions/assembled")
    )

    summary = assembler.assemble()

    print("\n✅ Assembly test complete")
    print(f"   Objects: {summary['total_objects']}")
    print(f"   References: {summary['total_references']}")


if __name__ == "__main__":
    main()
