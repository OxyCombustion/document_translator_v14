#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vector Database Interface - Abstract Base Class

Unified interface for vector database operations across ChromaDB and Pinecone.
Enables seamless switching between vector database backends via configuration.

Author: Claude Code
Date: 2025-11-20
Version: 1.0

Usage:
    from database_v14_P6.src.vector_db import ChromaDBAdapter, PineconeAdapter

    # Choose backend via configuration
    if config['vector_db']['backend'] == 'chromadb':
        db = ChromaDBAdapter(config['chromadb'])
    else:
        db = PineconeAdapter(config['pinecone'])

    # Use unified interface
    db.connect()
    collection = db.create_collection('my_collection', dimension=384)
    db.insert_chunks(collection, chunks, embeddings)
    results = db.query(collection, query_embedding, top_k=10)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


class VectorDatabaseInterface(ABC):
    """
    Abstract base class for vector database operations.

    All vector database adapters (ChromaDB, Pinecone, etc.) must implement
    this interface to ensure consistent behavior across backends.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize vector database adapter.

        Args:
            config: Configuration dictionary for the specific backend
        """
        self.config = config
        self.client = None
        self.connected = False

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to vector database.

        Returns:
            True if connection successful, False otherwise

        Example:
            >>> db = ChromaDBAdapter(config)
            >>> success = db.connect()
            >>> print(f"Connected: {success}")
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        Close connection to vector database.

        Returns:
            True if disconnection successful, False otherwise
        """
        pass

    @abstractmethod
    def create_collection(
        self,
        name: str,
        dimension: int,
        metadata: Optional[Dict[str, Any]] = None,
        overwrite: bool = False
    ) -> Any:
        """
        Create a new collection/index in the vector database.

        Args:
            name: Name of the collection/index
            dimension: Dimension of the embedding vectors
            metadata: Optional metadata for the collection
            overwrite: If True, delete existing collection with same name

        Returns:
            Collection/index object for the specific backend

        Example:
            >>> collection = db.create_collection(
            ...     name='thermodynamics',
            ...     dimension=384,
            ...     metadata={'source': 'chapter_4'}
            ... )
        """
        pass

    @abstractmethod
    def get_collection(self, name: str) -> Optional[Any]:
        """
        Get existing collection/index by name.

        Args:
            name: Name of the collection/index

        Returns:
            Collection/index object if found, None otherwise

        Example:
            >>> collection = db.get_collection('thermodynamics')
            >>> if collection:
            ...     print("Collection found")
        """
        pass

    @abstractmethod
    def delete_collection(self, name: str) -> bool:
        """
        Delete a collection/index.

        Args:
            name: Name of the collection/index to delete

        Returns:
            True if deletion successful, False otherwise

        Example:
            >>> success = db.delete_collection('old_collection')
        """
        pass

    @abstractmethod
    def list_collections(self) -> List[str]:
        """
        List all available collections/indexes.

        Returns:
            List of collection/index names

        Example:
            >>> collections = db.list_collections()
            >>> print(f"Available: {collections}")
        """
        pass

    @abstractmethod
    def insert_chunks(
        self,
        collection: Any,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        batch_size: Optional[int] = None
    ) -> Tuple[int, int]:
        """
        Batch insert chunks with embeddings into collection.

        Args:
            collection: Collection/index object
            chunks: List of chunk dictionaries with text and metadata
            embeddings: List of embedding vectors (same order as chunks)
            batch_size: Optional batch size (uses config default if None)

        Returns:
            Tuple of (successful_count, failed_count)

        Example:
            >>> chunks = [
            ...     {'chunk_id': 'c1', 'text': 'text1', 'metadata': {...}},
            ...     {'chunk_id': 'c2', 'text': 'text2', 'metadata': {...}}
            ... ]
            >>> embeddings = [[0.1, 0.2, ...], [0.3, 0.4, ...]]
            >>> success, failed = db.insert_chunks(collection, chunks, embeddings)
            >>> print(f"Inserted {success}, failed {failed}")
        """
        pass

    @abstractmethod
    def query(
        self,
        collection: Any,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        include_documents: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search query.

        Args:
            collection: Collection/index object
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filters: Optional metadata filters
            include_metadata: Include metadata in results
            include_documents: Include document text in results

        Returns:
            List of result dictionaries with id, score, metadata, document

        Example:
            >>> query_emb = model.encode("heat transfer")
            >>> results = db.query(
            ...     collection,
            ...     query_emb,
            ...     top_k=5,
            ...     filters={'page_number': {'$gte': 10}}
            ... )
            >>> for r in results:
            ...     print(f"Score: {r['score']:.3f} - {r['document'][:100]}")
        """
        pass

    @abstractmethod
    def get_collection_stats(self, collection: Any) -> Dict[str, Any]:
        """
        Get statistics about a collection.

        Args:
            collection: Collection/index object

        Returns:
            Dictionary with statistics (count, dimension, etc.)

        Example:
            >>> stats = db.get_collection_stats(collection)
            >>> print(f"Total vectors: {stats['count']}")
            >>> print(f"Dimension: {stats['dimension']}")
        """
        pass

    @abstractmethod
    def update_metadata(
        self,
        collection: Any,
        chunk_ids: List[str],
        metadata: List[Dict[str, Any]]
    ) -> int:
        """
        Update metadata for existing chunks.

        Args:
            collection: Collection/index object
            chunk_ids: List of chunk IDs to update
            metadata: List of metadata dictionaries (same order as chunk_ids)

        Returns:
            Number of chunks successfully updated

        Example:
            >>> updated = db.update_metadata(
            ...     collection,
            ...     ['c1', 'c2'],
            ...     [{'new_field': 'value1'}, {'new_field': 'value2'}]
            ... )
        """
        pass

    @abstractmethod
    def delete_chunks(
        self,
        collection: Any,
        chunk_ids: List[str]
    ) -> int:
        """
        Delete specific chunks from collection.

        Args:
            collection: Collection/index object
            chunk_ids: List of chunk IDs to delete

        Returns:
            Number of chunks successfully deleted

        Example:
            >>> deleted = db.delete_chunks(collection, ['c1', 'c2'])
        """
        pass

    def validate_embeddings(
        self,
        embeddings: List[List[float]],
        expected_dimension: int
    ) -> Tuple[bool, str]:
        """
        Validate embedding dimensions.

        Args:
            embeddings: List of embedding vectors
            expected_dimension: Expected dimension

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not embeddings:
            return False, "Empty embeddings list"

        for i, emb in enumerate(embeddings):
            if len(emb) != expected_dimension:
                return False, (
                    f"Embedding {i} has dimension {len(emb)}, "
                    f"expected {expected_dimension}"
                )

        return True, ""

    def validate_chunks(
        self,
        chunks: List[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """
        Validate chunk structure.

        Args:
            chunks: List of chunk dictionaries

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not chunks:
            return False, "Empty chunks list"

        required_fields = ['chunk_id', 'text']

        for i, chunk in enumerate(chunks):
            for field in required_fields:
                if field not in chunk:
                    return False, (
                        f"Chunk {i} missing required field: {field}"
                    )

        return True, ""

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
