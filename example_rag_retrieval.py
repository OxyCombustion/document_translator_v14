#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example RAG Retrieval - Demonstration of typical RAG use case

Shows how to retrieve relevant chunks from ChromaDB for answering questions
about heat transfer, with citation-aware context.

Author: Claude Code
Date: 2025-11-19
Version: 1.0
"""

from pathlib import Path
from typing import List, Dict, Any

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


# Configuration
CHROMA_DIR = Path("/home/thermodynamics/document_translator_v14/test_output_database/chromadb")
COLLECTION_NAME = "chapter_4_heat_transfer"


def get_collection() -> chromadb.Collection:
    """Initialize and return ChromaDB collection."""
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False)
    )

    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function
    )

    return collection


def retrieve_context(
    question: str,
    n_results: int = 3,
    include_citations: bool = True
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant context for a question.

    Args:
        question: User's question
        n_results: Number of chunks to retrieve
        include_citations: Whether to include citation information

    Returns:
        List of context dictionaries with text and metadata
    """
    collection = get_collection()

    results = collection.query(
        query_texts=[question],
        n_results=n_results
    )

    contexts = []
    for chunk_id, text, metadata in zip(
        results['ids'][0],
        results['documents'][0],
        results['metadatas'][0]
    ):
        context = {
            'chunk_id': chunk_id,
            'text': text,
            'section': metadata.get('section_title', 'Unknown'),
            'page': metadata.get('page_number', 'Unknown'),
        }

        if include_citations:
            context['citations'] = {
                'figures': metadata.get('cited_figures', '').split(',') if metadata.get('cited_figures') else [],
                'tables': metadata.get('cited_tables', '').split(',') if metadata.get('cited_tables') else [],
                'equations': metadata.get('cited_equations', '').split(',') if metadata.get('cited_equations') else [],
                'count': int(metadata.get('citation_count', 0))
            }

        contexts.append(context)

    return contexts


def format_context_for_llm(contexts: List[Dict[str, Any]]) -> str:
    """
    Format retrieved contexts for LLM prompt.

    Args:
        contexts: List of context dictionaries

    Returns:
        Formatted context string for LLM
    """
    formatted = []

    for i, ctx in enumerate(contexts, 1):
        chunk_info = f"[Chunk {i} - {ctx['section']}, Page {ctx['page']}]"
        formatted.append(chunk_info)

        # Add citation information
        citations = ctx.get('citations', {})
        if citations.get('count', 0) > 0:
            cite_parts = []
            if citations.get('figures'):
                cite_parts.append(f"Figures: {', '.join(citations['figures'])}")
            if citations.get('tables'):
                cite_parts.append(f"Tables: {', '.join(citations['tables'])}")
            if citations.get('equations'):
                cite_parts.append(f"Equations: {', '.join(citations['equations'])}")

            if cite_parts:
                formatted.append(f"Citations: {' | '.join(cite_parts)}")

        formatted.append(f"\n{ctx['text']}\n")
        formatted.append("-" * 80)

    return "\n".join(formatted)


def example_rag_query(question: str) -> None:
    """
    Demonstrate RAG retrieval for a question.

    Args:
        question: User's question
    """
    print(f"\n{'='*80}")
    print(f"RAG RETRIEVAL EXAMPLE")
    print(f"{'='*80}")
    print(f"\nQuestion: {question}\n")

    # Retrieve relevant contexts
    print("Retrieving relevant chunks...")
    contexts = retrieve_context(question, n_results=3)

    print(f"✓ Retrieved {len(contexts)} chunks\n")

    # Format for LLM
    formatted_context = format_context_for_llm(contexts)

    print(f"{'='*80}")
    print(f"RETRIEVED CONTEXT (for LLM)")
    print(f"{'='*80}\n")
    print(formatted_context)

    # Show how this would be used in a prompt
    print(f"\n{'='*80}")
    print(f"EXAMPLE LLM PROMPT")
    print(f"{'='*80}\n")

    prompt = f"""You are a heat transfer expert. Answer the question based on the provided context.

Context:
{formatted_context}

Question: {question}

Instructions:
- Use only information from the provided context
- Cite specific figures, tables, or equations when relevant
- If the context doesn't contain enough information, say so

Answer:"""

    print(prompt)


def main():
    """Run example RAG queries."""
    print("\n" + "="*80)
    print("PIPELINE 3 RAG RETRIEVAL EXAMPLES")
    print("="*80)
    print("\nThis script demonstrates how to use the ChromaDB collection")
    print("for typical RAG (Retrieval-Augmented Generation) use cases.")

    # Example 1: Convection heat transfer
    example_rag_query("What is convection heat transfer and how does it work?")

    # Example 2: Thermal conductivity
    print("\n\n" + "="*80)
    example_rag_query("Explain thermal conductivity and its role in heat transfer.")

    # Example 3: Radiation from gases
    print("\n\n" + "="*80)
    example_rag_query("How do combustion gases contribute to radiative heat transfer?")

    print("\n" + "="*80)
    print("Examples completed!")
    print("="*80)


if __name__ == '__main__':
    main()
