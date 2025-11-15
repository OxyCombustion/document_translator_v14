# -*- coding: utf-8 -*-
"""
ChromaDB Setup for RAG Development

Sets up ChromaDB collection and ingests document package for retrieval.

Author: Document Translator V11
Date: 2025-01-17
"""

import sys
import os

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

import json
from pathlib import Path
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


class RAGDatabase:
    """
    ChromaDB-based RAG database for engineering content.

    Features:
    - Automatic embedding generation
    - Metadata filtering
    - Similarity search
    - Cross-reference graph integration
    """

    def __init__(self, db_path: Path, collection_name: str = "engineering_content"):
        """
        Initialize ChromaDB connection.

        Args:
            db_path: Path to ChromaDB storage directory
            collection_name: Name of collection to create/use
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Create sentence-transformer embedding function
        # This uses HuggingFace models instead of ONNX (more reliable)
        print("Initializing sentence-transformers embedding function...")
        print("(Will download ~90MB model from HuggingFace on first use)")

        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        # Get or create collection with sentence-transformers
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "Engineering content with equations, tables, and figures"}
        )

        print(f"ChromaDB initialized at: {self.db_path}")
        print(f"Collection: {collection_name}")

    def ingest_jsonl(self, jsonl_file: Path, batch_size: int = 10) -> int:
        """
        Ingest document package from JSONL file in batches.

        Args:
            jsonl_file: Path to JSONL file with content objects
            batch_size: Number of objects to process per batch

        Returns:
            Number of objects ingested
        """
        print(f"\nIngesting from: {jsonl_file}")
        print(f"Batch size: {batch_size}")

        documents = []
        metadatas = []
        ids = []
        total_ingested = 0

        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                obj = json.loads(line)

                # Extract text for embedding
                text = obj.get("text", "")
                if not text:
                    continue

                # Prepare metadata (ChromaDB requires simple types)
                metadata = {
                    "type": obj.get("type", "unknown"),
                    "page": obj.get("metadata", {}).get("page", 0),
                    "domain": obj.get("metadata", {}).get("domain", ""),
                    "quality": obj.get("metadata", {}).get("quality", 0.0),
                    # Add representations as metadata
                    "has_latex": bool(obj.get("representations", {}).get("latex")),
                    "has_image": bool(obj.get("representations", {}).get("image_path")),
                }

                documents.append(text)
                metadatas.append(metadata)
                ids.append(obj["id"])

                # Process batch when full
                if len(documents) >= batch_size:
                    print(f"  Processing batch {total_ingested//batch_size + 1} ({len(documents)} objects)...")
                    try:
                        self.collection.add(
                            documents=documents,
                            metadatas=metadatas,
                            ids=ids
                        )
                        total_ingested += len(documents)
                        print(f"    ✅ Batch complete ({total_ingested} total)")
                    except Exception as e:
                        print(f"    ⚠️  Batch failed: {e}")

                    # Clear batch
                    documents = []
                    metadatas = []
                    ids = []

        # Process remaining documents
        if documents:
            print(f"  Processing final batch ({len(documents)} objects)...")
            try:
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                total_ingested += len(documents)
                print(f"    ✅ Final batch complete")
            except Exception as e:
                print(f"    ⚠️  Final batch failed: {e}")

        print(f"\n✅ Ingested {total_ingested} objects total")
        return total_ingested

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        content_type: Optional[str] = None,
        min_quality: float = 0.0
    ) -> Dict:
        """
        Query the database with semantic search.

        Args:
            query_text: Text query for semantic search
            n_results: Number of results to return
            content_type: Filter by type (equation, table, figure, text)
            min_quality: Minimum quality score

        Returns:
            Query results with IDs, documents, metadata, distances
        """
        # Build where filter using $and operator for multiple conditions
        conditions = []

        if content_type:
            conditions.append({"type": content_type})

        if min_quality > 0:
            conditions.append({"quality": {"$gte": min_quality}})

        # Combine conditions with $and if multiple
        where_filter = None
        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

        # Execute query
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where_filter
        )

        return results

    def get_by_id(self, object_id: str) -> Optional[Dict]:
        """
        Retrieve object by ID.

        Args:
            object_id: Object identifier

        Returns:
            Object data or None if not found
        """
        results = self.collection.get(
            ids=[object_id],
            include=["documents", "metadatas"]
        )

        if results["ids"]:
            return {
                "id": results["ids"][0],
                "text": results["documents"][0],
                "metadata": results["metadatas"][0]
            }

        return None

    def get_stats(self) -> Dict:
        """
        Get database statistics.

        Returns:
            Statistics dictionary
        """
        count = self.collection.count()

        # Get all objects to calculate stats
        all_objects = self.collection.get(include=["metadatas"])

        types = {}
        for metadata in all_objects["metadatas"]:
            obj_type = metadata.get("type", "unknown")
            types[obj_type] = types.get(obj_type, 0) + 1

        return {
            "total_objects": count,
            "by_type": types,
            "collection_name": self.collection.name
        }

    def reset(self):
        """Reset the database (delete all content)."""
        self.client.reset()
        print("⚠️ Database reset complete")


# Main execution - setup and test
if __name__ == "__main__":
    print("=== ChromaDB Setup for RAG ===\n")

    # Paths
    base_dir = Path("E:/document_translator_v13")
    db_path = base_dir / "rag_database"
    jsonl_file = base_dir / "results/rag_package/document_package.jsonl"

    # Initialize database
    db = RAGDatabase(db_path)

    # Check if already populated
    stats = db.get_stats()
    print(f"\nCurrent stats: {stats}")

    if stats["total_objects"] > 0:
        print("\n⚠️  Database already contains data.")
        print("To re-ingest, delete the rag_database directory first.")
    else:
        # Ingest document package
        db.ingest_jsonl(jsonl_file)

        # Show stats
        stats = db.get_stats()
        print(f"\n=== Database Stats ===")
        print(f"Total objects: {stats['total_objects']}")
        print(f"By type:")
        for obj_type, count in stats['by_type'].items():
            print(f"  {obj_type}: {count}")

    # Test queries
    print("\n=== Test Queries ===\n")

    # Query 1: Find thermal conductivity equations
    print("Query 1: 'thermal conductivity'")
    results = db.query("thermal conductivity", n_results=3)
    for i, (id, doc, metadata, distance) in enumerate(zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    )):
        print(f"\n  Result {i+1}:")
        print(f"    ID: {id}")
        print(f"    Type: {metadata['type']}")
        print(f"    Page: {metadata['page']}")
        print(f"    Distance: {distance:.4f}")
        print(f"    Text: {doc[:100]}...")

    # Query 2: Find equations only
    print("\n\nQuery 2: 'heat transfer' (equations only)")
    results = db.query("heat transfer", n_results=3, content_type="equation")
    for i, (id, doc, metadata) in enumerate(zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0]
    )):
        print(f"\n  Result {i+1}:")
        print(f"    ID: {id}")
        print(f"    Type: {metadata['type']}")
        print(f"    Page: {metadata['page']}")
        print(f"    Has LaTeX: {metadata.get('has_latex', False)}")

    # Query 3: Find high-quality content
    print("\n\nQuery 3: 'radiation' (min quality 0.85)")
    results = db.query("radiation", n_results=3, min_quality=0.85)
    for i, (id, doc, metadata) in enumerate(zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0]
    )):
        print(f"\n  Result {i+1}:")
        print(f"    ID: {id}")
        print(f"    Quality: {metadata['quality']}")
        print(f"    Text: {doc[:80]}...")

    print(f"\n✅ ChromaDB setup complete!")
    print(f"Database location: {db_path}")
