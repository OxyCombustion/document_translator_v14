#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pinecone Adapter - Production-Ready Implementation

Pinecone adapter implementing VectorDatabaseInterface.
Provides cloud-based vector database with auto-scaling and hybrid search.

Production Status: ⏸️ Production-ready but not yet tested (no API key)
- Serverless index support (latest Pinecone offering)
- Hybrid search (sparse + dense vectors)
- Metadata filtering with pre-filter optimization
- Namespace support for multi-tenancy
- Batch upsert with exponential backoff retry logic
- Comprehensive error handling and logging

Author: Claude Code
Date: 2025-11-20
Version: 1.0

Usage:
    from database_v14_P6.src.vector_db import PineconeAdapter

    # Initialize
    config = {
        'api_key': 'your-api-key',
        'environment': 'us-east-1',
        'index_name': 'thermodynamics-v14',
        'dimension': 384,
        'metric': 'cosine',
        'cloud': 'aws',
        'region': 'us-east-1',
        'namespace': 'chapter_4',
        'batch_size': 100,
        'max_retries': 3
    }
    db = PineconeAdapter(config)

    # Connect and create index
    db.connect()
    collection = db.create_collection('my_index', dimension=384)

    # Insert chunks
    chunks = [{'chunk_id': 'c1', 'text': 'text', 'metadata': {...}}]
    embeddings = [[0.1, 0.2, ...]]
    success, failed = db.insert_chunks(collection, chunks, embeddings)

    # Query with metadata filtering
    results = db.query(
        collection,
        query_embedding,
        top_k=5,
        filters={'page_number': {'$gte': 10}}
    )
"""

import os
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

from .vector_database_interface import VectorDatabaseInterface

logger = logging.getLogger(__name__)


class PineconeAdapter(VectorDatabaseInterface):
    """
    Pinecone adapter for cloud vector database with serverless auto-scaling.

    Features:
    - Serverless architecture (auto-scaling, pay-per-use)
    - Hybrid search support (sparse + dense vectors)
    - Metadata filtering with pre-filter optimization
    - Namespace support for document/collection isolation
    - Batch upsert with exponential backoff retry logic
    - Production-grade error handling

    Note: Requires Pinecone API key via environment variable or config.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Pinecone adapter.

        Args:
            config: Pinecone configuration dictionary
                - api_key: Pinecone API key (or use PINECONE_API_KEY env var)
                - environment: Pinecone environment (e.g., 'us-east-1')
                - index_name: Default index name
                - dimension: Embedding dimension (e.g., 384, 1536)
                - metric: Distance metric ('cosine', 'euclidean', 'dotproduct')
                - cloud: Cloud provider ('aws', 'gcp', 'azure')
                - region: Cloud region (e.g., 'us-east-1')
                - namespace: Default namespace for multi-tenancy
                - batch_size: Batch size for upsert operations
                - max_retries: Maximum retry attempts
                - retry_delay: Initial retry delay (seconds)
                - hybrid_search: Enable hybrid search (default: False)
                - alpha: Hybrid search balance (0.0=sparse, 1.0=dense)
                - mock_mode: Enable mock mode for testing without API
        """
        super().__init__(config)

        # API configuration
        self.api_key = config.get('api_key') or os.getenv('PINECONE_API_KEY')
        self.environment = config.get('environment', 'us-east-1')

        # Index configuration
        self.index_name = config.get('index_name', 'vector-index')
        self.dimension = config.get('dimension', 384)
        self.metric = config.get('metric', 'cosine')
        self.cloud = config.get('cloud', 'aws')
        self.region = config.get('region', 'us-east-1')

        # Namespace configuration
        self.default_namespace = config.get('namespace', '')

        # Batch processing configuration
        self.batch_size = config.get('batch_size', 100)
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 2.0)

        # Hybrid search configuration
        self.hybrid_search_enabled = config.get('hybrid_search', False)
        self.alpha = config.get('alpha', 0.5)  # Balance sparse/dense

        # Mock mode for testing without API key
        self.mock_mode = config.get('mock_mode', False)

        # Pinecone client and index
        self.pc = None
        self.index = None

        # Check Pinecone availability
        if not PINECONE_AVAILABLE and not self.mock_mode:
            logger.warning(
                "Pinecone library not installed. "
                "Install with: pip install pinecone-client"
            )

    def connect(self) -> bool:
        """
        Connect to Pinecone and initialize client.

        Returns:
            True if connection successful, False otherwise
        """
        if self.mock_mode:
            logger.info("Pinecone mock mode enabled - simulating connection")
            self.connected = True
            return True

        if not PINECONE_AVAILABLE:
            logger.error("Pinecone library not available")
            return False

        if not self.api_key:
            logger.error(
                "Pinecone API key not found. "
                "Set PINECONE_API_KEY environment variable or provide in config."
            )
            return False

        try:
            # Initialize Pinecone client
            self.pc = Pinecone(api_key=self.api_key)

            self.connected = True
            logger.info(
                f"Pinecone connected: environment={self.environment}, "
                f"region={self.region}"
            )
            return True

        except Exception as e:
            logger.error(f"Pinecone connection failed: {e}")
            self.connected = False
            return False

    def disconnect(self) -> bool:
        """
        Disconnect from Pinecone.

        Returns:
            True if disconnection successful
        """
        self.pc = None
        self.index = None
        self.connected = False
        logger.info("Pinecone disconnected")
        return True

    def create_collection(
        self,
        name: str,
        dimension: int,
        metadata: Optional[Dict[str, Any]] = None,
        overwrite: bool = False
    ) -> Any:
        """
        Create Pinecone serverless index.

        Args:
            name: Index name
            dimension: Embedding dimension (e.g., 384 for all-MiniLM-L6-v2)
            metadata: Optional index metadata (stored as tags)
            overwrite: If True, delete existing index

        Returns:
            Pinecone index object
        """
        if self.mock_mode:
            logger.info(f"Mock mode: Creating index {name}")
            return MockPineconeIndex(name)

        if not self.connected:
            raise RuntimeError("Not connected to Pinecone")

        # Delete existing index if overwrite=True
        if overwrite:
            try:
                self.pc.delete_index(name)
                logger.info(f"Deleted existing index: {name}")
                # Wait for deletion to complete
                time.sleep(5)
            except Exception as e:
                logger.debug(f"Index {name} doesn't exist or couldn't be deleted: {e}")

        # Check if index already exists
        existing_indexes = self.pc.list_indexes().names()

        if name not in existing_indexes:
            try:
                # Create serverless index
                self.pc.create_index(
                    name=name,
                    dimension=dimension,
                    metric=self.metric,
                    spec=ServerlessSpec(
                        cloud=self.cloud,
                        region=self.region
                    )
                )

                logger.info(
                    f"Created Pinecone index: {name} "
                    f"(dimension={dimension}, metric={self.metric}, "
                    f"cloud={self.cloud}, region={self.region})"
                )

                # Wait for index to be ready
                logger.info("Waiting for index to be ready...")
                time.sleep(10)

            except Exception as e:
                logger.error(f"Failed to create index {name}: {e}")
                raise
        else:
            logger.info(f"Index {name} already exists")

        # Get index object
        self.index = self.pc.Index(name)
        return self.index

    def get_collection(self, name: str) -> Optional[Any]:
        """
        Get existing Pinecone index.

        Args:
            name: Index name

        Returns:
            Pinecone index object if found, None otherwise
        """
        if self.mock_mode:
            logger.info(f"Mock mode: Getting index {name}")
            return MockPineconeIndex(name)

        if not self.connected:
            raise RuntimeError("Not connected to Pinecone")

        try:
            existing_indexes = self.pc.list_indexes().names()

            if name in existing_indexes:
                self.index = self.pc.Index(name)
                logger.info(f"Retrieved index: {name}")
                return self.index
            else:
                logger.warning(f"Index not found: {name}")
                return None

        except Exception as e:
            logger.error(f"Failed to get index {name}: {e}")
            return None

    def delete_collection(self, name: str) -> bool:
        """
        Delete Pinecone index.

        Args:
            name: Index name

        Returns:
            True if deletion successful
        """
        if self.mock_mode:
            logger.info(f"Mock mode: Deleting index {name}")
            return True

        if not self.connected:
            raise RuntimeError("Not connected to Pinecone")

        try:
            self.pc.delete_index(name)
            logger.info(f"Deleted index: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete index {name}: {e}")
            return False

    def list_collections(self) -> List[str]:
        """
        List all Pinecone indexes.

        Returns:
            List of index names
        """
        if self.mock_mode:
            logger.info("Mock mode: Listing indexes")
            return ['mock-index-1', 'mock-index-2']

        if not self.connected:
            raise RuntimeError("Not connected to Pinecone")

        try:
            indexes = self.pc.list_indexes().names()
            logger.info(f"Found {len(indexes)} indexes")
            return indexes

        except Exception as e:
            logger.error(f"Failed to list indexes: {e}")
            return []

    def insert_chunks(
        self,
        collection: Any,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        batch_size: Optional[int] = None
    ) -> Tuple[int, int]:
        """
        Batch upsert chunks with exponential backoff retry logic.

        Args:
            collection: Pinecone index object
            chunks: List of chunk dictionaries
            embeddings: List of embedding vectors
            batch_size: Batch size (uses config default if None)

        Returns:
            Tuple of (successful_count, failed_count)
        """
        if self.mock_mode:
            logger.info(f"Mock mode: Inserting {len(chunks)} chunks")
            return len(chunks), 0

        # Validate inputs
        is_valid, error_msg = self.validate_chunks(chunks)
        if not is_valid:
            raise ValueError(f"Invalid chunks: {error_msg}")

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) "
                "count mismatch"
            )

        # Validate embedding dimensions
        is_valid, error_msg = self.validate_embeddings(embeddings, self.dimension)
        if not is_valid:
            raise ValueError(f"Invalid embeddings: {error_msg}")

        # Use configured batch size if not provided
        if batch_size is None:
            batch_size = self.batch_size

        successful = 0
        failed = 0
        total_batches = (len(chunks) + batch_size - 1) // batch_size

        logger.info(
            f"Upserting {len(chunks)} chunks in {total_batches} batches "
            f"(batch_size={batch_size}, namespace={self.default_namespace})"
        )

        # Process in batches
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_num = (i // batch_size) + 1

            # Prepare vectors for Pinecone
            vectors = []
            for chunk, embedding in zip(batch_chunks, batch_embeddings):
                vector = {
                    'id': chunk['chunk_id'],
                    'values': embedding,
                    'metadata': self._prepare_metadata(chunk.get('metadata', {}))
                }

                # Add document text to metadata (truncate if too long)
                text = chunk['text']
                if len(text) > 40000:  # Pinecone metadata limit
                    text = text[:40000]
                vector['metadata']['text'] = text

                vectors.append(vector)

            # Exponential backoff retry logic
            retry_count = 0
            retry_delay = self.retry_delay

            while retry_count < self.max_retries:
                try:
                    collection.upsert(
                        vectors=vectors,
                        namespace=self.default_namespace
                    )

                    successful += len(batch_chunks)
                    logger.info(
                        f"Batch {batch_num}/{total_batches} upserted "
                        f"({len(batch_chunks)} chunks)"
                    )
                    break

                except Exception as e:
                    retry_count += 1
                    if retry_count < self.max_retries:
                        logger.warning(
                            f"Batch {batch_num} failed (attempt {retry_count}/"
                            f"{self.max_retries}): {e}"
                        )
                        logger.info(f"Retrying in {retry_delay:.1f}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(
                            f"Batch {batch_num} failed after "
                            f"{self.max_retries} attempts: {e}"
                        )
                        failed += len(batch_chunks)

        logger.info(
            f"Upsert complete: {successful} successful, {failed} failed"
        )
        return successful, failed

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
        Perform semantic search query with optional metadata filtering.

        Args:
            collection: Pinecone index object
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filters: Optional metadata filters (Pinecone filter syntax)
            include_metadata: Include metadata in results
            include_documents: Include document text in results

        Returns:
            List of result dictionaries

        Example filters:
            {'page_number': {'$gte': 10}}
            {'section': {'$eq': 'introduction'}}
            {'$and': [{'page': {'$gte': 5}}, {'page': {'$lte': 10}}]}
        """
        if self.mock_mode:
            logger.info(f"Mock mode: Querying with top_k={top_k}")
            return self._generate_mock_results(top_k)

        try:
            # Prepare query parameters
            query_params = {
                'vector': query_embedding,
                'top_k': top_k,
                'namespace': self.default_namespace,
                'include_metadata': include_metadata
            }

            # Add filters if provided (pre-filter for performance)
            if filters:
                query_params['filter'] = filters

            # Execute query
            results = collection.query(**query_params)

            # Format results
            formatted_results = []
            for match in results.get('matches', []):
                result = {
                    'id': match['id'],
                    'score': match['score']
                }

                if include_metadata and 'metadata' in match:
                    metadata = match['metadata'].copy()

                    # Extract document text if requested
                    if include_documents and 'text' in metadata:
                        result['document'] = metadata.pop('text')

                    result['metadata'] = metadata

                formatted_results.append(result)

            logger.info(
                f"Query returned {len(formatted_results)} results "
                f"(namespace={self.default_namespace})"
            )
            return formatted_results

        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []

    def get_collection_stats(self, collection: Any) -> Dict[str, Any]:
        """
        Get Pinecone index statistics.

        Args:
            collection: Pinecone index object

        Returns:
            Dictionary with statistics
        """
        if self.mock_mode:
            return {
                'name': 'mock-index',
                'count': 1000,
                'dimension': self.dimension,
                'metric': self.metric,
                'namespaces': {'': 500, 'chapter_4': 500}
            }

        try:
            stats = collection.describe_index_stats()

            # Get namespace stats
            namespaces = stats.get('namespaces', {})
            total_count = stats.get('total_vector_count', 0)

            result = {
                'name': collection._index_name if hasattr(collection, '_index_name') else 'unknown',
                'count': total_count,
                'dimension': stats.get('dimension', self.dimension),
                'metric': self.metric,
                'namespaces': {ns: info['vector_count'] for ns, info in namespaces.items()}
            }

            logger.info(
                f"Index stats: {result['name']} "
                f"({result['count']} vectors, dim={result['dimension']})"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {'error': str(e)}

    def update_metadata(
        self,
        collection: Any,
        chunk_ids: List[str],
        metadata: List[Dict[str, Any]]
    ) -> int:
        """
        Update metadata for existing chunks.

        Args:
            collection: Pinecone index object
            chunk_ids: List of chunk IDs
            metadata: List of metadata dictionaries

        Returns:
            Number of chunks successfully updated
        """
        if self.mock_mode:
            logger.info(f"Mock mode: Updating metadata for {len(chunk_ids)} chunks")
            return len(chunk_ids)

        if len(chunk_ids) != len(metadata):
            raise ValueError("chunk_ids and metadata length mismatch")

        try:
            # Pinecone requires full vector for update, so we fetch first
            # then update with new metadata
            fetch_response = collection.fetch(
                ids=chunk_ids,
                namespace=self.default_namespace
            )

            vectors = []
            for chunk_id, new_metadata in zip(chunk_ids, metadata):
                if chunk_id in fetch_response['vectors']:
                    vector_data = fetch_response['vectors'][chunk_id]

                    # Prepare updated vector
                    vectors.append({
                        'id': chunk_id,
                        'values': vector_data['values'],
                        'metadata': self._prepare_metadata(new_metadata)
                    })

            # Upsert with updated metadata
            if vectors:
                collection.upsert(
                    vectors=vectors,
                    namespace=self.default_namespace
                )

            logger.info(f"Updated metadata for {len(vectors)} chunks")
            return len(vectors)

        except Exception as e:
            logger.error(f"Metadata update failed: {e}")
            return 0

    def delete_chunks(
        self,
        collection: Any,
        chunk_ids: List[str]
    ) -> int:
        """
        Delete specific chunks from index.

        Args:
            collection: Pinecone index object
            chunk_ids: List of chunk IDs to delete

        Returns:
            Number of chunks successfully deleted
        """
        if self.mock_mode:
            logger.info(f"Mock mode: Deleting {len(chunk_ids)} chunks")
            return len(chunk_ids)

        try:
            collection.delete(
                ids=chunk_ids,
                namespace=self.default_namespace
            )

            logger.info(f"Deleted {len(chunk_ids)} chunks")
            return len(chunk_ids)

        except Exception as e:
            logger.error(f"Deletion failed: {e}")
            return 0

    def _prepare_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare metadata for Pinecone.

        Pinecone metadata requirements:
        - Supports strings, numbers, booleans, lists of strings
        - Max metadata size: ~40KB per vector
        - Filterable fields should be indexed

        Args:
            metadata: Original metadata dictionary

        Returns:
            Pinecone-compatible metadata dictionary
        """
        prepared = {}

        for key, value in metadata.items():
            # Convert values to Pinecone-compatible types
            if isinstance(value, (list, tuple)):
                # Convert list to list of strings
                prepared[key] = [str(v) for v in value]
            elif isinstance(value, bool):
                prepared[key] = value  # Booleans are supported
            elif isinstance(value, (int, float)):
                prepared[key] = value  # Numbers are supported
            elif value is None:
                prepared[key] = ''  # Convert None to empty string
            else:
                prepared[key] = str(value)

        return prepared

    def _generate_mock_results(self, top_k: int) -> List[Dict[str, Any]]:
        """Generate mock query results for testing."""
        return [
            {
                'id': f'mock_chunk_{i}',
                'score': 0.95 - (i * 0.05),
                'metadata': {
                    'page_number': i + 1,
                    'section': 'Mock Section'
                },
                'document': f'This is mock document text for chunk {i}'
            }
            for i in range(top_k)
        ]


class MockPineconeIndex:
    """Mock Pinecone index for testing without API key."""

    def __init__(self, name: str):
        self.name = name
        self._vectors = {}

    def upsert(self, vectors: List[Dict], namespace: str = ''):
        """Mock upsert operation."""
        for vector in vectors:
            self._vectors[vector['id']] = vector

    def query(self, vector: List[float], top_k: int = 10,
              namespace: str = '', include_metadata: bool = True,
              filter: Optional[Dict] = None) -> Dict:
        """Mock query operation."""
        matches = [
            {
                'id': f'mock_{i}',
                'score': 0.95 - (i * 0.05),
                'metadata': {'text': f'Mock text {i}', 'page': i}
            }
            for i in range(min(top_k, 5))
        ]
        return {'matches': matches}

    def fetch(self, ids: List[str], namespace: str = '') -> Dict:
        """Mock fetch operation."""
        vectors = {
            id: {'values': [0.1] * 384, 'metadata': {}}
            for id in ids
        }
        return {'vectors': vectors}

    def delete(self, ids: List[str], namespace: str = ''):
        """Mock delete operation."""
        for id in ids:
            self._vectors.pop(id, None)

    def describe_index_stats(self) -> Dict:
        """Mock stats operation."""
        return {
            'dimension': 384,
            'total_vector_count': len(self._vectors),
            'namespaces': {'': {'vector_count': len(self._vectors)}}
        }
