# Three-Pipeline Architecture Migration Plan

**Document Version**: 1.0
**Date**: 2025-11-14
**Author**: Web Claude Code (Anthropic)
**For Review By**: Local Claude Code
**Project**: Document Translator v13 Architecture Refactoring

---

## 🎯 Executive Summary

**Vision**: Split the monolithic document translator v13 system into three vertically-separated pipelines with clear interface boundaries to reduce context complexity for AI development agents and enable parallel development.

**Strategic Rationale**: By reducing context from ~1,500 lines (single CLAUDE.md) to ~500 lines per pipeline, we enable AI agents like Claude Code to work more efficiently on focused tasks without needing to understand the entire system.

**Expected Benefits**:
- 🧠 **Context Reduction**: 3x smaller context per development session
- 🚀 **Development Velocity**: Parallel development on independent pipelines
- 🔒 **Isolation**: Changes in one pipeline don't break others
- 🧪 **Testing**: Pipeline-specific tests without end-to-end dependencies
- 📚 **Maintainability**: Clear ownership and documentation boundaries

**Timeline**: 4-5 weeks for complete migration
**Risk Level**: MEDIUM (interface contracts are critical success factor)

---

## 📐 Current vs Proposed Architecture

### Current Architecture (Monolithic)

```
┌───────────────────────────────────────────────────────────┐
│ Document Translator v13 (Single Monolith)                │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │ Extraction  │ → │ Relationship │ → │  Curation    │  │
│  │  Agents     │   │  Detection   │   │  & Quality   │  │
│  └─────────────┘   └──────────────┘   └──────────────┘  │
│                                                           │
│  All components share:                                   │
│  - Single CLAUDE.md (~1,500 lines)                       │
│  - Tightly coupled imports                               │
│  - Shared configuration                                  │
│  - End-to-end testing only                               │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

**Problems**:
- ❌ AI agents must load full 1,500-line context for small changes
- ❌ Changes to extraction can accidentally break RAG or curation
- ❌ Cannot work on pipelines in parallel
- ❌ Testing requires full system setup

---

### Proposed Architecture (Three Vertical Pipelines)

```
┌─────────────────────────────────────────────────────────────────┐
│ Pipeline 1: EXTRACTION                                          │
├─────────────────────────────────────────────────────────────────┤
│ Context: extraction_CLAUDE.md (~500 lines)                      │
│ Input:  PDF documents                                           │
│ Output: extraction_results.json (INTERFACE v1.0)                │
│ Scope:  Object detection, extraction, image processing          │
│ Tests:  tests/pipeline1/ (no Pipeline 2/3 dependencies)         │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (JSON interface)
┌─────────────────────────────────────────────────────────────────┐
│ Pipeline 2: RAG PREPARATION                                     │
├─────────────────────────────────────────────────────────────────┤
│ Context: rag_CLAUDE.md (~500 lines)                             │
│ Input:  extraction_results.json                                 │
│ Output: rag_bundles.jsonl, knowledge_graph.json (INTERFACE v1.0)│
│ Scope:  Relationships, embeddings, semantic bundling            │
│ Tests:  tests/pipeline2/ (mock extraction input)                │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (JSONL + JSON interfaces)
┌─────────────────────────────────────────────────────────────────┐
│ Pipeline 3: CURATION & QUALITY                                  │
├─────────────────────────────────────────────────────────────────┤
│ Context: curation_CLAUDE.md (~500 lines)                        │
│ Input:  rag_bundles.jsonl, knowledge_graph.json                 │
│ Output: model_metadata_*.db, curated_indices.json               │
│ Scope:  Novelty detection, multi-model evaluation, tracking     │
│ Tests:  tests/pipeline3/ (mock RAG input)                       │
└─────────────────────────────────────────────────────────────────┘
```

**Benefits**:
- ✅ AI agents load only 500 lines of relevant context
- ✅ Strict JSON interfaces prevent accidental breakage
- ✅ Parallel development on all three pipelines
- ✅ Pipeline-specific testing with mocked inputs

---

## 🏗️ Detailed Pipeline Specifications

### Pipeline 1: Extraction

**Purpose**: Extract structured objects from PDF documents

**Input**:
- PDF documents: `data/{document_name}.pdf`

**Output**:
- `results/extraction/{document_id}/extraction_results.json` (v1.0 schema)
- Extracted images: `results/extraction/{document_id}/{type}/`
  - `equations/` - PNG images of equations
  - `tables/` - PNG images of tables
  - `figures/` - PNG images of figures

**Components** (to be moved/refactored):
```
pipeline1_extraction/
├── CLAUDE.md (extraction-specific context)
├── src/
│   ├── agents/
│   │   ├── detection/
│   │   │   ├── unified_detection_module.py
│   │   │   ├── docling_table_detector.py
│   │   │   └── figure_intelligence_analyzer.py
│   │   └── extraction/
│   │       ├── equation_extraction_agent.py
│   │       ├── table_extraction_agent.py
│   │       └── figure_extraction_agent.py
│   └── core/
│       └── extraction_registry.py
├── tests/
│   ├── test_detection.py
│   ├── test_extraction.py
│   └── test_extraction_output_schema.py
└── config/
    └── extraction_config.yaml
```

**Dependencies**:
- PyMuPDF (PDF processing)
- Docling (table detection)
- DocLayout-YOLO (object detection)
- OpenCV (image processing)
- **NO dependencies on Pipeline 2 or 3**

**Key Responsibilities**:
1. Detect objects in PDFs (equations, tables, figures, text)
2. Extract objects with high-quality images
3. Generate standardized JSON output
4. Track extraction history in extraction_registry.json

---

### Pipeline 2: RAG Preparation

**Purpose**: Build relationships, generate embeddings, create RAG-ready bundles

**Input**:
- `results/extraction/{document_id}/extraction_results.json`

**Output**:
- `results/rag/{document_id}/rag_bundles.jsonl` (one bundle per line)
- `results/rag/{document_id}/knowledge_graph.json`
- `results/rag/{document_id}/bundle_statistics.json`

**Components** (to be moved/refactored):
```
pipeline2_rag/
├── CLAUDE.md (RAG-specific context)
├── src/
│   ├── core/
│   │   ├── semantic_registry.py
│   │   └── reference_resolver.py
│   ├── detectors/
│   │   ├── variable_definition_detector.py
│   │   ├── data_dependency_detector.py
│   │   ├── cross_reference_detector.py
│   │   └── citation_detector.py
│   ├── validators/
│   │   └── relationship_validator.py
│   └── exporters/
│       ├── rag_micro_bundle_generator.py
│       ├── context_enhancer.py
│       └── knowledge_graph_builder.py
├── tests/
│   ├── test_relationship_detection.py
│   ├── test_bundle_generation.py
│   └── test_rag_output_schema.py
└── config/
    ├── relationship_extraction/
    └── rag/
```

**Dependencies**:
- sentence-transformers (for embeddings)
- NetworkX (for knowledge graph)
- spaCy or similar (for NLP)
- **NO dependencies on Pipeline 1 or 3**

**Key Responsibilities**:
1. Detect relationships between extracted objects
2. Validate dimensional consistency
3. Generate embeddings for semantic search
4. Build knowledge graph with typed edges
5. Create self-contained RAG bundles

---

### Pipeline 3: Curation & Quality

**Purpose**: Evaluate novelty, track quality, curate for specific AI models

**Input**:
- `results/rag/{document_id}/rag_bundles.jsonl`
- `results/rag/{document_id}/knowledge_graph.json`

**Output**:
- `results/curation/model_metadata_{model_id}.db` (SQLite)
- `results/curation/curated_indices.json`
- `results/curation/quality_metrics.json`

**Components** (to be moved/refactored):
```
pipeline3_curation/
├── CLAUDE.md (curation-specific context)
├── src/
│   ├── core/
│   │   ├── novelty_metadata_database.py
│   │   ├── local_llm_novelty_classifier.py
│   │   ├── llm_confidence_calibrator.py
│   │   └── domain_specificity_validator.py
│   ├── validators/
│   │   └── novelty_validation.py
│   └── exporters/
│       └── curated_index_builder.py
├── tests/
│   ├── test_novelty_classification.py
│   ├── test_calibration.py
│   └── test_curation_output_schema.py
└── config/
    └── curation_config.yaml
```

**Dependencies**:
- transformers (for local LLM - Qwen 2.5 3B)
- SQLite (for metadata storage)
- PyTorch (for LLM inference)
- **NO dependencies on Pipeline 1 or 2**

**Key Responsibilities**:
1. Classify novelty of content for specific models
2. Calibrate LLM confidence scores
3. Track quality metrics across models
4. Generate curated indices for model-specific RAG
5. Manage metadata staleness and expiration

---

## 📋 Interface Specifications

### Interface 1: extraction_results.json (Pipeline 1 → 2)

**Schema Version**: 1.0
**File Format**: JSON
**Location**: `results/extraction/{document_id}/extraction_results.json`

**Complete Schema**:
```json
{
  "schema_version": "1.0",
  "document_metadata": {
    "document_id": "ch04_heat_transfer",
    "source_pdf": "data/Ch-04_Heat_Transfer.pdf",
    "source_pdf_hash": "sha256:abc123...",
    "extraction_timestamp": "2025-11-14T10:00:00Z",
    "extractor_version": "v13.1.0",
    "total_pages": 34
  },
  "extracted_objects": {
    "equations": [
      {
        "id": "eq:1",
        "type": "equation",
        "content": "q = -kA dT/dx",
        "latex": "q = -kA \\frac{dT}{dx}",
        "page": 1,
        "bbox": {
          "x": 120,
          "y": 450,
          "width": 300,
          "height": 40
        },
        "image_path": "results/extraction/ch04_heat_transfer/equations/eq_001.png",
        "confidence": 0.95,
        "detection_method": "doclayout_yolo"
      }
    ],
    "tables": [
      {
        "id": "tbl:1",
        "type": "table",
        "title": "Thermal Conductivity of Materials",
        "page": 5,
        "bbox": {
          "x": 80,
          "y": 200,
          "width": 450,
          "height": 300
        },
        "image_path": "results/extraction/ch04_heat_transfer/tables/tbl_001.png",
        "data_path": "results/extraction/ch04_heat_transfer/tables/tbl_001.xlsx",
        "rows": 15,
        "columns": 4,
        "confidence": 0.88,
        "detection_method": "docling"
      }
    ],
    "figures": [
      {
        "id": "fig:1",
        "type": "figure",
        "caption": "Heat transfer through a plane wall",
        "page": 3,
        "bbox": {
          "x": 100,
          "y": 250,
          "width": 400,
          "height": 350
        },
        "image_path": "results/extraction/ch04_heat_transfer/figures/fig_001.png",
        "confidence": 0.92,
        "detection_method": "doclayout_yolo"
      }
    ],
    "text_chunks": [
      {
        "id": "txt:1",
        "type": "text",
        "content": "Fourier's law of heat conduction states that...",
        "page": 1,
        "bbox": {
          "x": 80,
          "y": 100,
          "width": 450,
          "height": 200
        },
        "word_count": 156,
        "char_count": 782
      }
    ]
  },
  "extraction_statistics": {
    "total_objects": 165,
    "equations": 108,
    "tables": 13,
    "figures": 44,
    "text_chunks": 250,
    "processing_time_seconds": 42.8,
    "success_rate": 0.982
  }
}
```

**Validation Rules**:
- ✅ `schema_version` must be "1.0"
- ✅ All `id` fields must be unique within type
- ✅ All `bbox` coordinates must be positive
- ✅ All `image_path` files must exist
- ✅ All `confidence` scores must be 0.0-1.0
- ✅ `source_pdf_hash` must match actual PDF hash

**Breaking Changes Policy**:
- Adding new fields: MINOR version bump (1.0 → 1.1) - backward compatible
- Renaming/removing fields: MAJOR version bump (1.0 → 2.0) - breaking change
- Pipeline 2 must support 1.x versions with graceful degradation

---

### Interface 2: rag_bundles.jsonl (Pipeline 2 → 3)

**Schema Version**: 1.0
**File Format**: JSON Lines (one object per line)
**Location**: `results/rag/{document_id}/rag_bundles.jsonl`

**Bundle Schema** (per line):
```json
{
  "bundle_id": "eq:1_bundle",
  "bundle_type": "equation",
  "schema_version": "1.0",
  "created_timestamp": "2025-11-14T10:05:00Z",
  "source_object": {
    "id": "eq:1",
    "type": "equation",
    "content": "q = -kA dT/dx",
    "latex": "q = -kA \\frac{dT}{dx}",
    "page": 1
  },
  "relationships": [
    {
      "relationship_id": "vardef:1",
      "type": "DEFINES_VARIABLE",
      "target_id": "var:q",
      "metadata": {
        "variable": "q",
        "definition": "heat flux (W/m²)"
      }
    }
  ],
  "embeddings": {
    "model": "all-MiniLM-L6-v2",
    "vector": [0.123, -0.456, 0.789, ...],  // 384 dimensions
    "vector_hash": "sha256:def456..."
  },
  "context_enhancement": {
    "usage_guidance": "This is Fourier's law for one-dimensional heat conduction...",
    "semantic_tags": ["heat_transfer", "conduction", "fouriers_law"],
    "related_bundles": ["tbl:3_bundle", "fig:1_bundle"]
  },
  "metadata": {
    "token_count": 42,
    "char_count": 156,
    "quality_score": 0.95
  }
}
```

**Validation Rules**:
- ✅ Each line must be valid JSON
- ✅ `bundle_id` must be unique across file
- ✅ `embeddings.vector` must have correct dimensions
- ✅ All `target_id` references must exist in knowledge graph
- ✅ `bundle_type` must be one of: equation, table, figure, concept

---

### Interface 3: knowledge_graph.json (Pipeline 2 → 3)

**Schema Version**: 1.0
**File Format**: JSON
**Location**: `results/rag/{document_id}/knowledge_graph.json`

**Graph Schema**:
```json
{
  "schema_version": "1.0",
  "document_id": "ch04_heat_transfer",
  "created_timestamp": "2025-11-14T10:05:00Z",
  "nodes": [
    {
      "id": "eq:1",
      "type": "equation",
      "label": "Fourier's Law",
      "page": 1,
      "metadata": {
        "content": "q = -kA dT/dx",
        "latex": "q = -kA \\frac{dT}{dx}"
      }
    },
    {
      "id": "var:q",
      "type": "variable",
      "label": "heat flux (q)",
      "metadata": {
        "symbol": "q",
        "name": "heat flux",
        "units": "W/m²",
        "dimension": "ML/T³"
      }
    },
    {
      "id": "tbl:3",
      "type": "table",
      "label": "Emissivity Values",
      "page": 8,
      "metadata": {
        "rows": 20,
        "columns": 3
      }
    }
  ],
  "edges": [
    {
      "id": "rel:1",
      "source": "eq:1",
      "target": "var:q",
      "type": "DEFINES_VARIABLE",
      "confidence": 0.98,
      "metadata": {
        "role": "output",
        "equation_position": "left_hand_side"
      }
    },
    {
      "id": "rel:2",
      "source": "eq:9",
      "target": "tbl:3",
      "type": "REQUIRES_DATA_FROM",
      "confidence": 0.95,
      "metadata": {
        "variable": "epsilon",
        "lookup_method": "select_by_material"
      }
    }
  ],
  "statistics": {
    "total_nodes": 250,
    "total_edges": 297,
    "node_types": {
      "equation": 108,
      "table": 13,
      "figure": 44,
      "variable": 78,
      "reference": 7
    },
    "edge_types": {
      "DEFINES_VARIABLE": 156,
      "REQUIRES_DATA_FROM": 45,
      "REFERENCES": 89,
      "CITES": 7
    }
  }
}
```

**Validation Rules**:
- ✅ All `edges.source` must reference existing `nodes.id`
- ✅ All `edges.target` must reference existing `nodes.id`
- ✅ No self-loops (source ≠ target)
- ✅ No duplicate edges (same source, target, type)
- ✅ Edge types must be from defined set

---

## 📋 Shared Infrastructure

### Common Library Structure

**Purpose**: Shared utilities used by all three pipelines

**Location**: `common/`

**Components**:
```
common/
├── __init__.py
├── pdf_utils.py          # PDF reading, hashing
├── config_loader.py      # YAML configuration loading
├── logging_setup.py      # Structured logging
├── file_utils.py         # Path handling, file operations
├── hash_utils.py         # SHA256 hashing for content
├── validation_utils.py   # Schema validation helpers
└── exceptions.py         # Shared exception types
```

**Versioning**: Common library has independent semantic versioning

**Example Usage**:
```python
# In Pipeline 1
from common.pdf_utils import compute_pdf_hash
from common.config_loader import load_config

# In Pipeline 2
from common.logging_setup import setup_logger
from common.validation_utils import validate_json_schema

# In Pipeline 3
from common.hash_utils import compute_content_hash
from common.exceptions import ValidationError
```

**Critical Rule**: Common library must have NO dependencies on pipeline-specific code

---

## 🗓️ Migration Plan (4-5 Weeks)

### Week 1: Foundation & Interface Definition

**Goal**: Define all interfaces and create validation infrastructure

**Tasks**:

#### Day 1-2: Interface Schema Definition
- [ ] **Task 1.1**: Create `schemas/` directory
- [ ] **Task 1.2**: Write `extraction_results_v1.json` JSON Schema
- [ ] **Task 1.3**: Write `rag_bundles_v1.json` JSON Schema
- [ ] **Task 1.4**: Write `knowledge_graph_v1.json` JSON Schema
- [ ] **Task 1.5**: Document versioning policy in `INTERFACE_VERSIONING.md`

**Deliverables**:
```
schemas/
├── extraction_results_v1.json
├── rag_bundles_v1.json
├── knowledge_graph_v1.json
└── README.md (versioning policy)
```

#### Day 3-4: Validation Infrastructure
- [ ] **Task 1.6**: Create `validate_interfaces.py` script
- [ ] **Task 1.7**: Implement Pydantic models for each schema
- [ ] **Task 1.8**: Write validation tests (`test_schema_validation.py`)
- [ ] **Task 1.9**: Create mock data generators for testing

**Deliverables**:
```
common/
├── schemas.py (Pydantic models)
└── validation_utils.py (validation functions)

tests/
└── test_interface_validation.py
```

#### Day 5: Shared Library Setup
- [ ] **Task 1.10**: Create `common/` directory structure
- [ ] **Task 1.11**: Move shared utilities to `common/`
- [ ] **Task 1.12**: Add `pyproject.toml` for common library
- [ ] **Task 1.13**: Write tests for common utilities

**Deliverables**:
```
common/
├── __init__.py
├── pdf_utils.py
├── config_loader.py
├── logging_setup.py
└── pyproject.toml

tests/common/
└── test_common_utils.py
```

---

### Week 2: Pipeline 1 (Extraction) Migration

**Goal**: Isolate extraction components into Pipeline 1

**Tasks**:

#### Day 1: Directory Restructuring
- [ ] **Task 2.1**: Create `pipeline1_extraction/` directory
- [ ] **Task 2.2**: Move detection agents to `pipeline1_extraction/src/agents/detection/`
- [ ] **Task 2.3**: Move extraction agents to `pipeline1_extraction/src/agents/extraction/`
- [ ] **Task 2.4**: Move extraction tests to `pipeline1_extraction/tests/`

**Deliverables**:
```
pipeline1_extraction/
├── src/
│   └── agents/
│       ├── detection/
│       └── extraction/
└── tests/
```

#### Day 2-3: Output Standardization
- [ ] **Task 2.5**: Create `ExtractionResultsBuilder` class
- [ ] **Task 2.6**: Update all extraction agents to use builder
- [ ] **Task 2.7**: Add schema validation to output generation
- [ ] **Task 2.8**: Test output format against schema

**Deliverables**:
```python
# pipeline1_extraction/src/output_builder.py
class ExtractionResultsBuilder:
    """Build standardized extraction_results.json output."""

    def add_equation(self, eq_data: dict) -> None: ...
    def add_table(self, tbl_data: dict) -> None: ...
    def add_figure(self, fig_data: dict) -> None: ...
    def build(self) -> dict: ...
    def validate(self) -> bool: ...
    def save(self, output_path: str) -> None: ...
```

#### Day 4: Pipeline 1 CLAUDE.md
- [ ] **Task 2.9**: Create `pipeline1_extraction/CLAUDE.md`
- [ ] **Task 2.10**: Extract extraction-specific content from main CLAUDE.md
- [ ] **Task 2.11**: Document input/output contracts
- [ ] **Task 2.12**: Add troubleshooting guide

**Deliverables**:
```
pipeline1_extraction/
└── CLAUDE.md (~500 lines, extraction-focused)
```

#### Day 5: Testing & Validation
- [ ] **Task 2.13**: Run full extraction pipeline on Chapter 4
- [ ] **Task 2.14**: Validate output against schema
- [ ] **Task 2.15**: Fix any validation errors
- [ ] **Task 2.16**: Document test results

**Success Criteria**:
- ✅ Chapter 4 extraction produces valid `extraction_results.json`
- ✅ All tests pass
- ✅ No dependencies on Pipeline 2 or 3 code

---

### Week 3: Pipeline 2 (RAG) Migration

**Goal**: Isolate RAG components into Pipeline 2

**Tasks**:

#### Day 1: Directory Restructuring
- [ ] **Task 3.1**: Create `pipeline2_rag/` directory
- [ ] **Task 3.2**: Move relationship detectors to `pipeline2_rag/src/detectors/`
- [ ] **Task 3.3**: Move exporters to `pipeline2_rag/src/exporters/`
- [ ] **Task 3.4**: Move RAG tests to `pipeline2_rag/tests/`

**Deliverables**:
```
pipeline2_rag/
├── src/
│   ├── detectors/
│   ├── exporters/
│   └── core/
└── tests/
```

#### Day 2-3: Input/Output Standardization
- [ ] **Task 3.5**: Create `ExtractionResultsReader` class (reads Pipeline 1 output)
- [ ] **Task 3.6**: Create `RAGBundleWriter` class (writes JSONL)
- [ ] **Task 3.7**: Create `KnowledgeGraphBuilder` class (builds graph JSON)
- [ ] **Task 3.8**: Add schema validation to all outputs

**Deliverables**:
```python
# pipeline2_rag/src/io_handlers.py
class ExtractionResultsReader:
    """Read and validate Pipeline 1 output."""
    def __init__(self, json_path: str): ...
    def validate(self) -> bool: ...
    def get_equations(self) -> List[dict]: ...
    def get_tables(self) -> List[dict]: ...
    def get_figures(self) -> List[dict]: ...

class RAGBundleWriter:
    """Write standardized RAG bundles."""
    def write_bundle(self, bundle: dict) -> None: ...
    def validate_bundle(self, bundle: dict) -> bool: ...
    def finalize(self) -> str: ...
```

#### Day 4: Pipeline 2 CLAUDE.md
- [ ] **Task 3.9**: Create `pipeline2_rag/CLAUDE.md`
- [ ] **Task 3.10**: Extract RAG-specific content from main CLAUDE.md
- [ ] **Task 3.11**: Document relationship detection logic
- [ ] **Task 3.12**: Add embedding generation guide

**Deliverables**:
```
pipeline2_rag/
└── CLAUDE.md (~500 lines, RAG-focused)
```

#### Day 5: Testing with Mock Data
- [ ] **Task 3.13**: Create mock `extraction_results.json` for testing
- [ ] **Task 3.14**: Run Pipeline 2 with mock input
- [ ] **Task 3.15**: Validate outputs against schemas
- [ ] **Task 3.16**: Test with real Pipeline 1 output from Week 2

**Success Criteria**:
- ✅ Pipeline 2 runs successfully with mock input
- ✅ Pipeline 2 processes real Chapter 4 extraction output
- ✅ All outputs pass schema validation
- ✅ No dependencies on Pipeline 1 or 3 code

---

### Week 4: Pipeline 3 (Curation) Migration

**Goal**: Isolate curation components into Pipeline 3

**Tasks**:

#### Day 1: Directory Restructuring
- [ ] **Task 4.1**: Create `pipeline3_curation/` directory
- [ ] **Task 4.2**: Move novelty classification to `pipeline3_curation/src/core/`
- [ ] **Task 4.3**: Move validation to `pipeline3_curation/src/validators/`
- [ ] **Task 4.4**: Move curation tests to `pipeline3_curation/tests/`

**Deliverables**:
```
pipeline3_curation/
├── src/
│   ├── core/
│   ├── validators/
│   └── exporters/
└── tests/
```

#### Day 2-3: Input/Output Standardization
- [ ] **Task 4.5**: Create `RAGBundleReader` class (reads Pipeline 2 output)
- [ ] **Task 4.6**: Create `KnowledgeGraphReader` class
- [ ] **Task 4.7**: Update database schema for pipeline architecture
- [ ] **Task 4.8**: Add metadata tracking for pipeline provenance

**Deliverables**:
```python
# pipeline3_curation/src/io_handlers.py
class RAGBundleReader:
    """Read and process RAG bundles from Pipeline 2."""
    def __init__(self, jsonl_path: str): ...
    def validate(self) -> bool: ...
    def iter_bundles(self) -> Iterator[dict]: ...
    def get_bundle_by_id(self, bundle_id: str) -> dict: ...

class KnowledgeGraphReader:
    """Read knowledge graph from Pipeline 2."""
    def __init__(self, json_path: str): ...
    def validate(self) -> bool: ...
    def get_nodes(self) -> List[dict]: ...
    def get_edges(self) -> List[dict]: ...
```

#### Day 4: Pipeline 3 CLAUDE.md
- [ ] **Task 4.9**: Create `pipeline3_curation/CLAUDE.md`
- [ ] **Task 4.10**: Extract curation-specific content from main CLAUDE.md
- [ ] **Task 4.11**: Document novelty classification logic
- [ ] **Task 4.12**: Add calibration layer documentation

**Deliverables**:
```
pipeline3_curation/
└── CLAUDE.md (~500 lines, curation-focused)
```

#### Day 5: Testing with Mock Data
- [ ] **Task 4.13**: Create mock `rag_bundles.jsonl` for testing
- [ ] **Task 4.14**: Run Pipeline 3 with mock input
- [ ] **Task 4.15**: Validate database outputs
- [ ] **Task 4.16**: Test with real Pipeline 2 output from Week 3

**Success Criteria**:
- ✅ Pipeline 3 runs successfully with mock input
- ✅ Pipeline 3 processes real Chapter 4 RAG output
- ✅ Database schema includes pipeline provenance
- ✅ No dependencies on Pipeline 1 or 2 code

---

### Week 5: Integration Testing & Documentation

**Goal**: Validate end-to-end pipeline and finalize documentation

**Tasks**:

#### Day 1-2: End-to-End Integration Testing
- [ ] **Task 5.1**: Run full three-pipeline sequence on Chapter 4
- [ ] **Task 5.2**: Validate all intermediate outputs
- [ ] **Task 5.3**: Compare results with monolithic version
- [ ] **Task 5.4**: Measure performance (time, memory)

**Test Sequence**:
```bash
# Pipeline 1: Extraction
cd pipeline1_extraction
python run_extraction.py --input data/Ch-04_Heat_Transfer.pdf \
    --output results/extraction/ch04/

# Validate Pipeline 1 output
python validate_extraction_output.py results/extraction/ch04/extraction_results.json

# Pipeline 2: RAG Preparation
cd ../pipeline2_rag
python run_rag_preparation.py \
    --input results/extraction/ch04/extraction_results.json \
    --output results/rag/ch04/

# Validate Pipeline 2 output
python validate_rag_output.py results/rag/ch04/

# Pipeline 3: Curation
cd ../pipeline3_curation
python run_curation.py \
    --input results/rag/ch04/rag_bundles.jsonl \
    --model qwen-2.5-3b \
    --output results/curation/

# Validate Pipeline 3 output
python validate_curation_output.py results/curation/model_metadata_qwen-2.5-3b.db
```

#### Day 3: Documentation Finalization
- [ ] **Task 5.5**: Write `PIPELINE_ARCHITECTURE_OVERVIEW.md`
- [ ] **Task 5.6**: Create developer quickstart guides for each pipeline
- [ ] **Task 5.7**: Document interface versioning policy
- [ ] **Task 5.8**: Write troubleshooting guide

**Deliverables**:
```
docs/
├── PIPELINE_ARCHITECTURE_OVERVIEW.md
├── PIPELINE1_QUICKSTART.md
├── PIPELINE2_QUICKSTART.md
├── PIPELINE3_QUICKSTART.md
├── INTERFACE_VERSIONING.md
└── TROUBLESHOOTING.md
```

#### Day 4: Cleanup & Migration
- [ ] **Task 5.9**: Archive old monolithic code to `archive/v13_monolithic/`
- [ ] **Task 5.10**: Update root CLAUDE.md to reference pipeline structure
- [ ] **Task 5.11**: Create `run_full_pipeline.sh` orchestration script
- [ ] **Task 5.12**: Update CI/CD configuration (if applicable)

**Deliverables**:
```
archive/
└── v13_monolithic/
    └── [all old code]

scripts/
└── run_full_pipeline.sh
```

#### Day 5: Final Validation & Sign-off
- [ ] **Task 5.13**: Run complete pipeline on 3 different documents
- [ ] **Task 5.14**: Validate all outputs
- [ ] **Task 5.15**: Performance benchmarking report
- [ ] **Task 5.16**: Create migration completion checklist

**Success Criteria**:
- ✅ All three pipelines run independently
- ✅ End-to-end integration produces correct results
- ✅ Performance comparable to monolithic version (±10%)
- ✅ All documentation complete
- ✅ All tests passing

---

## 🎯 Success Criteria & Validation

### Technical Success Criteria

1. **Interface Contracts** ✅
   - [ ] All interfaces have JSON schemas
   - [ ] All outputs pass schema validation
   - [ ] Interface versions documented

2. **Code Isolation** ✅
   - [ ] No cross-pipeline imports (except common/)
   - [ ] Each pipeline has independent tests
   - [ ] Each pipeline can run standalone

3. **Context Reduction** ✅
   - [ ] Each CLAUDE.md file ≤ 600 lines
   - [ ] 60% reduction from monolithic (~1,500 lines)
   - [ ] No duplicate content across files

4. **Functionality Preservation** ✅
   - [ ] Chapter 4 extraction: 165 objects (same as before)
   - [ ] RAG bundles: 120 bundles (same as before)
   - [ ] Curation: Same accuracy (95-97%)

5. **Performance** ✅
   - [ ] Pipeline 1: ≤ 60 seconds (was ~45s)
   - [ ] Pipeline 2: ≤ 90 seconds (was ~70s)
   - [ ] Pipeline 3: ≤ 20 seconds (was ~15s)
   - [ ] Total: ≤ 180 seconds (10% overhead acceptable)

### Development Success Criteria

6. **AI Agent Efficiency** ✅
   - [ ] Local Claude can work on one pipeline with <600 line context
   - [ ] Changes to one pipeline don't require understanding others
   - [ ] Mock data enables pipeline development without dependencies

7. **Parallel Development** ✅
   - [ ] Multiple developers can work on different pipelines simultaneously
   - [ ] Interface changes require explicit coordination
   - [ ] Pipeline-specific tests enable independent validation

8. **Maintainability** ✅
   - [ ] Clear ownership boundaries
   - [ ] Interface versioning enables evolution
   - [ ] Shared utilities prevent code duplication

---

## ⚠️ Risk Management

### Risk 1: Interface Breaking Changes

**Risk Level**: HIGH
**Probability**: MEDIUM
**Impact**: HIGH

**Scenario**: Pipeline 1 developer changes output format, breaking Pipeline 2

**Mitigation**:
1. **Semantic Versioning**: All interfaces use semver (v1.0, v1.1, v2.0)
2. **Schema Validation**: Automated tests validate outputs
3. **Deprecation Policy**:
   - v1.x supported for 6 months after v2.0 release
   - Pipeline 2 must support both v1.x and v2.x during transition
4. **Change Review Process**: Interface changes require review from all pipeline owners

**Detection**:
```python
# Automated in CI/CD
def test_interface_compatibility():
    # Pipeline 1 produces v1.0 output
    extraction_output = run_pipeline1()
    assert validate_schema(extraction_output, "extraction_results_v1.json")

    # Pipeline 2 can consume v1.0 input
    rag_output = run_pipeline2(extraction_output)
    assert rag_output is not None  # Didn't crash
```

---

### Risk 2: Shared Library Coupling

**Risk Level**: MEDIUM
**Probability**: HIGH
**Impact**: MEDIUM

**Scenario**: Common library becomes bloated with pipeline-specific code

**Mitigation**:
1. **Clear Scope**: Common library only for truly shared utilities (PDF, logging, config)
2. **Code Review**: Any addition to common/ requires justification
3. **Size Limit**: Common library ≤ 1,000 lines total
4. **No Pipeline Logic**: Common library has zero business logic

**Enforcement**:
```python
# Pre-commit hook
def check_common_library_size():
    total_lines = count_lines("common/")
    if total_lines > 1000:
        raise Error("Common library exceeds 1,000 lines")
```

---

### Risk 3: Testing Gaps

**Risk Level**: MEDIUM
**Probability**: MEDIUM
**Impact**: HIGH

**Scenario**: Pipeline changes pass individual tests but break integration

**Mitigation**:
1. **Unit Tests**: Each pipeline has comprehensive unit tests
2. **Integration Tests**: Weekly end-to-end pipeline runs
3. **Mock Data**: Standardized mock data for all interfaces
4. **Regression Suite**: Chapter 4 as regression test baseline

**Test Coverage Goals**:
- Pipeline 1: 85% code coverage
- Pipeline 2: 90% code coverage
- Pipeline 3: 85% code coverage
- Common library: 95% code coverage

---

### Risk 4: Documentation Drift

**Risk Level**: LOW
**Probability**: HIGH
**Impact**: MEDIUM

**Scenario**: CLAUDE.md files become outdated as code evolves

**Mitigation**:
1. **Documentation Review**: Update CLAUDE.md with every major change
2. **Automated Checks**: Link code examples in docs to actual code
3. **Quarterly Review**: Review all CLAUDE.md files every 3 months
4. **Version Tags**: Tag CLAUDE.md with code version

**Example**:
```markdown
<!-- In pipeline1_extraction/CLAUDE.md -->
# Current Version: v13.2.0
# Last Updated: 2025-11-14

## Quick Start
[Code example verified against v13.2.0]
```

---

## 📊 Performance Benchmarks

### Baseline (Monolithic Architecture)

**Test Document**: Chapter 4 Heat Transfer (34 pages, 165 objects)

```
Extraction:     42.8 seconds
RAG Prep:       68.3 seconds
Curation:       14.2 seconds
-----------------------------------
Total:          125.3 seconds
```

### Target (Pipeline Architecture)

**Acceptable Overhead**: ≤10% (137.8 seconds max)

**Expected Performance**:
```
Pipeline 1:     50 seconds   (+17%)  # Overhead from schema validation
Pipeline 2:     75 seconds   (+10%)  # Overhead from interface I/O
Pipeline 3:     18 seconds   (+27%)  # Overhead from additional validation
-----------------------------------
Total:          143 seconds  (+14%)  # Slightly above target

Optimizations planned:
- Lazy validation (only in debug mode)
- Binary format for large embeddings
- Caching of intermediate results

Optimized Target: 130 seconds (+4%)
```

---

## 🔄 Rollback Plan

**Scenario**: Pipeline architecture proves problematic

**Rollback Steps**:

1. **Archive Pipeline Code** (1 hour)
   ```bash
   mv pipeline1_extraction archive/pipeline_attempt_2025-11/
   mv pipeline2_rag archive/pipeline_attempt_2025-11/
   mv pipeline3_curation archive/pipeline_attempt_2025-11/
   ```

2. **Restore Monolithic Code** (30 minutes)
   ```bash
   git checkout v13_monolithic_backup
   # Or restore from archive/v13_monolithic/
   ```

3. **Restore CLAUDE.md** (15 minutes)
   ```bash
   cp archive/v13_monolithic/CLAUDE.md ./
   ```

4. **Validation** (30 minutes)
   - Run full test suite
   - Process Chapter 4 end-to-end
   - Verify outputs match pre-migration baseline

**Total Rollback Time**: 2-3 hours

**Rollback Criteria** (when to abort):
- ❌ Interface validation overhead >20%
- ❌ Cannot achieve <600 lines per CLAUDE.md
- ❌ Integration testing fails repeatedly
- ❌ Development velocity decreases (not increases)

---

## 📋 Detailed Task Checklist

### Week 1: Foundation (15 tasks)
- [ ] 1.1: Create schemas/ directory
- [ ] 1.2: Write extraction_results_v1.json schema
- [ ] 1.3: Write rag_bundles_v1.json schema
- [ ] 1.4: Write knowledge_graph_v1.json schema
- [ ] 1.5: Document versioning policy
- [ ] 1.6: Create validate_interfaces.py
- [ ] 1.7: Implement Pydantic models
- [ ] 1.8: Write validation tests
- [ ] 1.9: Create mock data generators
- [ ] 1.10: Create common/ directory
- [ ] 1.11: Move shared utilities
- [ ] 1.12: Add pyproject.toml
- [ ] 1.13: Write common/ tests
- [ ] 1.14: Update .gitignore
- [ ] 1.15: Week 1 validation checkpoint

### Week 2: Pipeline 1 (16 tasks)
- [ ] 2.1: Create pipeline1_extraction/ directory
- [ ] 2.2: Move detection agents
- [ ] 2.3: Move extraction agents
- [ ] 2.4: Move extraction tests
- [ ] 2.5: Create ExtractionResultsBuilder
- [ ] 2.6: Update agents to use builder
- [ ] 2.7: Add output schema validation
- [ ] 2.8: Test output format
- [ ] 2.9: Create pipeline1 CLAUDE.md
- [ ] 2.10: Extract content from main CLAUDE.md
- [ ] 2.11: Document I/O contracts
- [ ] 2.12: Add troubleshooting guide
- [ ] 2.13: Run extraction on Chapter 4
- [ ] 2.14: Validate output
- [ ] 2.15: Fix validation errors
- [ ] 2.16: Week 2 validation checkpoint

### Week 3: Pipeline 2 (16 tasks)
- [ ] 3.1: Create pipeline2_rag/ directory
- [ ] 3.2: Move relationship detectors
- [ ] 3.3: Move exporters
- [ ] 3.4: Move RAG tests
- [ ] 3.5: Create ExtractionResultsReader
- [ ] 3.6: Create RAGBundleWriter
- [ ] 3.7: Create KnowledgeGraphBuilder
- [ ] 3.8: Add output validation
- [ ] 3.9: Create pipeline2 CLAUDE.md
- [ ] 3.10: Extract RAG content
- [ ] 3.11: Document relationship logic
- [ ] 3.12: Add embedding guide
- [ ] 3.13: Create mock extraction input
- [ ] 3.14: Run with mock input
- [ ] 3.15: Validate outputs
- [ ] 3.16: Week 3 validation checkpoint

### Week 4: Pipeline 3 (16 tasks)
- [ ] 4.1: Create pipeline3_curation/ directory
- [ ] 4.2: Move novelty classification
- [ ] 4.3: Move validators
- [ ] 4.4: Move curation tests
- [ ] 4.5: Create RAGBundleReader
- [ ] 4.6: Create KnowledgeGraphReader
- [ ] 4.7: Update database schema
- [ ] 4.8: Add pipeline provenance
- [ ] 4.9: Create pipeline3 CLAUDE.md
- [ ] 4.10: Extract curation content
- [ ] 4.11: Document classification logic
- [ ] 4.12: Add calibration docs
- [ ] 4.13: Create mock RAG input
- [ ] 4.14: Run with mock input
- [ ] 4.15: Validate database
- [ ] 4.16: Week 4 validation checkpoint

### Week 5: Integration (16 tasks)
- [ ] 5.1: Run full pipeline on Chapter 4
- [ ] 5.2: Validate all outputs
- [ ] 5.3: Compare with monolithic
- [ ] 5.4: Performance benchmarks
- [ ] 5.5: Write architecture overview
- [ ] 5.6: Create quickstart guides
- [ ] 5.7: Document versioning
- [ ] 5.8: Write troubleshooting guide
- [ ] 5.9: Archive old code
- [ ] 5.10: Update root CLAUDE.md
- [ ] 5.11: Create orchestration script
- [ ] 5.12: Update CI/CD
- [ ] 5.13: Run on 3 documents
- [ ] 5.14: Final validation
- [ ] 5.15: Performance report
- [ ] 5.16: Migration completion checklist

**Total Tasks**: 79

---

## 🎯 Next Steps for Discussion

### Questions for Local Claude Code

1. **Timeline Feasibility**:
   - Does 4-5 weeks seem realistic?
   - Should we add buffer time?
   - Any tasks that seem underestimated?

2. **Interface Design**:
   - Are the proposed JSON schemas appropriate?
   - Should we use binary formats for embeddings (performance)?
   - Any missing fields in the schemas?

3. **Testing Strategy**:
   - Is mock data approach sufficient?
   - Should we create a test document (smaller than Chapter 4)?
   - What level of test coverage is realistic?

4. **Migration Risks**:
   - What risks are we missing?
   - How should we handle rollback scenario?
   - Should we migrate incrementally (one pipeline at a time)?

5. **Development Workflow**:
   - Should we create separate git branches for each pipeline?
   - How to coordinate interface changes?
   - What review process for CLAUDE.md updates?

### Proposed Decision Points

**Decision Point 1** (Week 1): Approve interface schemas
- Review all three JSON schemas
- Validate against current data
- Sign off on v1.0 contracts

**Decision Point 2** (Week 2): Validate Pipeline 1 isolation
- Confirm Pipeline 1 runs independently
- Review extraction_results.json quality
- Approve CLAUDE.md structure

**Decision Point 3** (Week 3): Validate Pipeline 2 isolation
- Confirm Pipeline 2 works with Pipeline 1 output
- Review RAG bundle quality
- Check knowledge graph completeness

**Decision Point 4** (Week 4): Validate Pipeline 3 isolation
- Confirm Pipeline 3 works with Pipeline 2 output
- Review curation quality
- Verify database schema

**Decision Point 5** (Week 5): Final migration approval
- Review end-to-end performance
- Compare with monolithic baseline
- Make go/no-go decision

---

## 📚 Reference Documentation

### Architecture Documents to Create

1. **PIPELINE_ARCHITECTURE_OVERVIEW.md**: High-level architecture explanation
2. **INTERFACE_VERSIONING.md**: Semantic versioning policy for interfaces
3. **PIPELINE1_QUICKSTART.md**: How to work on extraction pipeline
4. **PIPELINE2_QUICKSTART.md**: How to work on RAG pipeline
5. **PIPELINE3_QUICKSTART.md**: How to work on curation pipeline
6. **TROUBLESHOOTING.md**: Common issues and solutions
7. **MIGRATION_COMPLETION_CHECKLIST.md**: Final validation checklist

### Code Standards

1. **Interface Contracts**: All I/O must validate against schemas
2. **Error Handling**: Validation errors must include helpful messages
3. **Logging**: All pipelines use structured logging (JSON format)
4. **Configuration**: All pipelines use YAML configuration
5. **Testing**: Minimum 85% code coverage per pipeline

### Documentation Standards

1. **CLAUDE.md Structure**:
   - Purpose (50 lines)
   - Current Session (100 lines)
   - Architecture (150 lines)
   - Input/Output Contracts (100 lines)
   - Troubleshooting (100 lines)
   - **Total**: ~500 lines

2. **Code Comments**:
   - Every function has docstring
   - Complex logic has inline comments
   - Magic numbers explained

3. **Interface Documentation**:
   - Every field in schema has description
   - Examples for each interface
   - Validation rules documented

---

## ✅ Sign-off Checklist

### Pre-Migration Sign-off (Before Week 1)
- [ ] User approves overall plan
- [ ] User approves 4-5 week timeline
- [ ] User approves pipeline boundaries
- [ ] User approves interface design approach
- [ ] Local Claude Code reviews plan
- [ ] Local Claude Code approves task breakdown
- [ ] Resources allocated (AI agent time, user review time)

### Post-Migration Sign-off (After Week 5)
- [ ] All 79 tasks completed
- [ ] All interfaces validated
- [ ] All tests passing
- [ ] Performance benchmarks met
- [ ] Documentation complete
- [ ] User accepts final deliverables
- [ ] Migration officially complete

---

## 📝 Appendix: Template Files

### Template: extraction_results.json
```json
{
  "schema_version": "1.0",
  "document_metadata": {
    "document_id": "example_doc",
    "source_pdf": "data/example.pdf",
    "source_pdf_hash": "sha256:...",
    "extraction_timestamp": "2025-11-14T10:00:00Z",
    "extractor_version": "v13.1.0",
    "total_pages": 10
  },
  "extracted_objects": {
    "equations": [],
    "tables": [],
    "figures": [],
    "text_chunks": []
  },
  "extraction_statistics": {
    "total_objects": 0,
    "processing_time_seconds": 0.0,
    "success_rate": 1.0
  }
}
```

### Template: rag_bundles.jsonl
```json
{"bundle_id": "example_bundle", "bundle_type": "equation", "schema_version": "1.0", "source_object": {...}, "relationships": [], "embeddings": {...}, "context_enhancement": {...}, "metadata": {...}}
```

### Template: knowledge_graph.json
```json
{
  "schema_version": "1.0",
  "document_id": "example_doc",
  "created_timestamp": "2025-11-14T10:00:00Z",
  "nodes": [],
  "edges": [],
  "statistics": {
    "total_nodes": 0,
    "total_edges": 0
  }
}
```

---

**Document Status**: READY FOR REVIEW
**Next Action**: Local Claude Code to review and provide feedback
**Review Deadline**: Within 48 hours of document creation

**Prepared by**: Web Claude Code (Anthropic)
**Date**: 2025-11-14
**Version**: 1.0
