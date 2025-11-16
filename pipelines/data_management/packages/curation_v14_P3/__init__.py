"""
Curation Pipeline v14 P3

JSONL → Database curation and quality assurance pipeline.
Calibrates LLM confidence, validates domain specificity, manages novelty metadata,
and prepares data for production database storage.
"""

__version__ = "14.0.0"

from . import src

__all__ = ['src']
