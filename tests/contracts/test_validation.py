# -*- coding: utf-8 -*-
"""
Tests for Contract Validation Utilities

Tests validation functions for pipeline handoffs.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from pipelines.shared.contracts.extraction_output import (
    ExtractionOutput,
    ExtractedObject,
    BoundingBox,
    ExtractionMetadata,
    ExtractionQuality
)
from pipelines.shared.contracts.rag_output import (
    RAGOutput,
    RAGBundle,
    RAGMetadata
)
from pipelines.shared.contracts.validation import (
    ContractValidationError,
    validate_extraction_output,
    validate_rag_output,
    validate_extraction_to_rag_handoff,
    validate_rag_to_database_handoff,
    validate_pipeline_handoff
)


class TestValidateExtractionOutput:
    """Tests for validate_extraction_output function."""

    def create_valid_extraction_output(self, quality_score=0.93):
        """Helper to create valid ExtractionOutput."""
        bbox = BoundingBox(page=1, x0=100.0, y0=200.0, x1=400.0, y1=300.0)
        obj = ExtractedObject(
            object_id="eq_1",
            object_type="equation",
            bbox=bbox,
            file_path="/tmp/eq_1.png",
            confidence=0.95
        )
        quality = ExtractionQuality(
            overall_score=quality_score,
            equations_extracted=1
        )
        metadata = ExtractionMetadata(
            source_filename="test.pdf",
            page_count=10,
            extraction_quality=quality
        )
        return ExtractionOutput(
            document_id="test_doc",
            extraction_timestamp=datetime.now().isoformat(),
            objects=[obj],
            metadata=metadata
        )

    def test_valid_extraction(self):
        """Test validation of valid extraction output."""
        output = self.create_valid_extraction_output()
        assert validate_extraction_output(output)

    def test_low_quality_score(self):
        """Test rejection of low quality extraction."""
        output = self.create_valid_extraction_output(quality_score=0.3)
        with pytest.raises(ContractValidationError, match="quality too low"):
            validate_extraction_output(output, min_quality_score=0.5)

    def test_empty_content(self):
        """Test rejection of empty extraction."""
        output = self.create_valid_extraction_output()
        output.objects = []
        output.metadata.extraction_quality.equations_extracted = 0
        with pytest.raises(ContractValidationError, match="contains no objects"):
            validate_extraction_output(output, require_content=True)

    def test_invalid_structure(self):
        """Test validation of invalid structure."""
        output = self.create_valid_extraction_output()
        output.document_id = ""  # Invalid
        with pytest.raises(ContractValidationError):
            validate_extraction_output(output)


class TestValidateRAGOutput:
    """Tests for validate_rag_output function."""

    def create_valid_rag_output(self, num_bundles=1):
        """Helper to create valid RAGOutput."""
        bundles = []
        for i in range(num_bundles):
            bundle = RAGBundle(
                bundle_id=f"bundle:eq{i+1}_complete",
                bundle_type="equation",
                entity_id=f"eq:{i+1}",
                content={"latex": f"E = mc^{i+2}"},
                usage_guidance={},
                semantic_tags=["energy"],
                embedding_metadata={}
            )
            bundles.append(bundle)

        metadata = RAGMetadata(
            source_document_id="test_doc",
            processing_timestamp=datetime.now().isoformat(),
            total_bundles=num_bundles,
            bundles_by_type={"equation": num_bundles},
            total_relationships=5 * num_bundles
        )
        return RAGOutput(
            document_id="test_doc",
            bundles=bundles,
            metadata=metadata
        )

    def test_valid_rag_output(self):
        """Test validation of valid RAG output."""
        output = self.create_valid_rag_output()
        assert validate_rag_output(output)

    def test_too_few_bundles(self):
        """Test rejection of too few bundles."""
        output = self.create_valid_rag_output(num_bundles=0)
        output.metadata.total_bundles = 0
        with pytest.raises(ContractValidationError, match="too few bundles"):
            validate_rag_output(output, min_bundles=1)

    def test_no_relationships_warning(self, caplog):
        """Test warning for no relationships."""
        output = self.create_valid_rag_output()
        output.metadata.total_relationships = 0
        # Should pass but warn
        assert validate_rag_output(output, require_relationships=True)

    def test_oversized_bundles_warning(self, caplog):
        """Test warning for oversized bundles."""
        output = self.create_valid_rag_output()
        # Create bundle with huge content
        output.bundles[0].content = {"latex": "E = mc^2" * 1000}
        # Should pass but warn
        assert validate_rag_output(output, max_bundle_tokens=100)


class TestValidateExtractionToRAGHandoff:
    """Tests for validate_extraction_to_rag_handoff function."""

    def create_valid_extraction_output(self):
        """Helper to create valid ExtractionOutput."""
        bbox = BoundingBox(page=1, x0=100.0, y0=200.0, x1=400.0, y1=300.0)
        obj = ExtractedObject(
            object_id="eq_1",
            object_type="equation",
            bbox=bbox,
            file_path="/tmp/eq_1.png",
            confidence=0.95
        )
        quality = ExtractionQuality(
            overall_score=0.93,
            equations_extracted=1
        )
        metadata = ExtractionMetadata(
            source_filename="test.pdf",
            page_count=10,
            extraction_quality=quality
        )
        return ExtractionOutput(
            document_id="test_doc",
            extraction_timestamp=datetime.now().isoformat(),
            objects=[obj],
            metadata=metadata
        )

    def test_valid_handoff(self):
        """Test valid extraction→RAG handoff."""
        output = self.create_valid_extraction_output()
        assert validate_extraction_to_rag_handoff(output)

    def test_missing_source_filename(self):
        """Test rejection when source_filename missing."""
        output = self.create_valid_extraction_output()
        output.metadata.source_filename = ""
        with pytest.raises(ContractValidationError, match="Missing source_filename"):
            validate_extraction_to_rag_handoff(output)

    def test_invalid_page_count(self):
        """Test rejection of invalid page count."""
        output = self.create_valid_extraction_output()
        output.metadata.page_count = 0
        with pytest.raises(ContractValidationError):
            validate_extraction_to_rag_handoff(output)


class TestValidateRAGToDatabaseHandoff:
    """Tests for validate_rag_to_database_handoff function."""

    def create_valid_rag_output(self):
        """Helper to create valid RAGOutput."""
        bundle = RAGBundle(
            bundle_id="bundle:eq1_complete",
            bundle_type="equation",
            entity_id="eq:1",
            content={"latex": "E = mc^2"},
            usage_guidance={},
            semantic_tags=["energy"],
            embedding_metadata={"source_page": 1}
        )
        metadata = RAGMetadata(
            source_document_id="test_doc",
            processing_timestamp=datetime.now().isoformat(),
            total_bundles=1,
            bundles_by_type={"equation": 1}
        )
        return RAGOutput(
            document_id="test_doc",
            bundles=[bundle],
            metadata=metadata
        )

    def test_valid_handoff(self):
        """Test valid RAG→Database handoff."""
        output = self.create_valid_rag_output()
        assert validate_rag_to_database_handoff(output)

    def test_missing_embedding_metadata_warning(self, caplog):
        """Test warning for missing embedding metadata."""
        output = self.create_valid_rag_output()
        output.bundles[0].embedding_metadata = {}
        # Should pass but warn
        assert validate_rag_to_database_handoff(output)

    def test_missing_semantic_tags_warning(self, caplog):
        """Test warning for missing semantic tags."""
        output = self.create_valid_rag_output()
        output.bundles[0].semantic_tags = []
        # Should pass but warn
        assert validate_rag_to_database_handoff(output)


class TestValidatePipelineHandoff:
    """Tests for validate_pipeline_handoff convenience function."""

    def test_extraction_to_rag_handoff(self):
        """Test extraction→RAG handoff from file."""
        # Create and save extraction output
        bbox = BoundingBox(page=1, x0=100.0, y0=200.0, x1=400.0, y1=300.0)
        obj = ExtractedObject(
            object_id="eq_1",
            object_type="equation",
            bbox=bbox,
            file_path="/tmp/eq_1.png",
            confidence=0.95
        )
        quality = ExtractionQuality(overall_score=0.93, equations_extracted=1)
        metadata = ExtractionMetadata(
            source_filename="test.pdf",
            page_count=10,
            extraction_quality=quality
        )
        output = ExtractionOutput(
            document_id="test_doc",
            extraction_timestamp=datetime.now().isoformat(),
            objects=[obj],
            metadata=metadata
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "extraction_output.json"
            output.to_json_file(filepath)

            # Validate from file
            assert validate_pipeline_handoff(filepath, target_pipeline='rag')

    def test_rag_to_database_handoff(self):
        """Test RAG→Database handoff from file."""
        # Create and save RAG output
        bundle = RAGBundle(
            bundle_id="bundle:eq1_complete",
            bundle_type="equation",
            entity_id="eq:1",
            content={"latex": "E = mc^2"},
            usage_guidance={},
            semantic_tags=["energy"],
            embedding_metadata={}
        )
        metadata = RAGMetadata(
            source_document_id="test_doc",
            processing_timestamp=datetime.now().isoformat(),
            total_bundles=1,
            bundles_by_type={"equation": 1}
        )
        output = RAGOutput(
            document_id="test_doc",
            bundles=[bundle],
            metadata=metadata
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "rag_output.json"
            output.to_json_file(filepath)

            # Validate from file
            assert validate_pipeline_handoff(filepath, target_pipeline='database')

    def test_invalid_target_pipeline(self):
        """Test invalid target pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            filepath.write_text('{}')

            with pytest.raises(ValueError, match="Unknown target pipeline"):
                validate_pipeline_handoff(filepath, target_pipeline='invalid')

    def test_file_not_found(self):
        """Test file not found."""
        with pytest.raises(FileNotFoundError):
            validate_pipeline_handoff(Path("/nonexistent/file.json"), target_pipeline='rag')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
