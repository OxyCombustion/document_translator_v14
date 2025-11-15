"""
RAG Pipeline v14 P2

JSON → JSONL+Graph RAG preparation pipeline.
Processes extracted JSON objects into RAG-ready formats with embeddings, relationships, and knowledge graphs.
"""

__version__ = "14.0.0"

from . import src

__all__ = ['src']
