#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vector Database Abstraction Layer

Provides unified interface for ChromaDB and Pinecone vector databases
with seamless switching via configuration.

Author: Claude Code
Date: 2025-11-20
Version: 1.0
"""

from .vector_database_interface import VectorDatabaseInterface
from .chromadb_adapter import ChromaDBAdapter
from .pinecone_adapter import PineconeAdapter

__all__ = [
    'VectorDatabaseInterface',
    'ChromaDBAdapter',
    'PineconeAdapter',
]
