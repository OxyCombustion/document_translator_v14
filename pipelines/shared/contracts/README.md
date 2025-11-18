# Pipeline Data Contracts

**Version**: 1.0.0
**Status**: Production Ready
**Architecture**: Multi-AI v14 Pipeline System

---

## 📋 Overview

This directory contains **data contracts** that define interfaces between the three vertical pipelines in v14 architecture. Contracts ensure type safety, validation, and clear separation of concerns between pipelines.

### Why Data Contracts?

- ✅ **Fail Fast**: Invalid data caught at pipeline boundaries
- ✅ **Independent Development**: Pipelines evolve without breaking integrations
- ✅ **Self-Documenting**: Contracts ARE the interface specification
- ✅ **Testable**: Contract validation enables integration testing
- ✅ **Zero Dependencies**: Uses Python @dataclass (stdlib only)

---

## 🏗️ Contract Architecture

```
┌─────────────────┐
│ EXTRACTION      │ Produces:
│ PIPELINE (P1)   │ ────> ExtractionOutput.json
└─────────────────┘
         │
         │ Contract: extraction_output.py
         │ Validates: Objects, bounding boxes, metadata
         ▼
┌─────────────────┐
│ RAG INGESTION   │ Produces:
│ PIPELINE (P2)   │ ────> RAGOutput.jsonl
└─────────────────┘
         │
         │ Contract: rag_output.py
         │ Validates: Bundles, relationships, semantic tags
         ▼
┌─────────────────┐
│ DATA MANAGEMENT │ Ingests:
│ PIPELINE (P3)   │ ────> Vector Database
└─────────────────┘
```

---

## 📁 Files in This Directory

| File | Purpose | Lines |
|------|---------|-------|
| `extraction_output.py` | Extraction → RAG contract | 427 |
| `rag_output.py` | RAG → Database contract | 390 |
| `validation.py` | Validation utilities | 280 |
| `__init__.py` | Package exports | 52 |
| `examples/` | Example contract files | - |
| `README.md` | This documentation | - |

---

## 🎯 Quick Start

### Using Extraction Contract

```python
from pathlib import Path
from pipelines.shared.contracts.extraction_output import (
    ExtractionOutput,
    ExtractedObject,
    BoundingBox,
    ExtractionMetadata,
    ExtractionQuality
)

# Create extraction output
bbox = BoundingBox(page=1, x0=100.0, y0=200.0, x1=400.0, y1=300.0)
obj = ExtractedObject(
    object_id="eq_1",
    object_type="equation",
    bbox=bbox,
    file_path="equations/eq_1.png",
    confidence=0.95
)
quality = ExtractionQuality(overall_score=0.93, equations_extracted=1)
metadata = ExtractionMetadata(
    source_filename="Ch-04_Heat_Transfer.pdf",
    page_count=34,
    extraction_quality=quality
)
output = ExtractionOutput(
    document_id="chapter4_heat_transfer",
    extraction_timestamp="2025-11-18T10:00:00Z",
    objects=[obj],
    metadata=metadata
)

# Validate
output.validate()  # Raises ValueError if invalid

# Save
output.to_json_file(Path("extraction_output.json"))

# Load
loaded = ExtractionOutput.from_json_file(Path("extraction_output.json"))
```

### Using RAG Contract

```python
from pathlib import Path
from pipelines.shared.contracts.rag_output import (
    RAGOutput,
    RAGBundle,
    RAGMetadata
)

# Create RAG bundle
bundle = RAGBundle(
    bundle_id="bundle:eq1_complete",
    bundle_type="equation",
    entity_id="eq:1",
    content={"latex": "E = mc^2", "description": "Mass-energy equivalence"},
    usage_guidance={"when_to_use": "Energy calculations"},
    semantic_tags=["energy", "mass", "relativity"],
    embedding_metadata={"source_page": 1}
)

metadata = RAGMetadata(
    source_document_id="chapter4_heat_transfer",
    processing_timestamp="2025-11-18T11:00:00Z",
    total_bundles=1,
    bundles_by_type={"equation": 1},
    total_relationships=5
)

output = RAGOutput(
    document_id="chapter4_heat_transfer",
    bundles=[bundle],
    metadata=metadata
)

# Validate
output.validate()  # Raises ValueError if invalid

# Save as JSONL (preferred for vector DB ingestion)
output.to_jsonl_file(Path("rag_output.jsonl"))

# Or save as JSON
output.to_json_file(Path("rag_output.json"))

# Load
loaded = RAGOutput.from_jsonl_file(Path("rag_output.jsonl"), document_id="chapter4_heat_transfer")
```

### Using Validation Utilities

```python
from pathlib import Path
from pipelines.shared.contracts.validation import (
    validate_extraction_to_rag_handoff,
    validate_rag_to_database_handoff,
    validate_pipeline_handoff,
    ContractValidationError
)

# Validate extraction→RAG handoff
try:
    extraction_output = ExtractionOutput.from_json_file(Path("extraction_output.json"))
    validate_extraction_to_rag_handoff(extraction_output, min_quality_score=0.5)
    print("✅ Extraction output valid for RAG ingestion")
except ContractValidationError as e:
    print(f"❌ Validation failed: {e}")

# Validate RAG→Database handoff
try:
    rag_output = RAGOutput.from_json_file(Path("rag_output.json"))
    validate_rag_to_database_handoff(rag_output, min_bundles=1)
    print("✅ RAG output valid for database ingestion")
except ContractValidationError as e:
    print(f"❌ Validation failed: {e}")

# Convenience function for file validation
try:
    validate_pipeline_handoff(
        Path("extraction_output.json"),
        target_pipeline='rag',
        min_quality_score=0.5
    )
    print("✅ Pipeline handoff validated")
except ContractValidationError as e:
    print(f"❌ Validation failed: {e}")
```

---

## 📊 Contract Specifications

### ExtractionOutput Contract

**Purpose**: Defines output format from Extraction Pipeline (P1)

**Key Fields**:
- `document_id`: Unique document identifier (alphanumeric + _ -)
- `extraction_timestamp`: ISO 8601 timestamp
- `objects`: List of extracted objects (equations, tables, figures, text)
- `metadata`: Extraction quality metrics and source document info

**Validation Rules**:
- Document ID must be non-empty and alphanumeric
- Timestamp must be valid ISO 8601
- Object counts must match metadata
- Object IDs must match object types (eq_1 for equations, tbl_1 for tables, etc.)
- Bounding boxes must have valid coordinates (x1 > x0, y1 > y0)
- Confidence scores must be in [0.0, 1.0]

**Example**:
```json
{
  "document_id": "chapter4_heat_transfer",
  "extraction_timestamp": "2025-11-18T10:00:00Z",
  "objects": [
    {
      "object_id": "eq_1",
      "object_type": "equation",
      "bbox": {"page": 1, "x0": 100.0, "y0": 200.0, "x1": 400.0, "y1": 300.0},
      "file_path": "equations/eq_1.png",
      "confidence": 0.95,
      "metadata": {}
    }
  ],
  "metadata": {
    "source_filename": "Ch-04_Heat_Transfer.pdf",
    "page_count": 34,
    "extraction_quality": {
      "overall_score": 0.93,
      "equations_extracted": 108,
      "tables_extracted": 13,
      "figures_extracted": 47,
      "text_blocks_extracted": 250
    },
    "pipeline_version": "14.0.0"
  }
}
```

---

### RAGOutput Contract

**Purpose**: Defines output format from RAG Ingestion Pipeline (P2)

**Key Fields**:
- `document_id`: Unique document identifier (matches ExtractionOutput)
- `bundles`: List of RAG micro-bundles (self-contained embedding units)
- `metadata`: Bundle statistics, relationship counts, chunking info
- `knowledge_graph`: Optional graph data

**Validation Rules**:
- Document ID must match metadata.source_document_id
- Bundle counts must match metadata
- Bundle IDs must start with "bundle:"
- Entity IDs must have valid prefixes (eq:, tbl:, var:, etc.)
- Bundle types must be valid (equation, table, concept, figure, text)
- Content cannot be empty
- Semantic tags should be present (warning if missing)

**Example**:
```json
{
  "document_id": "chapter4_heat_transfer",
  "bundles": [
    {
      "bundle_id": "bundle:eq1_complete",
      "bundle_type": "equation",
      "entity_id": "eq:1",
      "content": {
        "latex": "q_c = -kA \\frac{dT}{dx}",
        "description": "Fourier's law of heat conduction"
      },
      "usage_guidance": {
        "when_to_use": "Calculate conductive heat transfer rate",
        "variables": {"q_c": "heat transfer rate", "k": "thermal conductivity"}
      },
      "semantic_tags": ["heat transfer", "conduction", "Fourier's law"],
      "embedding_metadata": {"source_page": 4, "section": "Conduction"},
      "relationships": []
    }
  ],
  "metadata": {
    "source_document_id": "chapter4_heat_transfer",
    "processing_timestamp": "2025-11-18T11:00:00Z",
    "total_bundles": 1,
    "bundles_by_type": {"equation": 1},
    "total_relationships": 5,
    "semantic_chunks_created": 34,
    "citations_extracted": 386,
    "average_bundle_tokens": 425.3
  }
}
```

---

## 🧪 Testing

Comprehensive test suite included in `tests/contracts/`:

```bash
# Run all contract tests
pytest tests/contracts/ -v

# Run specific test file
pytest tests/contracts/test_extraction_output.py -v
pytest tests/contracts/test_rag_output.py -v
pytest tests/contracts/test_validation.py -v

# Run with coverage
pytest tests/contracts/ --cov=pipelines.shared.contracts --cov-report=html
```

**Test Coverage**:
- BoundingBox validation (valid/invalid coordinates)
- ExtractedObject validation (ID formats, types, confidence)
- ExtractionQuality metrics validation
- ExtractionOutput validation (count matching, serialization)
- RAGBundle validation (IDs, types, content)
- RAGOutput validation (bundle counts, metadata)
- Round-trip serialization (JSON and JSONL)
- Pipeline handoff validation
- Contract validation errors

---

## 🔧 Integration with Pipelines

### Extraction Pipeline (P1)

**At the end of extraction processing**:

```python
from pipelines.shared.contracts.extraction_output import ExtractionOutput

# Build ExtractionOutput from pipeline results
output = ExtractionOutput(
    document_id=doc_id,
    extraction_timestamp=datetime.now().isoformat(),
    objects=extracted_objects,
    metadata=extraction_metadata
)

# Validate before saving
try:
    output.validate()
    output.validate_completeness()
except ValueError as e:
    logger.error(f"Extraction output validation failed: {e}")
    raise

# Save
output.to_json_file(output_dir / "extraction_output.json")
logger.info(f"✅ Extraction complete: {output.summary()}")
```

### RAG Ingestion Pipeline (P2)

**At the start of RAG processing**:

```python
from pipelines.shared.contracts.extraction_output import ExtractionOutput
from pipelines.shared.contracts.validation import validate_extraction_to_rag_handoff

# Load and validate extraction output
extraction_output = ExtractionOutput.from_json_file(input_path / "extraction_output.json")

# Validate for RAG ingestion
try:
    validate_extraction_to_rag_handoff(extraction_output, min_quality_score=0.5)
except ContractValidationError as e:
    logger.error(f"Extraction output not suitable for RAG: {e}")
    raise

# Process...
```

**At the end of RAG processing**:

```python
from pipelines.shared.contracts.rag_output import RAGOutput

# Build RAGOutput from pipeline results
output = RAGOutput(
    document_id=doc_id,
    bundles=rag_bundles,
    metadata=rag_metadata,
    knowledge_graph=graph_data
)

# Validate before saving
try:
    output.validate()
    output.validate_completeness()
except ValueError as e:
    logger.error(f"RAG output validation failed: {e}")
    raise

# Save (JSONL preferred for vector DB)
output.to_jsonl_file(output_dir / "rag_output.jsonl")
logger.info(f"✅ RAG processing complete: {output.summary()}")
```

### Database Management Pipeline (P3)

**At the start of database ingestion**:

```python
from pipelines.shared.contracts.rag_output import RAGOutput
from pipelines.shared.contracts.validation import validate_rag_to_database_handoff

# Load and validate RAG output
rag_output = RAGOutput.from_jsonl_file(
    input_path / "rag_output.jsonl",
    document_id=doc_id
)

# Validate for database ingestion
try:
    validate_rag_to_database_handoff(rag_output, min_bundles=1)
except ContractValidationError as e:
    logger.error(f"RAG output not suitable for database: {e}")
    raise

# Ingest bundles...
for bundle in rag_output.bundles:
    vector_db.add_bundle(bundle)
```

---

## 🎓 Best Practices

### 1. **Always Validate**

```python
# ✅ Good
output.validate()  # Explicit validation
output.to_json_file(path, validate=True)  # Validate before save

# ❌ Bad
output.to_json_file(path, validate=False)  # Skipping validation
```

### 2. **Use Specific Exceptions**

```python
# ✅ Good
try:
    validate_extraction_to_rag_handoff(output)
except ContractValidationError as e:
    logger.error(f"Contract validation failed: {e}")
    # Handle contract-specific failure
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Handle other failures

# ❌ Bad
try:
    validate_extraction_to_rag_handoff(output)
except Exception as e:
    # Too broad - can't distinguish contract failures
    pass
```

### 3. **Log Validation Results**

```python
# ✅ Good
try:
    output.validate()
    logger.info(f"✅ Validation passed: {output.summary()}")
except ValueError as e:
    logger.error(f"❌ Validation failed: {e}")
    raise

# ❌ Bad
output.validate()  # Silent - hard to debug
```

### 4. **Check Completeness**

```python
# ✅ Good
output.validate()  # Structure is correct
output.validate_completeness()  # Content is sufficient

# ⚠️ Adequate but not ideal
output.validate()  # Only structure, not content quality
```

### 5. **Use Type Hints**

```python
# ✅ Good
from pipelines.shared.contracts.extraction_output import ExtractionOutput

def process_extraction(output: ExtractionOutput) -> bool:
    output.validate()
    # IDE autocomplete works, type checking catches errors
    return True

# ❌ Bad
def process_extraction(output):  # No type hints
    output.validate()  # IDE can't help, no type safety
    return True
```

---

## 📚 Additional Resources

- **Architecture**: `/home/thermodynamics/document_translator_v14/V14_VERTICAL_PIPELINE_ARCHITECTURE_REVIEW.md`
- **Multi-AI Plan**: `/home/thermodynamics/document_translator_v14/V14_MULTI_AI_CONTEXT_REDUCTION_PLAN.md`
- **Orchestrator Context**: `/home/thermodynamics/document_translator_v14/ORCHESTRATOR.md`
- **Example Files**: `pipelines/shared/contracts/examples/`
- **Tests**: `tests/contracts/`

---

## 🚀 Future Enhancements (Optional)

### Phase B: Pydantic Migration

If additional validation features are needed, contracts can be migrated to Pydantic:

**Benefits**:
- Automatic JSON schema generation
- More detailed error messages
- Better IDE support
- Field validators and custom validation logic

**Migration Path**:
1. Add `pydantic` to `requirements.txt`
2. Replace `@dataclass` with `BaseModel`
3. Use Field() for constraints
4. Add custom validators
5. Update tests

---

**Version**: 1.0.0
**Last Updated**: 2025-11-18
**Authors**: Multi-AI Architecture Team
