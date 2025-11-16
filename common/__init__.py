"""
Common utilities for v14 architecture.

This package provides shared infrastructure used across all three pipelines:
- extraction_v14_P1 (PDF → JSON)
- rag_v14_P2 (JSON → JSONL+Graph)
- curation_v14_P3 (JSONL → Database)
"""

__version__ = "14.0.0"

from . import src

__all__ = ['src']
