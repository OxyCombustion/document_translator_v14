# -*- coding: utf-8 -*-
"""
Tests for ExtractionOutput Contract

Tests validation, serialization, and round-trip conversion.
"""

import pytest
import json
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


class TestBoundingBox:
    """Tests for BoundingBox dataclass."""

    def test_valid_bounding_box(self):
        """Test valid bounding box creation."""
        bbox = BoundingBox(page=1, x0=100.0, y0=200.0, x1=400.0, y1=300.0)
        assert bbox.validate()
        assert bbox.area() == (400.0 - 100.0) * (300.0 - 200.0)

    def test_invalid_page_number(self):
        """Test invalid page number (< 1)."""
        bbox = BoundingBox(page=0, x0=100.0, y0=200.0, x1=400.0, y1=300.0)
        with pytest.raises(ValueError, match="Page number must be >= 1"):
            bbox.validate()

    def test_invalid_x_coordinates(self):
        """Test invalid X coordinates (x1 <= x0)."""
        bbox = BoundingBox(page=1, x0=400.0, y0=200.0, x1=100.0, y1=300.0)
        with pytest.raises(ValueError, match="x1.*must be > x0"):
            bbox.validate()

    def test_invalid_y_coordinates(self):
        """Test invalid Y coordinates (y1 <= y0)."""
        bbox = BoundingBox(page=1, x0=100.0, y0=300.0, x1=400.0, y1=200.0)
        with pytest.raises(ValueError, match="y1.*must be > y0"):
            bbox.validate()


class TestExtractedObject:
    """Tests for ExtractedObject dataclass."""

    def test_valid_equation_object(self):
        """Test valid equation object."""
        bbox = BoundingBox(page=1, x0=100.0, y0=200.0, x1=400.0, y1=300.0)
        obj = ExtractedObject(
            object_id="eq_1",
            object_type="equation",
            bbox=bbox,
            file_path="/tmp/eq_1.png",
            confidence=0.95
        )
        assert obj.validate()

    def test_valid_table_object(self):
        """Test valid table object."""
        bbox = BoundingBox(page=2, x0=100.0, y0=200.0, x1=400.0, y1=300.0)
        obj = ExtractedObject(
            object_id="tbl_3",
            object_type="table",
            bbox=bbox,
            file_path="/tmp/tbl_3.csv",
            confidence=0.88
        )
        assert obj.validate()

    def test_invalid_object_id_prefix(self):
        """Test invalid object_id prefix."""
        bbox = BoundingBox(page=1, x0=100.0, y0=200.0, x1=400.0, y1=300.0)
        obj = ExtractedObject(
            object_id="invalid_1",
            object_type="equation",
            bbox=bbox,
            file_path="/tmp/test.png",
            confidence=0.95
        )
        with pytest.raises(ValueError, match="object_id must start with"):
            obj.validate()

    def test_invalid_object_type(self):
        """Test invalid object_type."""
        bbox = BoundingBox(page=1, x0=100.0, y0=200.0, x1=400.0, y1=300.0)
        obj = ExtractedObject(
            object_id="eq_1",
            object_type="invalid_type",
            bbox=bbox,
            file_path="/tmp/test.png",
            confidence=0.95
        )
        with pytest.raises(ValueError, match="object_type must be one of"):
            obj.validate()

    def test_mismatched_id_and_type(self):
        """Test object_id prefix doesn't match object_type."""
        bbox = BoundingBox(page=1, x0=100.0, y0=200.0, x1=400.0, y1=300.0)
        obj = ExtractedObject(
            object_id="tbl_1",  # table prefix
            object_type="equation",  # but equation type
            bbox=bbox,
            file_path="/tmp/test.png",
            confidence=0.95
        )
        with pytest.raises(ValueError, match="object_id.*must start with 'eq_'"):
            obj.validate()

    def test_invalid_confidence(self):
        """Test invalid confidence score."""
        bbox = BoundingBox(page=1, x0=100.0, y0=200.0, x1=400.0, y1=300.0)
        obj = ExtractedObject(
            object_id="eq_1",
            object_type="equation",
            bbox=bbox,
            file_path="/tmp/test.png",
            confidence=1.5  # > 1.0
        )
        with pytest.raises(ValueError, match="confidence must be in"):
            obj.validate()


class TestExtractionQuality:
    """Tests for ExtractionQuality dataclass."""

    def test_valid_quality(self):
        """Test valid quality metrics."""
        quality = ExtractionQuality(
            overall_score=0.93,
            equations_extracted=108,
            tables_extracted=13,
            figures_extracted=47,
            text_blocks_extracted=250
        )
        assert quality.validate()
        assert quality.total_objects() == 108 + 13 + 47 + 250

    def test_invalid_overall_score(self):
        """Test invalid overall_score."""
        quality = ExtractionQuality(overall_score=1.5)
        with pytest.raises(ValueError, match="overall_score must be in"):
            quality.validate()

    def test_negative_counts(self):
        """Test negative extraction counts."""
        quality = ExtractionQuality(overall_score=0.9, equations_extracted=-5)
        with pytest.raises(ValueError, match="equations_extracted must be >= 0"):
            quality.validate()


class TestExtractionMetadata:
    """Tests for ExtractionMetadata dataclass."""

    def test_valid_metadata(self):
        """Test valid metadata."""
        quality = ExtractionQuality(overall_score=0.93, equations_extracted=108)
        metadata = ExtractionMetadata(
            source_filename="Ch-04_Heat_Transfer.pdf",
            page_count=34,
            extraction_quality=quality,
            file_hash="abc123def456",
            doi="10.1234/example.doi"
        )
        assert metadata.validate()

    def test_invalid_page_count(self):
        """Test invalid page_count."""
        quality = ExtractionQuality(overall_score=0.93)
        metadata = ExtractionMetadata(
            source_filename="test.pdf",
            page_count=0,  # Invalid
            extraction_quality=quality
        )
        with pytest.raises(ValueError, match="page_count must be >= 1"):
            metadata.validate()


class TestExtractionOutput:
    """Tests for ExtractionOutput dataclass."""

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
            equations_extracted=1,
            tables_extracted=0,
            figures_extracted=0,
            text_blocks_extracted=0
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

    def test_valid_extraction_output(self):
        """Test valid extraction output."""
        output = self.create_valid_extraction_output()
        assert output.validate()

    def test_empty_document_id(self):
        """Test empty document_id."""
        output = self.create_valid_extraction_output()
        output.document_id = ""
        with pytest.raises(ValueError, match="document_id cannot be empty"):
            output.validate()

    def test_invalid_document_id_format(self):
        """Test invalid document_id format."""
        output = self.create_valid_extraction_output()
        output.document_id = "invalid doc!"  # Contains space and special char
        with pytest.raises(ValueError, match="document_id must be alphanumeric"):
            output.validate()

    def test_invalid_timestamp(self):
        """Test invalid timestamp format."""
        output = self.create_valid_extraction_output()
        output.extraction_timestamp = "invalid-timestamp"
        with pytest.raises(ValueError, match="extraction_timestamp must be valid ISO 8601"):
            output.validate()

    def test_object_count_mismatch(self):
        """Test mismatch between objects list and metadata counts."""
        output = self.create_valid_extraction_output()
        # Metadata says 1 equation, but we add a table
        bbox = BoundingBox(page=1, x0=100.0, y0=200.0, x1=400.0, y1=300.0)
        table_obj = ExtractedObject(
            object_id="tbl_1",
            object_type="table",
            bbox=bbox,
            file_path="/tmp/tbl_1.csv",
            confidence=0.88
        )
        output.objects.append(table_obj)
        with pytest.raises(ValueError, match="Table count mismatch"):
            output.validate()

    def test_validate_completeness_empty(self):
        """Test completeness validation with no objects."""
        output = self.create_valid_extraction_output()
        output.objects = []
        output.metadata.extraction_quality.equations_extracted = 0
        with pytest.raises(ValueError, match="No objects extracted"):
            output.validate_completeness()

    def test_to_dict_conversion(self):
        """Test conversion to dictionary."""
        output = self.create_valid_extraction_output()
        data = output.to_dict()
        assert isinstance(data, dict)
        assert data['document_id'] == "test_doc"
        assert len(data['objects']) == 1
        assert data['objects'][0]['object_id'] == "eq_1"

    def test_round_trip_serialization(self):
        """Test save and load round-trip."""
        output = self.create_valid_extraction_output()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "extraction_output.json"

            # Save
            output.to_json_file(filepath)
            assert filepath.exists()

            # Load
            loaded_output = ExtractionOutput.from_json_file(filepath)

            # Verify
            assert loaded_output.document_id == output.document_id
            assert len(loaded_output.objects) == len(output.objects)
            assert loaded_output.objects[0].object_id == output.objects[0].object_id
            assert loaded_output.metadata.page_count == output.metadata.page_count

    def test_summary_generation(self):
        """Test summary generation."""
        output = self.create_valid_extraction_output()
        summary = output.summary()
        assert summary['document_id'] == "test_doc"
        assert summary['total_objects'] == 1
        assert summary['objects_by_type']['equations'] == 1
        assert summary['quality_score'] == 0.93


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
