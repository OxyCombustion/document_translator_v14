# -*- coding: utf-8 -*-
"""
Tests for RAGOutput Contract

Tests validation, serialization, and round-trip conversion.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from pipelines.shared.contracts.rag_output import (
    RAGOutput,
    RAGBundle,
    RAGMetadata
)


class TestRAGBundle:
    """Tests for RAGBundle dataclass."""

    def test_valid_equation_bundle(self):
        """Test valid equation bundle."""
        bundle = RAGBundle(
            bundle_id="bundle:eq9_complete",
            bundle_type="equation",
            entity_id="eq:9",
            content={"latex": "E = mc^2", "description": "Mass-energy equivalence"},
            usage_guidance={"when_to_use": "Energy calculations"},
            semantic_tags=["energy", "mass", "relativity"],
            embedding_metadata={"source_page": 42}
        )
        assert bundle.validate()

    def test_invalid_bundle_id_prefix(self):
        """Test invalid bundle_id prefix."""
        bundle = RAGBundle(
            bundle_id="invalid:eq9",
            bundle_type="equation",
            entity_id="eq:9",
            content={"latex": "E = mc^2"},
            usage_guidance={},
            semantic_tags=["test"],
            embedding_metadata={}
        )
        with pytest.raises(ValueError, match="bundle_id must start with 'bundle:'"):
            bundle.validate()

    def test_invalid_bundle_type(self):
        """Test invalid bundle_type."""
        bundle = RAGBundle(
            bundle_id="bundle:test",
            bundle_type="invalid_type",
            entity_id="eq:9",
            content={"test": "data"},
            usage_guidance={},
            semantic_tags=["test"],
            embedding_metadata={}
        )
        with pytest.raises(ValueError, match="bundle_type must be one of"):
            bundle.validate()

    def test_invalid_entity_id_prefix(self):
        """Test invalid entity_id prefix."""
        bundle = RAGBundle(
            bundle_id="bundle:test",
            bundle_type="equation",
            entity_id="invalid:9",
            content={"test": "data"},
            usage_guidance={},
            semantic_tags=["test"],
            embedding_metadata={}
        )
        with pytest.raises(ValueError, match="entity_id must start with"):
            bundle.validate()

    def test_empty_content(self):
        """Test empty content."""
        bundle = RAGBundle(
            bundle_id="bundle:test",
            bundle_type="equation",
            entity_id="eq:9",
            content={},  # Empty
            usage_guidance={},
            semantic_tags=["test"],
            embedding_metadata={}
        )
        with pytest.raises(ValueError, match="content cannot be empty"):
            bundle.validate()

    def test_token_count_estimation(self):
        """Test token count estimation."""
        bundle = RAGBundle(
            bundle_id="bundle:eq9_complete",
            bundle_type="equation",
            entity_id="eq:9",
            content={"latex": "E = mc^2" * 100},  # Long content
            usage_guidance={"test": "data"},
            semantic_tags=["energy"],
            embedding_metadata={}
        )
        token_count = bundle.estimate_token_count()
        assert token_count > 0
        assert isinstance(token_count, int)


class TestRAGMetadata:
    """Tests for RAGMetadata dataclass."""

    def test_valid_metadata(self):
        """Test valid RAG metadata."""
        metadata = RAGMetadata(
            source_document_id="test_doc",
            processing_timestamp=datetime.now().isoformat(),
            total_bundles=10,
            bundles_by_type={"equation": 5, "table": 3, "concept": 2},
            total_relationships=42,
            semantic_chunks_created=34,
            citations_extracted=128
        )
        assert metadata.validate()

    def test_empty_source_document_id(self):
        """Test empty source_document_id."""
        metadata = RAGMetadata(
            source_document_id="",
            processing_timestamp=datetime.now().isoformat()
        )
        with pytest.raises(ValueError, match="source_document_id cannot be empty"):
            metadata.validate()

    def test_invalid_timestamp(self):
        """Test invalid timestamp."""
        metadata = RAGMetadata(
            source_document_id="test_doc",
            processing_timestamp="invalid-timestamp"
        )
        with pytest.raises(ValueError, match="processing_timestamp must be valid ISO 8601"):
            metadata.validate()

    def test_negative_counts(self):
        """Test negative counts."""
        metadata = RAGMetadata(
            source_document_id="test_doc",
            processing_timestamp=datetime.now().isoformat(),
            total_bundles=-1
        )
        with pytest.raises(ValueError, match="total_bundles must be >= 0"):
            metadata.validate()


class TestRAGOutput:
    """Tests for RAGOutput dataclass."""

    def create_valid_rag_output(self):
        """Helper to create valid RAGOutput."""
        bundle = RAGBundle(
            bundle_id="bundle:eq1_complete",
            bundle_type="equation",
            entity_id="eq:1",
            content={"latex": "E = mc^2", "description": "Mass-energy equivalence"},
            usage_guidance={"when_to_use": "Energy calculations"},
            semantic_tags=["energy", "mass"],
            embedding_metadata={"source_page": 1}
        )
        metadata = RAGMetadata(
            source_document_id="test_doc",
            processing_timestamp=datetime.now().isoformat(),
            total_bundles=1,
            bundles_by_type={"equation": 1},
            total_relationships=5
        )
        return RAGOutput(
            document_id="test_doc",
            bundles=[bundle],
            metadata=metadata
        )

    def test_valid_rag_output(self):
        """Test valid RAG output."""
        output = self.create_valid_rag_output()
        assert output.validate()

    def test_empty_document_id(self):
        """Test empty document_id."""
        output = self.create_valid_rag_output()
        output.document_id = ""
        with pytest.raises(ValueError, match="document_id cannot be empty"):
            output.validate()

    def test_document_id_mismatch(self):
        """Test document_id mismatch with metadata."""
        output = self.create_valid_rag_output()
        output.metadata.source_document_id = "different_doc"
        with pytest.raises(ValueError, match="document_id mismatch"):
            output.validate()

    def test_bundle_count_mismatch(self):
        """Test bundle count mismatch with metadata."""
        output = self.create_valid_rag_output()
        output.metadata.total_bundles = 5  # Says 5 but only has 1
        with pytest.raises(ValueError, match="Bundle count mismatch"):
            output.validate()

    def test_bundle_type_count_mismatch(self):
        """Test bundle type count mismatch."""
        output = self.create_valid_rag_output()
        output.metadata.bundles_by_type = {"equation": 2}  # Says 2 but only has 1
        with pytest.raises(ValueError, match="Bundle type 'equation' count mismatch"):
            output.validate()

    def test_validate_completeness_empty(self):
        """Test completeness validation with no bundles."""
        output = self.create_valid_rag_output()
        output.bundles = []
        output.metadata.total_bundles = 0
        with pytest.raises(ValueError, match="No bundles created"):
            output.validate_completeness()

    def test_to_dict_conversion(self):
        """Test conversion to dictionary."""
        output = self.create_valid_rag_output()
        data = output.to_dict()
        assert isinstance(data, dict)
        assert data['document_id'] == "test_doc"
        assert len(data['bundles']) == 1
        assert data['bundles'][0]['bundle_id'] == "bundle:eq1_complete"

    def test_round_trip_json_serialization(self):
        """Test JSON save and load round-trip."""
        output = self.create_valid_rag_output()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "rag_output.json"

            # Save
            output.to_json_file(filepath)
            assert filepath.exists()

            # Load
            loaded_output = RAGOutput.from_json_file(filepath)

            # Verify
            assert loaded_output.document_id == output.document_id
            assert len(loaded_output.bundles) == len(output.bundles)
            assert loaded_output.bundles[0].bundle_id == output.bundles[0].bundle_id
            assert loaded_output.metadata.total_bundles == output.metadata.total_bundles

    def test_round_trip_jsonl_serialization(self):
        """Test JSONL save and load round-trip."""
        output = self.create_valid_rag_output()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "rag_output.jsonl"

            # Save
            output.to_jsonl_file(filepath)
            assert filepath.exists()

            # Load
            loaded_output = RAGOutput.from_jsonl_file(filepath, document_id="test_doc")

            # Verify
            assert loaded_output.document_id == output.document_id
            assert len(loaded_output.bundles) == len(output.bundles)
            assert loaded_output.bundles[0].bundle_id == output.bundles[0].bundle_id

    def test_summary_generation(self):
        """Test summary generation."""
        output = self.create_valid_rag_output()
        summary = output.summary()
        assert summary['document_id'] == "test_doc"
        assert summary['total_bundles'] == 1
        assert summary['bundles_by_type'] == {"equation": 1}
        assert summary['total_relationships'] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
