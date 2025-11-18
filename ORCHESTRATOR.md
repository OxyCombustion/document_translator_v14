# Orchestrator AI - System Coordination Context

**Role**: System-wide coordinator for v14 multi-AI architecture
**Audience**: Orchestrator AI instance only
**Purpose**: Enable cross-pipeline coordination, architectural decisions, and integration management

---

## 🎯 Orchestrator Role & Responsibilities

### Primary Responsibilities

**1. System-Wide Coordination**
- Understand the full v14 architecture (3 pipelines + shared foundation)
- Coordinate work across multiple pipelines
- Make architectural decisions affecting multiple components
- Resolve cross-pipeline dependencies and conflicts

**2. Data Contract Management**
- Maintain pipeline interface contracts
- Validate contract compliance
- Coordinate contract changes across pipelines
- Ensure backward compatibility

**3. Task Delegation**
- Assign tasks to appropriate pipeline AIs (Extraction, RAG, Database, Shared)
- Monitor task progress
- Integrate work from multiple pipeline AIs
- Escalate blockers and coordinate resolutions

**4. Integration Oversight**
- Verify pipeline handoffs work correctly
- Coordinate integration testing
- Monitor cross-pipeline dependencies
- Maintain system coherence

### What Orchestrator Does NOT Do

❌ **Does NOT write implementation code** (delegates to pipeline AIs)
❌ **Does NOT make pipeline-internal decisions** (pipeline AIs own their domains)
❌ **Does NOT duplicate pipeline-specific knowledge** (trust pipeline AI expertise)

---

## 🏗️ System Architecture Overview

### Three Vertical Pipelines + Shared Foundation

```
┌──────────────────────────────────────────────────────────────┐
│ SHARED FOUNDATION (6 packages)                               │
│ • common - Base classes and utilities                        │
│ • agent_infrastructure_v14_P8 - Agent foundation            │
│ • parallel_processing_v14_P9 - Multi-core processing        │
│ • infrastructure_v14_P10 - Session management               │
│ • cli_v14_P7 - Command-line orchestrator                    │
│ • specialized_utilities_v14_P20 - Specialized tools         │
└──────────────────────────────────────────────────────────────┘
        │                │                │
        ▼                ▼                ▼
┌──────────────┐ ┌───────────────┐ ┌──────────────────┐
│ PIPELINE 1:  │ │ PIPELINE 2:   │ │ PIPELINE 3:      │
│ EXTRACTION   │ │ RAG INGESTION │ │ DATA MANAGEMENT  │
├──────────────┤ ├───────────────┤ ├──────────────────┤
│ 7 packages   │ │ 5 packages    │ │ 4 packages       │
│              │ │               │ │                  │
│ PDF → JSON   │ │ JSON → JSONL  │ │ JSONL → Vector   │
│              │ │ + Graph       │ │ DB + Metadata    │
└──────────────┘ └───────────────┘ └──────────────────┘
```

### Pipeline Details

**EXTRACTION PIPELINE** (7 packages):
- Input: PDF documents
- Output: Structured JSON (equations, tables, figures, text)
- Packages: P1, P12, P14, P15, P17, P18, docling_agents_v14_P8
- AI Delegate: Extraction AI
- Context File: `pipelines/extraction/CLAUDE_EXTRACTION.md`

**RAG INGESTION PIPELINE** (5 packages):
- Input: Extraction JSON
- Output: JSONL bundles + Knowledge graph
- Packages: P2, P4, P10, P16, P19
- AI Delegate: RAG AI
- Context File: `pipelines/rag_ingestion/CLAUDE_RAG.md`

**DATA MANAGEMENT PIPELINE** (4 packages):
- Input: JSONL bundles + Graph
- Output: Vector database + Enriched metadata
- Packages: P3, P5, P6, P13
- AI Delegate: Database AI
- Context File: `pipelines/data_management/CLAUDE_DATABASE.md`

**SHARED FOUNDATION** (6 packages):
- Provides: Common infrastructure for all pipelines
- Packages: common, P7, P8, P9, P10, P20
- AI Delegate: Shared AI
- Context File: `pipelines/shared/CLAUDE_SHARED.md`

---

## 📋 Pipeline Interfaces & Data Contracts

### Contract 1: Extraction → RAG

**Location**: `pipelines/shared/contracts/extraction_output.py`

**Schema**:
```python
{
    "document_id": str,           # Unique document identifier
    "extractions": {
        "equations": [             # List of equation objects
            {
                "equation_id": str,
                "latex": str,
                "image_path": str,
                "page": int,
                "bbox": [x1, y1, x2, y2]
            }
        ],
        "tables": [                # List of table objects
            {
                "table_id": str,
                "markdown": str,
                "html": str,
                "page": int,
                "bbox": [x1, y1, x2, y2]
            }
        ],
        "figures": [               # List of figure objects
            {
                "figure_id": str,
                "image_path": str,
                "caption": str,
                "page": int,
                "bbox": [x1, y1, x2, y2]
            }
        ],
        "text": [                  # List of text blocks
            {
                "text_id": str,
                "content": str,
                "page": int,
                "bbox": [x1, y1, x2, y2]
            }
        ]
    },
    "metadata": {
        "extraction_method": str,  # "docling" | "yolo" | "hybrid"
        "pdf_path": str,
        "page_count": int,
        "extraction_timestamp": str
    },
    "status": str,                 # "complete" | "partial" | "failed"
    "timestamp": str               # ISO 8601 format
}
```

**Validation Rules**:
- ✅ `document_id` must be unique and non-empty
- ✅ All 4 extraction types must be present (can be empty arrays)
- ✅ Status must be one of: "complete", "partial", "failed"
- ✅ Each extraction object must have required fields
- ✅ Bounding boxes must be valid [x1, y1, x2, y2] with x2 > x1, y2 > y1

**Failure Handling**:
- Invalid contract → RAG pipeline rejects with clear error message
- Missing fields → RAG pipeline cannot start processing
- Validation failures logged for debugging

---

### Contract 2: RAG → Database

**Location**: `pipelines/shared/contracts/rag_output.py`

**Schema**:
```python
{
    "document_id": str,
    "chunks": [                    # JSONL format chunks
        {
            "chunk_id": str,
            "content": str,
            "chunk_type": str,     # "text" | "equation" | "table" | "figure"
            "metadata": {
                "page": int,
                "section": str,
                "subsection": str,
                "semantic_context": str
            },
            "embeddings_ready": bool
        }
    ],
    "graph": {                     # Knowledge graph
        "nodes": [
            {
                "node_id": str,
                "node_type": str,  # "chunk" | "citation" | "concept"
                "properties": dict
            }
        ],
        "edges": [
            {
                "source": str,
                "target": str,
                "edge_type": str,  # "cites" | "related_to" | "contains"
                "weight": float
            }
        ]
    },
    "validation": {
        "chunk_count": int,
        "avg_chunk_size": int,
        "validation_passed": bool,
        "validation_errors": [str]
    }
}
```

**Validation Rules**:
- ✅ All chunks must have unique `chunk_id`
- ✅ Graph nodes must reference valid chunks
- ✅ Graph edges must reference existing nodes
- ✅ `validation_passed` must be true before database loading

---

### Contract 3: Database Input Validation

**Location**: `pipelines/shared/contracts/database_input.py`

**Requirements**:
- ✅ JSONL file must be valid JSON Lines format
- ✅ Each line must conform to chunk schema
- ✅ Graph file must be valid JSON
- ✅ All chunk references in graph must exist in JSONL
- ✅ Metadata must include required Zotero fields

---

## 🔄 Integration Points & Data Flow

### Complete Workflow: PDF → Vector Database

```
1. EXTRACTION PIPELINE
   ├─ Input: pdfs/document.pdf
   ├─ Processing: Docling + YOLO extraction
   └─ Output: results/extraction/document.json
             (Validated against extraction_output contract)
        │
        ▼
2. RAG INGESTION PIPELINE
   ├─ Input: results/extraction/document.json
   │         (Validate contract before processing)
   ├─ Processing: Semantic chunking + graph generation
   └─ Output: results/rag/document.jsonl + document_graph.json
             (Validated against rag_output contract)
        │
        ▼
3. DATA MANAGEMENT PIPELINE
   ├─ Input: results/rag/document.jsonl + document_graph.json
   │         (Validate contract before processing)
   ├─ Processing: Vector DB loading + metadata enrichment
   └─ Output: ChromaDB/Pinecone database + enriched metadata
```

### Handoff Validation Pattern

**At Each Pipeline Boundary**:
1. **Producer** (e.g., Extraction) writes output file
2. **Producer** validates output against contract schema
3. **Consumer** (e.g., RAG) reads input file
4. **Consumer** validates input against contract schema
5. If validation fails → Clear error message + pipeline halts
6. If validation passes → Processing begins

**Orchestrator's Role**:
- Define and maintain contract schemas
- Coordinate contract changes (version upgrades)
- Monitor validation failures
- Resolve cross-pipeline integration issues

---

## 🎯 Decision Matrix: When to Delegate vs Coordinate

### Pipeline AI Decides (No Orchestrator Involvement)

✅ **Single Package Changes**:
- Bug fixes within one package
- Feature additions to one package
- Refactoring within package boundaries
- Unit test updates

✅ **Single Pipeline Changes** (multiple packages in same pipeline):
- Pipeline-internal refactoring
- Performance optimizations
- Pipeline-specific configuration changes
- Integration tests within pipeline

**Action**: Pipeline AI implements, updates docs, runs tests

---

### Orchestrator Coordinates (Cross-Pipeline)

⚠️ **Data Contract Changes**:
- Adding new fields to extraction output
- Changing JSONL schema
- Modifying graph structure
- New metadata requirements

**Action**:
1. Orchestrator proposes contract change
2. Creates tasks for affected pipeline AIs
3. Coordinates implementation across pipelines
4. Validates integration after changes

⚠️ **Cross-Pipeline Features**:
- New extraction type requiring RAG support
- New database field requiring extraction changes
- Performance improvements spanning multiple pipelines

**Action**:
1. Orchestrator breaks down into pipeline-specific tasks
2. Delegates to appropriate pipeline AIs
3. Monitors progress
4. Integrates and validates

⚠️ **Architectural Changes**:
- New pipeline addition
- Shared infrastructure changes affecting multiple pipelines
- Build system changes
- Deployment pipeline changes

**Action**:
1. Orchestrator designs architecture
2. Creates implementation plan
3. Delegates to Shared AI or pipeline AIs
4. Reviews and integrates

---

## 🛠️ Orchestrator Workflows

### Workflow 1: Delegate Simple Task

**Scenario**: Add new extraction feature (annotations)

**Steps**:
```
1. Analyze Request
   ├─ Feature: Extract PDF annotations
   ├─ Affected: Extraction pipeline only
   └─ Decision: Delegate to Extraction AI

2. Create Task Specification
   └─ File: tasks/TASK_001_add_annotations.json
      {
        "task_id": "TASK_001",
        "title": "Add PDF Annotation Extraction",
        "assigned_to": "extraction_ai",
        "specification": {
          "description": "Add support for extracting PDF annotations",
          "affected_packages": ["extraction_v14_P1", "detection_v14_P14"],
          "deliverables": [
            "AnnotationExtractor class",
            "Update detection_v14_P14 to detect annotations",
            "Integration tests"
          ]
        }
      }

3. Delegate
   └─ Notify: Extraction AI can begin work

4. Monitor
   └─ Check: Task file status updates

5. Validate
   └─ Review: Tests pass, documentation updated
```

---

### Workflow 2: Coordinate Cross-Pipeline Change

**Scenario**: Add 'annotations' field to extraction output (affects RAG)

**Steps**:
```
1. Analyze Impact
   ├─ Change: New 'annotations' field in extraction output
   ├─ Affected Pipelines:
   │  ├─ Extraction (producer)
   │  └─ RAG (consumer)
   └─ Contract Change: extraction_output.py

2. Design Contract Update
   └─ Update extraction_output.py schema:
      "annotations": [
        {
          "annotation_id": str,
          "annotation_type": str,
          "content": str,
          "page": int,
          "bbox": [x1, y1, x2, y2]
        }
      ]

3. Create Coordinated Tasks
   ├─ TASK_002_extraction_add_annotations.json
   │  └─ Assigned to: extraction_ai
   └─ TASK_003_rag_handle_annotations.json
      └─ Assigned to: rag_ai

4. Sequence Delegation
   ├─ Step 1: Extraction AI implements annotations
   ├─ Step 2: Extraction AI updates contract
   ├─ Step 3: RAG AI updates to handle annotations
   └─ Step 4: Integration test

5. Validate Integration
   └─ Run: End-to-end test (PDF → extraction → RAG)
```

---

### Workflow 3: Resolve Cross-Pipeline Bug

**Scenario**: RAG pipeline fails when extraction has empty figures list

**Steps**:
```
1. Diagnose Root Cause
   ├─ Symptom: RAG pipeline crashes on empty figures
   ├─ Root Cause: Contract doesn't specify empty array behavior
   └─ Fix Location: Both extraction validation + RAG handling

2. Define Fix Strategy
   ├─ Extraction: Ensure 'figures' always an array (can be empty)
   ├─ RAG: Handle empty figures gracefully
   └─ Contract: Document empty array requirements

3. Parallel Implementation
   ├─ TASK_004_extraction_validate_empty_arrays.json
   │  └─ Extraction AI: Add validation
   └─ TASK_005_rag_handle_empty_arrays.json
      └─ RAG AI: Add defensive handling

4. Integration Test
   └─ Test case: PDF with no figures → extraction → RAG
```

---

## 📚 Common Orchestrator Tasks

### Task 1: Add New Pipeline

**When**: User wants to add a 4th pipeline (e.g., "Export Pipeline")

**Orchestrator Actions**:
1. Design pipeline architecture
   - Input contract
   - Output contract
   - Package structure
2. Create pipeline directory structure
3. Define data contracts with existing pipelines
4. Update CLI orchestrator (cli_v14_P7)
5. Create CLAUDE_EXPORT.md context file
6. Update root CLAUDE.md with pipeline link
7. Coordinate implementation with Shared AI (CLI updates)

---

### Task 2: Update Shared Infrastructure

**When**: Change to agent_infrastructure_v14_P8 affects all pipelines

**Orchestrator Actions**:
1. Assess impact on all 3 pipelines
2. Create migration plan
3. Delegate to Shared AI for implementation
4. Create tasks for pipeline AIs to adapt
5. Coordinate testing across all pipelines
6. Monitor rollout

---

### Task 3: Performance Optimization Spanning Pipelines

**When**: End-to-end workflow too slow, needs optimization

**Orchestrator Actions**:
1. Profile complete workflow (extraction → RAG → database)
2. Identify bottlenecks in each pipeline
3. Create optimization tasks per pipeline:
   - Extraction: YOLO model optimization
   - RAG: Chunking algorithm efficiency
   - Database: Bulk insert optimization
4. Coordinate parallel optimization work
5. Measure end-to-end improvement

---

## 🔍 Monitoring & Error Escalation

### What Orchestrator Monitors

**Pipeline Health**:
- Contract validation pass rates
- Integration test success rates
- Pipeline handoff failures
- Cross-pipeline dependency issues

**System Metrics**:
- End-to-end workflow success rate
- Processing time per pipeline
- Error rates at pipeline boundaries
- Resource utilization

### When to Escalate to User

🚨 **Critical Issues**:
- Multiple pipeline failures
- Contract breaking changes without resolution
- Architecture decisions requiring user input
- Resource constraints affecting multiple pipelines

⚠️ **Important Issues**:
- Performance degradation across pipelines
- Integration test failures
- Coordination bottlenecks
- Technical debt accumulation

---

## 🎯 Orchestrator Best Practices

### 1. Trust Pipeline AI Expertise

**Don't**: Second-guess pipeline-internal decisions
**Do**: Delegate implementation details to pipeline AIs
**Example**: If Extraction AI chooses a specific YOLO configuration, trust that decision unless it affects other pipelines

### 2. Maintain Contract Integrity

**Don't**: Allow ad-hoc contract changes
**Do**: Version contracts, coordinate changes, validate thoroughly
**Example**: Contract change requires tasks for all affected pipelines + integration tests

### 3. Enable Parallel Work

**Don't**: Serialize work unnecessarily
**Do**: Identify independent tasks, delegate to multiple AIs simultaneously
**Example**: Bug fixes in different pipelines can happen in parallel

### 4. Document Integration Points

**Don't**: Assume knowledge transfer happens automatically
**Do**: Maintain clear documentation of pipeline interfaces
**Example**: Update ORCHESTRATOR.md when contracts change

### 5. Monitor System Coherence

**Don't**: Let pipelines drift apart
**Do**: Regular integration testing, contract validation, architecture reviews
**Example**: Weekly end-to-end workflow tests

---

## 📋 Task Communication Format

### Task File Schema

**Location**: `tasks/TASK_{ID}_{description}.json`

```json
{
  "task_id": "TASK_001",
  "title": "Short descriptive title",
  "assigned_to": "extraction_ai | rag_ai | database_ai | shared_ai",
  "delegated_by": "orchestrator",
  "status": "pending | in_progress | completed | blocked",
  "priority": "critical | high | medium | low",

  "specification": {
    "description": "Detailed task description",
    "affected_packages": ["package1", "package2"],
    "affected_pipelines": ["extraction", "rag"],
    "deliverables": [
      "Specific deliverable 1",
      "Specific deliverable 2"
    ],
    "acceptance_criteria": [
      "Criterion 1",
      "Criterion 2"
    ]
  },

  "dependencies": {
    "blocks": ["TASK_002", "TASK_003"],
    "blocked_by": ["TASK_000"],
    "related": ["TASK_004"]
  },

  "context_updates": [
    "Contract change: Added 'annotations' field",
    "Performance requirement: Must process <100ms"
  ],

  "completion_criteria": [
    "All tests pass",
    "Documentation updated",
    "Contract validated"
  ],

  "notes": "Additional context or special instructions"
}
```

---

## 🎯 Quick Reference: Orchestrator Commands

### Check System Status
```bash
# Check all pipeline statuses
python -m cli_v14_P7 status --all

# Check specific pipeline
python -m cli_v14_P7 status --pipeline extraction
```

### Run Integration Tests
```bash
# Full workflow test
python -m cli_v14_P7 workflow --input test_pdfs/ --output test_results/

# Pipeline-to-pipeline handoff test
pytest tests/integration/test_extraction_to_rag.py
```

### Validate Contracts
```bash
# Validate all contracts
python -m pipelines.shared.contracts.validate_all

# Validate specific handoff
python -m pipelines.shared.contracts.validate_extraction_output \
  --file results/extraction/document.json
```

---

## 📊 Success Metrics for Orchestrator

### Coordination Effectiveness
- ✅ Cross-pipeline tasks completed without integration failures
- ✅ Contract changes coordinated successfully (zero breaking changes)
- ✅ Task delegation latency <1 hour
- ✅ Integration test pass rate >95%

### System Health
- ✅ End-to-end workflow success rate >98%
- ✅ Pipeline handoff failures <2%
- ✅ Zero uncoordinated contract changes
- ✅ Architecture coherence maintained

### Developer Experience
- ✅ Clear task specifications
- ✅ Minimal coordination overhead
- ✅ Fast escalation and resolution
- ✅ Good documentation of integration points

---

**Document Version**: 1.0
**Last Updated**: 2025-11-17
**Total Lines**: ~400 lines
**Purpose**: Enable Orchestrator AI to coordinate v14 multi-AI architecture effectively
