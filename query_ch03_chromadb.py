#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive Query Tool for Chapter 3 ChromaDB Collection

Demonstrates semantic search capabilities on the Chapter 3 Fluid Dynamics
vector database.

Author: Claude Code
Date: 2025-11-20
"""

import sys
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from pathlib import Path

print("=" * 80)
print("CHAPTER 3 CHROMADB SEMANTIC SEARCH TOOL")
print("=" * 80)
print()

# Configuration
CHROMA_DIR = Path("/home/thermodynamics/document_translator_v14/test_output_database_ch03/chromadb")
COLLECTION_NAME = "chapter_3_fluid_dynamics"

# Initialize ChromaDB client
print(f"Connecting to ChromaDB...")
print(f"Database: {CHROMA_DIR}")
client = chromadb.PersistentClient(
    path=str(CHROMA_DIR),
    settings=Settings(anonymized_telemetry=False)
)

# Get collection
collection = client.get_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
)

print(f"✓ Connected to collection: {COLLECTION_NAME}")
print(f"✓ Total chunks: {collection.count()}")
print()

# Interactive query loop
print("=" * 80)
print("SEMANTIC SEARCH (type 'quit' to exit)")
print("=" * 80)
print()

print("Example queries:")
print("  - 'What is viscosity?'")
print("  - 'Explain conservation of momentum'")
print("  - 'How does turbulent flow work?'")
print("  - 'Surface tension in steam generators'")
print()

while True:
    print("-" * 80)
    query = input("Query: ").strip()

    if query.lower() in ['quit', 'exit', 'q']:
        print("\nExiting. Goodbye!")
        break

    if not query:
        continue

    print()
    print(f"Searching for: '{query}'")
    print()

    # Perform semantic search
    results = collection.query(
        query_texts=[query],
        n_results=3
    )

    # Display results
    for i, (chunk_id, text, metadata) in enumerate(zip(
        results['ids'][0],
        results['documents'][0],
        results['metadatas'][0]
    ), 1):
        print(f"Result {i}:")
        print(f"  Chunk ID: {chunk_id}")
        print(f"  Page: {metadata.get('page_number', 'N/A')}")
        print(f"  Section: {metadata.get('section_title', 'N/A')}")
        print(f"  Characters: {metadata.get('char_count', 'N/A')}")
        print()
        print(f"  Text:")
        # Print text with indentation
        for line in text.split('\n')[:15]:  # First 15 lines
            print(f"    {line}")
        if text.count('\n') > 15:
            print(f"    ... ({text.count('\\n') - 15} more lines)")
        print()
