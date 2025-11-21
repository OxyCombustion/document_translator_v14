#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert Chapter 3 RAG Output from JSON to JSONL Format

Converts the directory-per-section JSON array format used by Chapter 3
to the single JSONL file format expected by the database pipeline.

Author: Claude Code
Date: 2025-11-20
"""

import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Any

# UTF-8 setup
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')

print("=" * 80)
print("CONVERT CHAPTER 3 RAG OUTPUT TO JSONL FORMAT")
print("=" * 80)
print()

# Configuration
INPUT_DIR = Path("test_output_ch03_rag")
OUTPUT_FILE = INPUT_DIR / "rag_bundles.jsonl"
CITATION_GRAPH_FILE = INPUT_DIR / "citation_graph.json"

print(f"Input directory: {INPUT_DIR}")
print(f"Output JSONL: {OUTPUT_FILE}")
print(f"Output citation graph: {CITATION_GRAPH_FILE}")
print()

# Step 1: Find all chunks.json files
print("=" * 80)
print("STEP 1: DISCOVERING CHUNK FILES")
print("=" * 80)
print()

chunk_files = sorted(INPUT_DIR.glob("*/chunks.json"))
print(f"Found {len(chunk_files)} chunk files:")
for f in chunk_files:
    size_kb = f.stat().st_size / 1024
    print(f"  - {f.relative_to(INPUT_DIR)} ({size_kb:.1f} KB)")
print()

# Step 2: Load all chunks
print("=" * 80)
print("STEP 2: LOADING CHUNKS FROM JSON ARRAYS")
print("=" * 80)
print()

all_chunks = []
total_chars = 0

for chunk_file in chunk_files:
    section_name = chunk_file.parent.name
    print(f"Loading {section_name}...")

    with open(chunk_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    if not isinstance(chunks, list):
        print(f"  ERROR: Expected JSON array, got {type(chunks)}")
        continue

    print(f"  - Loaded {len(chunks)} chunks")

    # Add chunks to master list
    for chunk in chunks:
        all_chunks.append(chunk)
        total_chars += chunk.get('char_count', 0)
    print()

print(f"✓ Total chunks loaded: {len(all_chunks)}")
print(f"✓ Total characters: {total_chars:,}")
if all_chunks:
    print(f"✓ Average chunk size: {total_chars // len(all_chunks):,} chars")
print()

# Step 3: Write JSONL file
print("=" * 80)
print("STEP 3: WRITING JSONL FILE")
print("=" * 80)
print()

print(f"Writing to: {OUTPUT_FILE}")
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    for chunk in all_chunks:
        f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

output_size_kb = OUTPUT_FILE.stat().st_size / 1024
print(f"✓ Written {len(all_chunks)} chunks ({output_size_kb:.1f} KB)")
print()

# Step 4: Create stub citation graph
print("=" * 80)
print("STEP 4: CREATING STUB CITATION GRAPH")
print("=" * 80)
print()

citation_graph = {
    "document_name": "Ch-03_Fluid_Dynamics",
    "citation_stats": {
        "total_citations": 0,
        "by_type": {
            "figure": 0,
            "table": 0,
            "equation": 0,
            "chapter": 0,
            "reference": 0
        },
        "chunks_with_citations": 0,
        "chunks_without_citations": len(all_chunks)
    },
    "citations_by_chunk": {},
    "note": "Chapter 3 RAG output did not include citation extraction. This is a stub graph for database pipeline compatibility."
}

print(f"Writing to: {CITATION_GRAPH_FILE}")
with open(CITATION_GRAPH_FILE, 'w', encoding='utf-8') as f:
    json.dump(citation_graph, f, indent=2, ensure_ascii=False)

graph_size_kb = CITATION_GRAPH_FILE.stat().st_size / 1024
print(f"✓ Written stub citation graph ({graph_size_kb:.1f} KB)")
print()

# Summary
print("=" * 80)
print("CONVERSION COMPLETE")
print("=" * 80)
print()
print(f"✓ Converted {len(all_chunks)} chunks from JSON arrays to JSONL")
print(f"✓ Created stub citation graph (0 citations)")
print()
print("Output files:")
print(f"  - {OUTPUT_FILE} ({output_size_kb:.1f} KB)")
print(f"  - {CITATION_GRAPH_FILE} ({graph_size_kb:.1f} KB)")
print()
print("Ready for database ingestion pipeline!")
print()
